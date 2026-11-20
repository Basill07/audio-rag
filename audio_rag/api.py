"""REST API + a small web demo page.

    uvicorn audio_rag.api:app --reload
    open http://localhost:8000
"""

from __future__ import annotations

import tempfile
import time
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel

from .rag import MachineAssistant, list_machines

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


@app.post("/speak")
def speak(req: SpeakRequest):
    """Text to speech with Piper. 204 = no Piper voice installed (the web page then uses the browser voice)."""
    from . import voice

    with tempfile.TemporaryDirectory() as tmp:
        wav = voice.synthesize(req.text, Path(tmp) / "answer.wav")
        if wav is None:
            return Response(status_code=204)
        return Response(wav.read_bytes(), media_type="audio/wav")
