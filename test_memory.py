from memory.store import MemoryStore

def test_memory_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("BERON_DB_PATH", str(db))
    m = MemoryStore()
    m.add("user", "hello")
    assert m.recent(1)[0]["content"] == "hello"
