"""RAG core: load machine documents into ChromaDB and answer questions with a local Llama model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
from llama_index.core import PromptTemplate, Settings as LISettings, SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.vector_stores.chroma import ChromaVectorStore

from .config import settings

SUPPORTED_FILES = [".md", ".txt", ".pdf", ".docx"]

# The answer is spoken out loud, so the prompt asks for short, plain sentences.
QA_PROMPT = PromptTemplate(
    "You are a voice assistant built into an industrial machine. A technician is asking you a question "
    "while working, so answer in short, clear spoken sentences.\n"
    "Rules:\n"
    "- Use ONLY the documentation below. If the answer is not in it, say: "
    "\"I can't find that in the documentation for this machine.\"\n"
    "- For procedures, give numbered steps, one short sentence each.\n"
    "- Always mention safety steps (like lockout) if the documentation lists them.\n"
    "- No markdown, no tables, no bullet symbols. Keep it under 120 words.\n\n"
    "Documentation:\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Question: {query_str}\n"
    "Answer:"
)


@dataclass
class Source:
    file: str
    section: str
    score: float | None
    text: str


@dataclass
class Answer:
    question: str
    answer: str
    sources: list[Source]


def configure_models() -> None:
    """Point LlamaIndex at the local Ollama models (or fake ones for tests)."""
    if settings.mock_models:
        from llama_index.core.llms import MockLLM

        from .mock import HashEmbedding

        LISettings.embed_model = HashEmbedding()
        LISettings.llm = MockLLM(max_tokens=60)
        return

    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.llms.ollama import Ollama

    LISettings.embed_model = OllamaEmbedding(model_name=settings.embed_model, base_url=settings.ollama_url)
    LISettings.llm = Ollama(
        model=settings.llm_model,
        base_url=settings.ollama_url,
        request_timeout=settings.llm_timeout,
        temperature=0.1,  # low = sticks to the documents
    )


def collection_name(machine: str) -> str:
    """ChromaDB names: 3-63 characters, letters, digits, '_' or '-'."""
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", machine).strip("_-") or "machine"
    return f"m_{name}"[:63]


def _vector_store(machine: str) -> ChromaVectorStore:
    settings.db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.db_dir))
    collection = client.get_or_create_collection(collection_name(machine))
    return ChromaVectorStore(chroma_collection=collection)


def list_machines() -> list[str]:
    if not settings.data_dir.exists():
        return []
    return sorted(p.name for p in settings.data_dir.iterdir() if p.is_dir() and not p.name.startswith("."))


def ingest(machine: str, reset: bool = True) -> int:
    """Read every document in data/<machine>/, split it into chunks and store the vectors.

    Returns the number of chunks stored.
    """
    configure_models()
    folder = settings.data_dir / machine
    if not folder.is_dir():
        raise FileNotFoundError(f"No folder for machine '{machine}' at {folder}")

    if reset:
        client = chromadb.PersistentClient(path=str(settings.db_dir))
        try:
            client.delete_collection(collection_name(machine))
        except Exception:
            pass  # nothing to delete yet

    documents = SimpleDirectoryReader(
        str(folder),
        required_exts=SUPPORTED_FILES,
        exclude=["whisper_hints.txt"],  # speech hints, not documentation
        recursive=True,
    ).load_data()
    if not documents:
        raise ValueError(f"No supported documents ({', '.join(SUPPORTED_FILES)}) in {folder}")
    for doc in documents:
        doc.metadata["machine"] = machine

    # Split by headings first (keeps an error code and its fix together), then by size.
    pipeline = IngestionPipeline(
        transformations=[
            MarkdownNodeParser(),
            SentenceSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap),
        ]
    )
    nodes = pipeline.run(documents=documents)

    storage = StorageContext.from_defaults(vector_store=_vector_store(machine))
    VectorStoreIndex(nodes, storage_context=storage, show_progress=False)
    return len(nodes)


CODE_PATTERN = re.compile(r"\b[A-Z]{1,3}-?\d{2,4}\b")  # E47, ERR-102, BIT-T25-70 ...


class ExactCodeBoost(BaseNodePostprocessor):
    """Hybrid search: vector search finds similar text, but codes like "E47" must match exactly.

    Chunks that contain a code from the question move to the top. Then we keep the best `top_n`.
    """

    top_n: int = 4

    def _postprocess_nodes(self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None) -> list[NodeWithScore]:
        codes = set(CODE_PATTERN.findall(query_bundle.query_str.upper())) if query_bundle else set()
        if codes:
            def has_code(n: NodeWithScore) -> bool:
                text = n.node.get_content().upper()
                return any(re.search(rf"\b{re.escape(c)}\b", text) for c in codes)

            # stable sort: exact matches first, vector order kept inside each group
            nodes = sorted(nodes, key=lambda n: not has_code(n))
        return nodes[: self.top_n]


class MachineAssistant:
    """Answers questions about one machine."""

    def __init__(self, machine: str):
        configure_models()
        self.machine = machine
        store = _vector_store(machine)
        if store._collection.count() == 0:
            raise RuntimeError(f"No data for '{machine}'. Run: python -m audio_rag.cli ingest {machine}")
        index = VectorStoreIndex.from_vector_store(store)
        self.engine = index.as_query_engine(
            similarity_top_k=settings.top_k * 3,  # fetch more, then let the exact-code boost pick
            node_postprocessors=[ExactCodeBoost(top_n=settings.top_k)],
            text_qa_template=QA_PROMPT,
        )

    def ask(self, question: str) -> Answer:
        response = self.engine.query(question)
        sources = []
        for hit in response.source_nodes:
            meta = hit.node.metadata
            content = hit.node.get_content()
            first_line = content.lstrip().split("\n", 1)[0]
            heading = first_line.lstrip("#").strip() if first_line.startswith("#") else ""
            path = (meta.get("header_path") or "").strip("/")
            sources.append(
                Source(
                    file=Path(meta.get("file_name", "?")).name,
                    section=" > ".join(p for p in [path.split("/")[-1] if path else "", heading] if p) or "-",
                    score=round(hit.score, 3) if hit.score is not None else None,
                    text=hit.node.get_content()[:300],
                )
            )
        return Answer(question=question, answer=clean_for_speech(str(response)), sources=sources)


def clean_for_speech(text: str) -> str:
    """Remove markdown leftovers so the TTS voice doesn't read symbols out loud."""
    text = re.sub(r"[*_#`>|]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
