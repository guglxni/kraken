"""Reef Memory — semantic recall over past voyages.

Primary backend is the mem0 universal memory layer (mem0ai), configured
local-first (no data egress, no LLM extraction required). When mem0 cannot
initialize for any reason — missing LLM key, offline, import failure — the
implementation gracefully falls back to the hand-rolled LanceDB + fastembed
vector store, and finally to a no-op. store()/recall() are always best-effort
and never raise.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import structlog

logger = structlog.get_logger(__name__)

_REEF_DIR = Path.home() / ".kraken" / "reef"
_TABLE_NAME = "voyages"
_EMBED_MODEL_ID = "BAAI/bge-small-en-v1.5"
_MEM0_USER_ID = "kraken"

Backend = Literal["mem0", "lancedb", "noop"]


class ReefMemory:
    """Semantic store for past voyage findings.

    Backend selection (lazy, on first store/recall):
      1. mem0 (local-first config) if it imports and initializes cleanly.
      2. LanceDB + fastembed vector store.
      3. No-op (nothing installed) — store() is silent, recall() returns [].
    """

    def __init__(self, directory: Path = _REEF_DIR) -> None:
        self.directory = directory
        self._backend: Backend | None = None
        # mem0 backend handle
        self._mem: Any = None
        # lancedb fallback handles
        self._db: Any = None
        self._table: Any = None
        self._embed_model: Any = None

    # ── backend selection ─────────────────────────────────────────────────

    def _select_backend(self) -> None:
        """Pick a backend once, lazily. Idempotent."""
        if self._backend is not None:
            return

        if self._try_init_mem0():
            self._backend = "mem0"
            logger.info("reef_backend_selected", backend="mem0")
            return

        if self._try_init_lancedb():
            self._backend = "lancedb"
            logger.info("reef_backend_selected", backend="lancedb")
            return

        self._backend = "noop"
        logger.info("reef_backend_selected", backend="noop")

    def _try_init_mem0(self) -> bool:
        """Attempt a fully-local mem0 init. Returns True on success.

        mem0's default Memory() expects an OpenAI LLM for memory extraction,
        which is unavailable offline. We configure a local-first stack
        (fastembed embeddings + an on-disk vector store) and disable any
        network dependency we can. Because offline init is unreliable, ANY
        exception here is swallowed and we fall back to LanceDB.
        """
        try:
            from mem0 import Memory  # type: ignore[import]

            self.directory.mkdir(parents=True, exist_ok=True)
            # Local-first stack: HuggingFace embeddings (runs offline via
            # sentence-transformers) + FAISS on-disk vector store. No LLM key
            # required because we always call add(..., infer=False) so mem0
            # never invokes its extraction LLM.
            config = {
                "embedder": {
                    "provider": "huggingface",
                    "config": {"model": _EMBED_MODEL_ID},
                },
                "vector_store": {
                    "provider": "faiss",
                    "config": {
                        "collection_name": _TABLE_NAME,
                        "path": str(self.directory / "mem0_faiss"),
                    },
                },
            }
            self._mem = Memory.from_config(config)
            return True
        except Exception as exc:
            # Missing LLM key, missing optional deps, offline, schema drift —
            # all non-fatal; fall back to LanceDB.
            logger.warning("reef_mem0_init_failed", error=str(exc))
            self._mem = None
            return False

    def _try_init_lancedb(self) -> bool:
        """Attempt to connect the LanceDB fallback. Returns True on success."""
        try:
            import lancedb  # type: ignore[import]

            self.directory.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self.directory))
            try:
                self._table = self._db.open_table(_TABLE_NAME)
            except Exception:
                self._table = None
            return True
        except ImportError:
            logger.warning("lancedb_not_installed", hint="pip install lancedb fastembed")
            self._db = None
            return False
        except Exception as exc:
            logger.warning("reef_lancedb_init_failed", error=str(exc))
            self._db = None
            return False

    def _get_embed_model(self) -> Any:
        if self._embed_model is None:
            from fastembed import TextEmbedding  # type: ignore[import]
            self._embed_model = TextEmbedding(_EMBED_MODEL_ID)
        return self._embed_model

    # ── public interface ──────────────────────────────────────────────────

    def store(self, voyage_id: str, question: str, kind: str, payload: dict[str, Any]) -> None:
        """Embed and store a voyage result for future recall. Best-effort."""
        self._select_backend()
        if self._backend == "mem0":
            self._store_mem0(voyage_id, question, kind, payload)
        elif self._backend == "lancedb":
            self._store_lancedb(voyage_id, question, kind, payload)
        # noop: silently return

    def recall(self, question: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Return the top-K most similar past voyages as few-shot exemplars."""
        self._select_backend()
        if self._backend == "mem0":
            return self._recall_mem0(question, top_k)
        if self._backend == "lancedb":
            return self._recall_lancedb(question, top_k)
        return []

    # ── mem0 backend ──────────────────────────────────────────────────────

    def _store_mem0(
        self, voyage_id: str, question: str, kind: str, payload: dict[str, Any]
    ) -> None:
        try:
            text = f"{kind}: {question}"
            metadata = {
                "voyage_id": voyage_id,
                "question": question,
                "kind": kind,
                "payload": json.dumps(payload),
            }
            self._mem.add(
                text,
                user_id=_MEM0_USER_ID,
                metadata=metadata,
                infer=False,
            )
            logger.info("reef_stored", voyage_id=voyage_id, kind=kind, backend="mem0")
        except Exception as exc:
            logger.warning("reef_store_failed", error=str(exc), backend="mem0")

    def _recall_mem0(self, question: str, top_k: int) -> list[dict[str, Any]]:
        try:
            raw = self._mem.search(query=question, user_id=_MEM0_USER_ID, limit=top_k)
            # mem0 returns either a list or {"results": [...]} depending on version.
            results = raw.get("results", []) if isinstance(raw, dict) else raw

            out: list[dict[str, Any]] = []
            for r in results:
                meta = r.get("metadata") or {}
                raw_payload = meta.get("payload", "{}")
                try:
                    payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
                except (ValueError, TypeError):
                    payload = {}
                out.append(
                    {
                        "voyage_id": meta.get("voyage_id", ""),
                        "question": meta.get("question", r.get("memory", "")),
                        "kind": meta.get("kind", ""),
                        "payload": payload,
                    }
                )
            return out
        except Exception as exc:
            logger.warning("reef_recall_failed", error=str(exc), backend="mem0")
            return []

    # ── lancedb fallback backend ──────────────────────────────────────────

    def _store_lancedb(
        self, voyage_id: str, question: str, kind: str, payload: dict[str, Any]
    ) -> None:
        if self._db is None:
            return
        try:
            model = self._get_embed_model()
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

            logger.info("reef_stored", voyage_id=voyage_id, kind=kind, backend="lancedb")
        except Exception as exc:
            logger.warning("reef_store_failed", error=str(exc), backend="lancedb")

    def _recall_lancedb(self, question: str, top_k: int) -> list[dict[str, Any]]:
        if self._db is None or self._table is None:
            return []
        try:
            model = self._get_embed_model()
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
            logger.warning("reef_recall_failed", error=str(exc), backend="lancedb")
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
