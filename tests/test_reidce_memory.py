from pathlib import Path

from reidce.memory import MemoryStore


def test_memory_store_add_and_search(tmp_path: Path) -> None:
    store = MemoryStore()
    store.add("Topology optimization improved with stiffness and slenderness scoring", tags=["topology"])
    store.add("CAD geometry memory created for actuator envelope", tags=["geometry"])
    store.add("Manufacturing gate requires tolerance evidence", tags=["manufacturing", "qa"])

    results = store.search("stiffness slenderness", top_k=2)
    assert results
    assert "Topology optimization" in results[0].record.text

    filtered = store.search("tolerance", required_tags=["manufacturing"])
    assert filtered
    assert "tolerance" in filtered[0].record.text.lower()

    path = tmp_path / "memory.jsonl"
    store.save(path)

    loaded = MemoryStore(path)
    reload_results = loaded.search("actuator envelope", top_k=1)
    assert reload_results
    assert "CAD geometry" in reload_results[0].record.text
