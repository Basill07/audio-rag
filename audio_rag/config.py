"""Central settings. Every value can be overridden with an environment variable."""

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # Where the machine documents live: one sub-folder per machine (data/station3, data/truck_x, ...)
    data_dir: Path = field(default_factory=lambda: Path(_env("AUDIO_RAG_DATA_DIR", str(ROOT / "data"))))
    # Where ChromaDB stores the vectors on disk
    db_dir: Path = field(default_factory=lambda: Path(_env("AUDIO_RAG_DB_DIR", str(ROOT / "storage" / "chroma"))))

    # Local models served by Ollama (https://ollama.com)
    ollama_url: str = _env("OLLAMA_URL", "http://localhost:11434")
    llm_model: str = _env("AUDIO_RAG_LLM", "llama3.1:8b")
    embed_model: str = _env("AUDIO_RAG_EMBED", "nomic-embed-text")
    llm_timeout: float = float(_env("AUDIO_RAG_LLM_TIMEOUT", "120"))

    # Retrieval
    chunk_size: int = int(_env("AUDIO_RAG_CHUNK_SIZE", "512"))
    chunk_overlap: int = int(_env("AUDIO_RAG_CHUNK_OVERLAP", "64"))
    top_k: int = int(_env("AUDIO_RAG_TOP_K", "4"))

    # Speech-to-text (faster-whisper): tiny, base, small, medium, large-v3
    whisper_model: str = _env("AUDIO_RAG_WHISPER", "base")
    whisper_language: str = _env("AUDIO_RAG_LANGUAGE", "en")

    # Text-to-speech (Piper). Path to a .onnx voice; empty = use the system voice instead
    piper_voice: str = _env("AUDIO_RAG_PIPER_VOICE", str(ROOT / "voices" / "en_US-lessac-medium.onnx"))

    # Use fake models (no Ollama needed) for tests
    mock_models: bool = _env("AUDIO_RAG_MOCK", "0") == "1"


settings = Settings()
