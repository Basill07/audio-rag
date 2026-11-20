"""Check how well the assistant answers a set of test questions.

    python scripts/evaluate.py station3

For each question it checks:
  - retrieval: did one of the top chunks come from the expected section?
  - answer:    does the answer contain at least one expected keyword?
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audio_rag.config import settings  # noqa: E402
from audio_rag.rag import MachineAssistant  # noqa: E402


def main(machine: str) -> None:
    cases = json.loads((Path(__file__).resolve().parent.parent / "eval" / f"{machine}.json").read_text())
    assistant = MachineAssistant(machine)

    retrieval_ok = answer_ok = 0
    retrieval_total = 0
    times = []
    for case in cases:
        t0 = time.perf_counter()
        result = assistant.ask(case["question"])
        times.append(time.perf_counter() - t0)

        hit = None
        if case["expect_section"]:
            retrieval_total += 1
            hit = any(case["expect_section"].lower() in (s.section + " " + s.text).lower() for s in result.sources)
            retrieval_ok += hit
        good = any(k.lower() in result.answer.lower() for k in case["answer_keywords"])
        answer_ok += good

        mark = lambda ok: "-" if ok is None else ("OK " if ok else "MISS")  # noqa: E731
        print(f"[retrieval {mark(hit)}] [answer {mark(good)}] {case['question']}")
        if not good:
            print(f"      answer: {result.answer[:160]}")

    n = len(cases)
    print("\n--- Summary ---")
    print(f"LLM: {settings.llm_model}   embeddings: {settings.embed_model}   top_k: {settings.top_k}")
    print(f"Retrieval hit rate: {retrieval_ok}/{retrieval_total} ({100 * retrieval_ok / max(retrieval_total, 1):.0f}%)")
    print(f"Answer keyword match: {answer_ok}/{n} ({100 * answer_ok / n:.0f}%)")
    print(f"Average answer time: {sum(times) / n:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "station3")
