"""Voice in and out: microphone recording, Whisper speech-to-text, Piper text-to-speech."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

from .config import settings

SAMPLE_RATE = 16_000  # Whisper expects 16 kHz mono

# Default hint for Whisper. Each machine can add its own words in data/<machine>/whisper_hints.txt
# (error codes, part names), which helps Whisper hear "E47" instead of "ee forty seven".
DEFAULT_HINTS = "Questions about an industrial machine: error codes, maintenance, safety and spare parts."


def load_hints(machine: str) -> str:
    hints_file = settings.data_dir / machine / "whisper_hints.txt"
    if hints_file.exists():
        return hints_file.read_text(encoding="utf-8").strip()
    return DEFAULT_HINTS


# ---------- Speech to text ----------

@lru_cache(maxsize=1)
def _whisper():
    from faster_whisper import WhisperModel

    # int8 runs well on a laptop CPU, including Apple Silicon
    return WhisperModel(settings.whisper_model, device="auto", compute_type="int8")


def transcribe(audio: str | Path | np.ndarray, hints: str = DEFAULT_HINTS) -> str:
    """Turn speech into text. `audio` is a file path or a 16 kHz mono float32 array."""
    if isinstance(audio, Path):
        audio = str(audio)
    segments, _info = _whisper().transcribe(
        audio,
        language=settings.whisper_language or None,
        initial_prompt=hints,
        vad_filter=True,  # skip silence
        beam_size=5,
    )
    return normalize_codes(" ".join(seg.text.strip() for seg in segments).strip())


# Whisper often mishears codes: "error E47" -> "air Re47", "error E 47", "E-47", "ee 47".
_CODE_FIXES = [
    (re.compile(r"\b(?:air|error|era|arrow)\s+r?e\s?-?(\d{2,3})\b", re.I), r"error E\1"),
    (re.compile(r"\b(?:r?e|ee|e-)\s?-?(\d{2,3})\b", re.I), r"E\1"),
    (re.compile(r"\berror\s+(\d{2,3})\b", re.I), r"error E\1"),
]


def normalize_codes(text: str) -> str:
    """Turn misheard error codes back into the form used in the manuals (E47)."""
    for pattern, repl in _CODE_FIXES:
        text = pattern.sub(repl, text)
    return text


# ---------- Microphone ----------

def record_push_to_talk() -> np.ndarray:
    """Press Enter to start speaking, Enter again to stop. Returns 16 kHz mono audio."""
    import sounddevice as sd

    chunks: list[np.ndarray] = []

    def callback(indata, _frames, _time, status):
        if status:
            print(f"(mic: {status})")
        chunks.append(indata.copy())

    input("Press Enter and ask your question... ")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
        input("Listening. Press Enter when you're done.")
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks)[:, 0]


# ---------- Text to speech ----------

@lru_cache(maxsize=1)
def _piper():
    voice_path = Path(settings.piper_voice)
    if not settings.piper_voice or not voice_path.exists():
        return None
    from piper import PiperVoice

    return PiperVoice.load(voice_path)


def synthesize(text: str, out_path: str | Path) -> Path | None:
    """Write the spoken answer to a WAV file with Piper. Returns None if no Piper voice is installed."""
    voice = _piper()
    if voice is None:
        return None
    out_path = Path(out_path)
    with wave.open(str(out_path), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    return out_path


def speak(text: str) -> None:
    """Say the answer out loud. Uses Piper if a voice is installed, otherwise the system voice."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = synthesize(text, Path(tmp) / "answer.wav")
        if wav is not None:
            _play_wav(wav)
            return
    _system_say(text)


def _play_wav(path: Path) -> None:
    if platform.system() == "Darwin" and shutil.which("afplay"):
        subprocess.run(["afplay", str(path)], check=False)
        return
    import sounddevice as sd

    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    sd.play(data, rate)
    sd.wait()


def _system_say(text: str) -> None:
    if platform.system() == "Darwin" and shutil.which("say"):
        subprocess.run(["say", text], check=False)
    elif shutil.which("espeak-ng") or shutil.which("espeak"):
        subprocess.run([shutil.which("espeak-ng") or shutil.which("espeak"), text], check=False)
    else:
        print("(No voice output available. Install a Piper voice: see README.)")
