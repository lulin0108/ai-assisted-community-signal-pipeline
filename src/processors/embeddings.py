"""Embedding providers for model artifacts and clustering."""

import hashlib
import re
from typing import Protocol


DEFAULT_EMBEDDING_BACKEND = "hashing"
DEFAULT_TRANSFORMER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HASHING_EMBEDDING_DIMENSIONS = 64


class EmbeddingProvider(Protocol):
    artifact_model_name: str
    artifact_model_version: str
    model_identifier: str
    grouping_basis: str

    def vector(self, item: dict) -> list[float]:
        ...

    def payload(self, item: dict) -> dict:
        ...

    def dimensions(self, item: dict) -> int:
        ...

    def model_label(self) -> str:
        ...


class HashingEmbeddingProvider:
    artifact_model_name = "hashed-text-embedding"
    artifact_model_version = "v1"
    model_identifier = "sparse_hashing"
    grouping_basis = "pain mechanism candidate buckets plus hashed embedding cosine connected components"

    def vector(self, item: dict) -> list[float]:
        tokens = _tokens_for_embedding(item)
        vector = [0.0] * HASHING_EMBEDDING_DIMENSIONS
        for token in tokens:
            vector[_stable_index(token, HASHING_EMBEDDING_DIMENSIONS)] += 1.0
        return _normalize(vector)

    def payload(self, item: dict) -> dict:
        tokens = _tokens_for_embedding(item)
        vector = [round(value, 6) for value in self.vector(item)]
        nonzero_indices = [index for index, value in enumerate(vector) if value]
        return {
            "embedding_type": "sparse_hashing",
            "dimensions": HASHING_EMBEDDING_DIMENSIONS,
            "nonzero_indices": nonzero_indices,
            "values": [vector[index] for index in nonzero_indices],
            "top_terms": top_terms([item]),
            "token_count": len(tokens),
            "source_text_fields": ["title", "clean_text", "relevance_reasons", "quality_reasons"],
        }

    def dimensions(self, item: dict) -> int:
        return HASHING_EMBEDDING_DIMENSIONS

    def model_label(self) -> str:
        return f"{self.artifact_model_name}@{self.artifact_model_version}"


class SentenceTransformerEmbeddingProvider:
    artifact_model_name = "sentence-transformer-embedding"
    artifact_model_version = "v1"
    grouping_basis = "pain mechanism candidate buckets plus transformer embedding cosine connected components"

    def __init__(self, model_identifier: str = DEFAULT_TRANSFORMER_MODEL) -> None:
        self.model_identifier = model_identifier
        self._model = None
        self._vectors: dict[str, list[float]] = {}

    def vector(self, item: dict) -> list[float]:
        item_id = item["item_id"]
        if item_id not in self._vectors:
            vector = self._model_instance().encode(_item_text(item), normalize_embeddings=True)
            self._vectors[item_id] = [float(value) for value in vector.tolist()]
        return self._vectors[item_id]

    def payload(self, item: dict) -> dict:
        tokens = _tokens_for_embedding(item)
        vector = [round(value, 6) for value in self.vector(item)]
        return {
            "embedding_type": "dense_transformer",
            "dimensions": len(vector),
            "values": vector,
            "top_terms": top_terms([item]),
            "token_count": len(tokens),
            "model_identifier": self.model_identifier,
            "source_text_fields": ["title", "clean_text", "relevance_reasons", "quality_reasons"],
        }

    def dimensions(self, item: dict) -> int:
        return len(self.vector(item))

    def model_label(self) -> str:
        return f"{self.artifact_model_name}@{self.artifact_model_version}:{self.model_identifier}"

    def _model_instance(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "Install sentence-transformers to use --embedding-backend sentence-transformer."
                ) from exc
            self._model = SentenceTransformer(self.model_identifier)
        return self._model


def build_embedding_provider(backend: str, model_identifier: str = "") -> EmbeddingProvider:
    if backend == "hashing":
        return HashingEmbeddingProvider()
    if backend == "sentence-transformer":
        return SentenceTransformerEmbeddingProvider(model_identifier or DEFAULT_TRANSFORMER_MODEL)
    raise ValueError(f"Unsupported embedding backend: {backend}")


def top_terms(items: list[dict]) -> list[str]:
    counter: dict[str, int] = {}
    for item in items:
        for token in re.findall(r"[a-z][a-z0-9-]{2,}", _item_text(item)):
            if token not in STOPWORDS:
                counter[token] = counter.get(token, 0) + 1
    return [
        term
        for term, _ in sorted(counter.items(), key=lambda value: (-value[1], value[0]))[:8]
    ]


def _tokens_for_embedding(item: dict) -> list[str]:
    tokens = []
    for token in re.findall(r"[a-z][a-z0-9-]{2,}", _item_text(item)):
        if token not in STOPWORDS:
            tokens.append(token)
    return tokens


def _item_text(item: dict) -> str:
    return " ".join(
        [
            item.get("title", ""),
            item.get("clean_text", ""),
            item.get("relevance_reasons", ""),
            item.get("quality_reasons", ""),
        ]
    ).lower()


def _stable_index(value: str, dimensions: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % dimensions


def _normalize(vector: list[float]) -> list[float]:
    norm = sum(value * value for value in vector) ** 0.5
    if not norm:
        return vector
    return [value / norm for value in vector]


STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "because",
    "before",
    "but",
    "can",
    "for",
    "from",
    "have",
    "how",
    "into",
    "our",
    "still",
    "scope",
    "that",
    "the",
    "their",
    "terms",
    "this",
    "too",
    "use",
    "using",
    "with",
    "without",
}
