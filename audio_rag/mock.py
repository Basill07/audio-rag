"""A tiny keyword-based embedding so tests can run without Ollama.

It hashes words into a fixed-size vector. It's not smart, but questions that share
words with a chunk ("E47", "feeder", "jam") will find that chunk, which is enough
to check that ingestion and retrieval work.
"""

import hashlib
import math
import re

from llama_index.core.base.embeddings.base import BaseEmbedding

_STOP = {"the", "a", "an", "is", "on", "in", "of", "to", "and", "or", "what", "how", "do", "i", "it", "for", "with", "at", "be"}


def _embed(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if word in _STOP:
            continue
        idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class HashEmbedding(BaseEmbedding):
    dim: int = 512

    def _get_query_embedding(self, query: str) -> list[float]:
        return _embed(query, self.dim)

    def _get_text_embedding(self, text: str) -> list[float]:
        return _embed(text, self.dim)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)
