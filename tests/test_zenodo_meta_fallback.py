"""#158 follow-up — EACCES fallback for data/zenodo_meta.json writes.

The container user can't write the gluster-backed /app/data mount, so a
successful Zenodo publish would silently drop the local meta JSON. The
fallback writes to /tmp/zenodo_meta_pending.json and returns its path
loudly so the operator can copy it back.
"""
import os
import stat


from src.exporters import zenodo_uploader
from src.exporters.zenodo_uploader import persist_meta_with_fallback


PAYLOAD = {
    "deposition_id": 20184796,
    "doi": "10.5281/zenodo.20184796",
    "concept_doi": "10.5281/zenodo.20184643",
    "published_at": "2026-05-14",
}


def test_writes_to_target_when_dir_is_writable(tmp_path):
    target = tmp_path / "zenodo_meta.json"
    written = persist_meta_with_fallback(target, PAYLOAD)
    assert written == target
    assert target.exists()
    body = target.read_text()
    assert "20184796" in body


def test_falls_back_to_tmp_on_eacces(tmp_path, monkeypatch, caplog):
    """If the target dir is read-only, the helper writes to /tmp/ and
    returns the fallback Path. The deposit-success path must keep going.
    """
    readonly = tmp_path / "data"
    readonly.mkdir()
    os.chmod(readonly, stat.S_IRUSR | stat.S_IXUSR)  # r-x------
    target = readonly / "zenodo_meta.json"

    # Redirect the fallback to a tmp_path so we don't litter /tmp across runs.
    fallback = tmp_path / "fallback.json"
    monkeypatch.setattr(zenodo_uploader, "META_FALLBACK_PATH", fallback)

    try:
        with caplog.at_level("ERROR", logger=zenodo_uploader.__name__):
            written = persist_meta_with_fallback(target, PAYLOAD)
        assert written == fallback
        assert fallback.exists()
        assert "20184796" in fallback.read_text()
        # Loud log so the operator notices.
        assert any("EACCES" in rec.getMessage() for rec in caplog.records)
    finally:
        # Restore so pytest can clean up tmp_path.
        os.chmod(readonly, stat.S_IRWXU)
