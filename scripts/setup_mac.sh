#!/usr/bin/env bash
# One-time setup on macOS. Run from the project folder: bash scripts/setup_mac.sh
set -e

if ! command -v ollama >/dev/null; then
  echo "Ollama is not installed. Install it from https://ollama.com/download (or: brew install ollama), then run this again."
  exit 1
fi

echo "1/4 Python environment"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "2/4 Local models (this downloads a few GB the first time)"
ollama pull "${AUDIO_RAG_LLM:-llama3.1:8b}"
ollama pull nomic-embed-text

echo "3/4 Piper voice"
mkdir -p voices
python -m piper.download_voices en_US-lessac-medium --download-dir voices

echo "4/4 Load the sample machine manual"
python -m audio_rag.cli ingest station3

echo
echo "Done. Try:"
echo "  source .venv/bin/activate"
echo "  python -m audio_rag.cli ask station3 \"How do I clear error E47?\""
echo "  python -m audio_rag.cli voice station3"
echo "  uvicorn audio_rag.api:app   # then open http://localhost:8000"
