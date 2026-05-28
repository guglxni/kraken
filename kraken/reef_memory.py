"""Reef Memory — LanceDB vector search over past voyages.

Stores finding payloads as embeddings so the Quartermaster can recall
similar past voyages as few-shot exemplars before dispatching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_REEF_DIR = Path.home() / ".kraken" / "reef"
_TABLE_NAME = "voyages"


class ReefMemory:
    """Vector store for past voyage findings using LanceDB + fastembed."""

    def __init__(self, directory: Path = _REEF_DIR) -> None:
        self.directory = directory
        self._db: Any = None
        self._table: Any = None

    def _connect(self) -> None:
        if self._db is not None:
            return
        try:
            import lancedb  # type: ignore[import]
            self.directory.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self.directory))
            try:
                self._table = self._db.open_table(_TABLE_NAME)
            except Exception:
                self._table = None
        except ImportError:
            logger.warning("lancedb_not_installed", hint="pip install lancedb fastembed")

    def store(self, voyage_id: str, question: str, kind: str, payload: dict[str, Any]) -> None:
        """Embed and store a voyage result for future recall."""
        self._connect()
        if self._db is None:
            return

        try:
            from fastembed import TextEmbedding  # type: ignore[import]
            import json

            model = TextEmbedding("BAAI/bge-small-en-v1.5")
            text = f"{kind}: {question}"
            embedding = list(next(model.embed([text])))

            row = {
                "voyage_id": voyage_id,
                "question": question,
                "kind": kind,
                "payload": json.dumps(payload),
                "vector": embedding,
            }

            if self._table is None:
                self._table = self._db.create_table(_TABLE_NAME, data=[row])
            else:
                self._table.add([row])

            logger.info("reef_stored", voyage_id=voyage_id, kind=kind)
        except Exception as exc:
            logger.warning("reef_store_failed", error=str(exc))

    def recall(self, question: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Return the top-K most similar past voyages as few-shot exemplars."""
        self._connect()
        if self._db is None or self._table is None:
            return []

        try:
            from fastembed import TextEmbedding  # type: ignore[import]
            import json

            model = TextEmbedding("BAAI/bge-small-en-v1.5")
            embedding = list(next(model.embed([question])))

            results = (
                self._table.search(embedding)
                .limit(top_k)
                .to_list()
            )

            return [
                {
                    "voyage_id": r["voyage_id"],
                    "question": r["question"],
                    "kind": r["kind"],
                    "payload": json.loads(r["payload"]),
                }
                for r in results
            ]
        except Exception as exc:
            logger.warning("reef_recall_failed", error=str(exc))
            return []


_reef: ReefMemory | None = None


def get_reef() -> ReefMemory:
    global _reef
    if _reef is None:
        _reef = ReefMemory()
    return _reef


def inject_exemplars(voyage_id: str, question: str) -> list[dict[str, Any]]:
    """Hook called by Quartermaster pre-invoke to inject Reef exemplars."""
    return get_reef().recall(question)
