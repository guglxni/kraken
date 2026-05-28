"""Tests for Reef Memory — LanceDB vector search over past voyages.

These tests verify the store/recall interface without requiring lancedb or
fastembed to be installed. They test the graceful degradation path and the
basic object interface.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from kraken.reef_memory import ReefMemory, get_reef, inject_exemplars

# ── Graceful degradation (no lancedb installed) ───────────────────────────────

def test_reef_memory_store_noop_when_lancedb_missing(tmp_path: Path) -> None:
    """store() silently returns when lancedb is not installed."""
    reef = ReefMemory(directory=tmp_path / "reef")
    with patch.dict("sys.modules", {"lancedb": None}):
        # Should not raise
        reef.store("v1", "test question", "hot_deploy", {"rows": []})


def test_reef_memory_recall_empty_when_lancedb_missing(tmp_path: Path) -> None:
    """recall() returns [] when lancedb is not installed."""
    reef = ReefMemory(directory=tmp_path / "reef")
    with patch.dict("sys.modules", {"lancedb": None}):
        result = reef.recall("test question")
    assert result == []


def test_reef_memory_recall_empty_before_any_store(tmp_path: Path) -> None:
    """recall() returns [] when the table hasn't been created yet."""
    reef = ReefMemory(directory=tmp_path / "reef")
    # Don't call store — table should be None
    reef._connect = MagicMock()  # prevent real lancedb connect
    reef._db = None
    result = reef.recall("any question")
    assert result == []


# ── Mock-based store/recall round-trip ───────────────────────────────────────

def _make_mock_lancedb(tmp_path: Path):
    """Build a minimal in-memory mock of lancedb + fastembed."""
    rows: list[dict] = []

    mock_table = MagicMock()
    mock_table.add.side_effect = lambda data: rows.extend(data)
    mock_table.search.return_value.limit.return_value.to_list.return_value = rows[:3]

    mock_db = MagicMock()
    mock_db.open_table.side_effect = Exception("table not found")
    # Capture the initial `data` kwarg passed to create_table
    def _create_table(name: str, data: list | None = None) -> MagicMock:
        if data:
            rows.extend(data)
        return mock_table
    mock_db.create_table.side_effect = _create_table

    mock_lancedb = MagicMock()
    mock_lancedb.connect.return_value = mock_db

    mock_embedding_model = MagicMock()
    mock_embedding_model.embed.return_value = iter([[0.1] * 384])

    mock_fastembed = MagicMock()
    mock_fastembed.TextEmbedding.return_value = mock_embedding_model

    return mock_lancedb, mock_fastembed, rows


def test_reef_memory_store_creates_table(tmp_path: Path) -> None:
    mock_lancedb, mock_fastembed, rows = _make_mock_lancedb(tmp_path)

    reef = ReefMemory(directory=tmp_path / "reef")
    with (
        patch.dict("sys.modules", {"lancedb": mock_lancedb, "fastembed": mock_fastembed}),
    ):
        reef.store("vid-1", "deploy broke prod", "hot_deploy", {"rows": [{"sha": "abc"}]})

    assert len(rows) == 1
    assert rows[0]["voyage_id"] == "vid-1"
    assert rows[0]["kind"] == "hot_deploy"
    assert json.loads(rows[0]["payload"]) == {"rows": [{"sha": "abc"}]}


def test_reef_memory_recall_returns_exemplars(tmp_path: Path) -> None:
    mock_lancedb, mock_fastembed, rows = _make_mock_lancedb(tmp_path)

    reef = ReefMemory(directory=tmp_path / "reef")
    # Pre-populate rows so the mock table search returns them
    rows.extend([
        {
            "voyage_id": "vid-1",
            "question": "deploy broke prod",
            "kind": "hot_deploy",
            "payload": json.dumps({"rows": [{"sha": "abc"}]}),
        }
    ])

    # Make open_table succeed on second call
    mock_db = mock_lancedb.connect.return_value
    mock_table = MagicMock()
    mock_table.search.return_value.limit.return_value.to_list.return_value = rows[:3]
    mock_db.open_table.side_effect = None
    mock_db.open_table.return_value = mock_table

    with (
        patch.dict("sys.modules", {"lancedb": mock_lancedb, "fastembed": mock_fastembed}),
    ):
        results = reef.recall("is the deploy bad?", top_k=3)

    assert len(results) == 1
    assert results[0]["voyage_id"] == "vid-1"
    assert results[0]["kind"] == "hot_deploy"
    assert results[0]["payload"] == {"rows": [{"sha": "abc"}]}


# ── mem0 backend selection + fallback ────────────────────────────────────────

def test_reef_falls_back_to_lancedb_when_mem0_init_fails(tmp_path: Path) -> None:
    """When mem0 init raises, the lancedb path is used instead."""
    mock_lancedb, mock_fastembed, rows = _make_mock_lancedb(tmp_path)

    reef = ReefMemory(directory=tmp_path / "reef")
    # Force mem0 init to fail regardless of whether mem0 is installed.
    with (
        patch.object(reef, "_try_init_mem0", return_value=False),
        patch.dict("sys.modules", {"lancedb": mock_lancedb, "fastembed": mock_fastembed}),
    ):
        reef.store("vid-1", "deploy broke prod", "hot_deploy", {"rows": [{"sha": "abc"}]})

    assert reef._backend == "lancedb"
    assert len(rows) == 1
    assert rows[0]["voyage_id"] == "vid-1"
    # The lancedb mock was actually exercised.
    mock_lancedb.connect.assert_called_once()


def test_reef_mem0_store_and_recall_mapping(tmp_path: Path) -> None:
    """With a mocked mem0 Memory, store→add and recall→search map correctly."""
    mock_mem = MagicMock()
    # search() returns mem0's {"results": [...]} shape with metadata payload.
    mock_mem.search.return_value = {
        "results": [
            {
                "id": "m1",
                "memory": "hot_deploy: deploy broke prod",
                "score": 0.9,
                "metadata": {
                    "voyage_id": "vid-1",
                    "question": "deploy broke prod",
                    "kind": "hot_deploy",
                    "payload": json.dumps({"rows": [{"sha": "abc"}]}),
                },
            }
        ]
    }

    reef = ReefMemory(directory=tmp_path / "reef")

    def _fake_init() -> bool:
        reef._mem = mock_mem
        return True

    with patch.object(reef, "_try_init_mem0", side_effect=_fake_init):
        reef.store("vid-1", "deploy broke prod", "hot_deploy", {"rows": [{"sha": "abc"}]})
        results = reef.recall("is the deploy bad?", top_k=3)

    assert reef._backend == "mem0"

    # store() → add() with text + metadata + user_id + infer=False
    mock_mem.add.assert_called_once()
    _, kwargs = mock_mem.add.call_args
    assert kwargs["user_id"] == "kraken"
    assert kwargs["infer"] is False
    assert kwargs["metadata"]["voyage_id"] == "vid-1"
    assert kwargs["metadata"]["kind"] == "hot_deploy"
    assert json.loads(kwargs["metadata"]["payload"]) == {"rows": [{"sha": "abc"}]}

    # recall() → search() with query + user_id + limit
    mock_mem.search.assert_called_once_with(query="is the deploy bad?", user_id="kraken", limit=3)

    # mapped back to the required dict shape
    assert len(results) == 1
    assert results[0]["voyage_id"] == "vid-1"
    assert results[0]["question"] == "deploy broke prod"
    assert results[0]["kind"] == "hot_deploy"
    assert results[0]["payload"] == {"rows": [{"sha": "abc"}]}


# ── Singleton ──────────────────────────────────────────────────────────────────

def test_get_reef_returns_singleton() -> None:
    r1 = get_reef()
    r2 = get_reef()
    assert r1 is r2


def test_inject_exemplars_returns_list() -> None:
    """inject_exemplars never raises — returns [] on any failure."""
    with patch("kraken.reef_memory.get_reef") as mock_get:
        mock_reef = MagicMock()
        mock_reef.recall.return_value = [{"voyage_id": "x", "kind": "hot_deploy", "question": "q", "payload": {}}]
        mock_get.return_value = mock_reef

        result = inject_exemplars("vid", "did the deploy break things?")

    assert isinstance(result, list)
    assert len(result) == 1
