"""REST API + a small web demo page.

    uvicorn audio_rag.api:app --reload
    open http://localhost:8000
"""

from __future__ import annotations

import re
import shutil
import tempfile
import time
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel

from .config import settings
from .rag import SUPPORTED_FILES, MachineAssistant, ingest, list_machines

app = FastAPI(title="Audio RAG", description="Ask a machine about itself, by voice.", version="0.1.0")
STATIC = Path(__file__).parent / "static"


@lru_cache(maxsize=16)
def _assistant(machine: str) -> MachineAssistant:
    return MachineAssistant(machine)


def _get_assistant(machine: str) -> MachineAssistant:
    if machine not in list_machines():
        raise HTTPException(404, f"Unknown machine '{machine}'")
    try:
        return _assistant(machine)
    except RuntimeError as err:
        raise HTTPException(409, str(err)) from err


class AskRequest(BaseModel):
    machine: str
    question: str


class SpeakRequest(BaseModel):
    text: str


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/machines")
def machines():
    return {"machines": list_machines()}


@app.post("/ask")
def ask(req: AskRequest):
    t0 = time.perf_counter()
    answer = _get_assistant(req.machine).ask(req.question)
    return {**asdict(answer), "seconds": round(time.perf_counter() - t0, 2)}


@app.post("/ask-audio")
async def ask_audio(machine: str = Form(...), audio: UploadFile = File(...)):
    """Upload a recording (wav, mp3, webm, ...). Returns what was heard and the answer."""
    from . import voice

    assistant = _get_assistant(machine)
    suffix = Path(audio.filename or "rec.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(await audio.read())
        tmp.flush()
        t0 = time.perf_counter()
        question = voice.transcribe(tmp.name, hints=voice.load_hints(machine))
    t1 = time.perf_counter()
    if not question:
        raise HTTPException(422, "No speech detected")
    answer = assistant.ask(question)
    return {
        **asdict(answer),
        "timing": {"speech_to_text": round(t1 - t0, 2), "answer": round(time.perf_counter() - t1, 2)},
    }


def _safe_machine_name(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_-")
    if not clean:
        raise HTTPException(400, "Please give the machine a name (letters, numbers, - or _)")
    return clean[:50]


def _safe_relative_path(filename: str) -> Path | None:
    """Keep the folder structure of an uploaded folder, but never allow paths outside it."""
    parts = [p for p in Path(filename.replace("\\", "/")).parts if p not in ("", ".", "..", "/")]
    if not parts:
        return None
    return Path(*parts)


@app.get("/machines/{machine}/documents")
def list_documents(machine: str):
    folder = settings.data_dir / _safe_machine_name(machine)
    if not folder.is_dir():
        raise HTTPException(404, f"Unknown machine '{machine}'")
    files = [str(p.relative_to(folder)) for p in sorted(folder.rglob("*")) if p.is_file() and p.suffix.lower() in SUPPORTED_FILES]
    return {"machine": folder.name, "documents": files}


@app.post("/machines/{machine}/documents")
async def upload_documents(machine: str, files: list[UploadFile] = File(...), replace: bool = Form(False)):
    """Upload files or a whole folder for a machine, then (re)build its search index.

    replace=true deletes the machine's old documents first.
    """
    name = _safe_machine_name(machine)
    folder = settings.data_dir / name
    if replace and folder.exists():
        hints = folder / "whisper_hints.txt"
        keep = hints.read_bytes() if hints.exists() else None
        shutil.rmtree(folder)
        if keep is not None:
            folder.mkdir(parents=True)
            hints.write_bytes(keep)
    folder.mkdir(parents=True, exist_ok=True)

    saved, skipped = [], []
    for f in files:
        rel = _safe_relative_path(f.filename or "")
        if rel is None:
            continue
        # A chosen folder arrives as "FolderName/sub/file.pdf": drop the top folder name.
        if len(rel.parts) > 1:
            rel = Path(*rel.parts[1:])
        if rel.name == "whisper_hints.txt":
            target = folder / "whisper_hints.txt"
        elif rel.suffix.lower() not in SUPPORTED_FILES or rel.name.startswith("."):
            skipped.append(str(rel))
            continue
        else:
            target = folder / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(await f.read())
        saved.append(str(rel))

    if not saved:
        raise HTTPException(400, f"No supported files. Use: {', '.join(SUPPORTED_FILES)}")

    t0 = time.perf_counter()
    chunks = ingest(name)
    _assistant.cache_clear()  # make sure the next question uses the new documents
    return {
        "machine": name,
        "saved": saved,
        "skipped": skipped,
        "chunks": chunks,
        "seconds": round(time.perf_counter() - t0, 1),
    }


@app.post("/speak")
def speak(req: SpeakRequest):
    """Text to speech with Piper. 204 = no Piper voice installed (the web page then uses the browser voice)."""
    from . import voice

    with tempfile.TemporaryDirectory() as tmp:
        wav = voice.synthesize(req.text, Path(tmp) / "answer.wav")
        if wav is None:
            return Response(status_code=204)
        return Response(wav.read_bytes(), media_type="audio/wav")
