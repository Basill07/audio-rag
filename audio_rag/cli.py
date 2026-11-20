"""Command line entry point.

    python -m audio_rag.cli ingest station3          # load the documents
    python -m audio_rag.cli ask station3 "How do I clear E47?"
    python -m audio_rag.cli chat station3            # type questions
    python -m audio_rag.cli voice station3           # talk to the machine
"""

from __future__ import annotations

import argparse
import sys
import time

from .config import settings
from .rag import MachineAssistant, ingest, list_machines


def _print_answer(answer, show_sources: bool = True) -> None:
    print(f"\nAssistant: {answer.answer}\n")
    if show_sources and answer.sources:
        print("Sources:")
        for s in answer.sources:
            print(f"  - {s.file} | {s.section} (score {s.score})")
        print()


def cmd_ingest(args) -> None:
    machines = list_machines() if args.machine == "all" else [args.machine]
    for m in machines:
        n = ingest(m)
        print(f"{m}: stored {n} chunks")


def cmd_ask(args) -> None:
    assistant = MachineAssistant(args.machine)
    _print_answer(assistant.ask(args.question), show_sources=not args.no_sources)


def cmd_chat(args) -> None:
    assistant = MachineAssistant(args.machine)
    print(f"Chatting with '{args.machine}'. Type 'exit' to quit.")
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"exit", "quit"}:
            break
        if q:
            _print_answer(assistant.ask(q), show_sources=not args.no_sources)


def cmd_voice(args) -> None:
    from . import voice

    assistant = MachineAssistant(args.machine)
    hints = voice.load_hints(args.machine)
    print(f"Voice assistant for '{args.machine}' (Whisper '{settings.whisper_model}', LLM '{settings.llm_model}').")
    print("Press Ctrl+C to quit.\n")
    voice.speak(f"Hello. Ask me anything about {args.machine.replace('_', ' ')}.")
    while True:
        try:
            audio = voice.record_push_to_talk()
        except KeyboardInterrupt:
            print("\nBye.")
            break
        if audio.size < voice.SAMPLE_RATE * 0.3:
            print("(Too short, try again.)")
            continue

        t0 = time.perf_counter()
        question = voice.transcribe(audio, hints=hints)
        t1 = time.perf_counter()
        if not question:
            print("(I didn't catch that.)")
            continue
        print(f"You said: {question}")

        answer = assistant.ask(question)
        t2 = time.perf_counter()
        _print_answer(answer, show_sources=not args.no_sources)
        print(f"(speech-to-text {t1 - t0:.1f}s, answer {t2 - t1:.1f}s)")
        voice.speak(answer.answer)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="audio_rag", description="Ask a machine about itself, by voice.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="Load documents from data/<machine>/ into the vector database")
    p.add_argument("machine", help="Folder name in data/, or 'all'")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("ask", help="Ask one question as text")
    p.add_argument("machine")
    p.add_argument("question")
    p.add_argument("--no-sources", action="store_true")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("chat", help="Type questions in a loop")
    p.add_argument("machine")
    p.add_argument("--no-sources", action="store_true")
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("voice", help="Push-to-talk voice assistant")
    p.add_argument("machine")
    p.add_argument("--no-sources", action="store_true")
    p.set_defaults(func=cmd_voice)

    p = sub.add_parser("machines", help="List machines in data/")
    p.set_defaults(func=lambda _a: print("\n".join(list_machines()) or "(none)"))

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (FileNotFoundError, RuntimeError, ValueError) as err:
        sys.exit(f"Error: {err}")
    except Exception as err:  # most often: Ollama isn't running
        if "connect" in type(err).__name__.lower() or "connection" in str(err).lower():
            sys.exit(f"Can't reach Ollama at {settings.ollama_url}. Start the Ollama app (or run 'ollama serve') and try again.")
        raise


if __name__ == "__main__":
    main()
