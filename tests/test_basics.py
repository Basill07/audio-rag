"""Fast tests that run without Ollama, a microphone or downloaded models.

    AUDIO_RAG_MOCK=1 pytest -q
"""

import os

os.environ.setdefault("AUDIO_RAG_MOCK", "1")

import pytest  # noqa: E402

from audio_rag.voice import normalize_codes  # noqa: E402


@pytest.mark.parametrize(
    "heard, expected",
    [
        ("How do I clear air Re47 on Station 3?", "How do I clear error E47 on Station 3?"),
        ("what is error 52", "what is error E52"),
        ("show me E 60", "show me E60"),
        ("replace every 50,000 cycles", "replace every 50,000 cycles"),  # numbers that aren't codes stay
    ],
)
def test_normalize_codes(heard, expected):
    assert normalize_codes(heard) == expected


@pytest.fixture(scope="module")
def assistant(tmp_path_factory):
    os.environ["AUDIO_RAG_DB_DIR"] = str(tmp_path_factory.mktemp("chroma"))
    import importlib

    from audio_rag import config, rag

    importlib.reload(config)
    importlib.reload(rag)
    assert rag.ingest("station3") > 5
    return rag.MachineAssistant("station3")


@pytest.mark.parametrize(
    "question, section",
    [
        ("How do I clear error E47?", "E47"),
        ("What does E52 mean?", "E52"),
        ("Light curtain error E23", "E23"),
        ("When do I replace the screwdriver bit?", "bit"),
    ],
)
def test_retrieval_finds_right_section(assistant, question, section):
    top = assistant.ask(question).sources[0]
    assert section.lower() in top.section.lower()
