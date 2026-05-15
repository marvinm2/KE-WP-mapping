"""
Regression tests for Plan 32-05 (DEBT-06):

The KE-WP RDF export route MUST return 503 with body
``{"error": "No KE-WP mappings available for RDF export"}`` whenever
there are zero approved mappings — even when ``generate_ke_wp_turtle([])``
emits a non-empty Turtle prelude (rdflib's ``Graph().serialize()`` always
emits ``@prefix`` declarations, so the bare ``st_size == 0`` check is not
sufficient on its own).

The fix is to mirror ``download_ke_reactome_rdf``'s guard:

    if mappings:
        content = generate_ke_wp_turtle(mappings)
        cache_path.write_text(content or "", encoding="utf-8")
    else:
        cache_path.write_text("", encoding="utf-8")
"""

import src.blueprints.main as main_bp_mod


class _EmptyMappingModel:
    """Stand-in for MappingModel that always reports zero rows."""

    def get_all_mappings(self):
        return []


def test_ke_wp_rdf_returns_503_when_no_mappings(client, tmp_path, monkeypatch):
    """With zero mappings and an isolated cache dir, /exports/rdf/ke-wp 503s
    with the canonical error body and writes an empty placeholder file."""
    monkeypatch.setattr(main_bp_mod, "EXPORT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(main_bp_mod, "mapping_model", _EmptyMappingModel())

    response = client.get("/exports/rdf/ke-wp")
    assert response.status_code == 503, (
        f"Expected 503 on empty graph, got {response.status_code}; "
        f"body={response.data!r}"
    )
    body = response.get_json()
    assert body == {"error": "No KE-WP mappings available for RDF export"}, (
        f"Body shape regression: {body!r}"
    )

    # The placeholder cache file MUST be empty (proves the
    # if-mappings short-circuit ran, NOT a prefix-only Turtle blob)
    cache_file = tmp_path / "ke-wp-mappings.ttl"
    assert cache_file.exists()
    assert cache_file.stat().st_size == 0, (
        f"Cache file is non-empty ({cache_file.stat().st_size} bytes) — "
        "this means generate_ke_wp_turtle([]) emitted a non-empty "
        "prelude and was NOT short-circuited. The 503 check would "
        "bypass on subsequent requests."
    )


def test_ke_wp_rdf_503_when_generator_emits_prelude_only(client, tmp_path, monkeypatch):
    """Guards against the case where generate_ke_wp_turtle([]) returns
    a non-empty ``@prefix`` prelude. The route MUST short-circuit BEFORE
    invoking the generator on empty mappings, not rely on st_size of the
    serialised result.
    """
    monkeypatch.setattr(main_bp_mod, "EXPORT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(main_bp_mod, "mapping_model", _EmptyMappingModel())

    # Force the generator to return a non-empty prelude for empty input.
    # The exporter module is imported INSIDE the route, so we patch at the
    # source module path so the late-bound import sees our replacement.
    monkeypatch.setattr(
        "src.exporters.rdf_exporter.generate_ke_wp_turtle",
        lambda mappings: (
            "@prefix dc: <http://purl.org/dc/elements/1.1/> .\n"
            if not mappings else ""
        ),
    )

    response = client.get("/exports/rdf/ke-wp")
    assert response.status_code == 503, (
        f"Expected 503 even when generator emits prelude, got "
        f"{response.status_code}; body={response.data!r}"
    )
    assert response.get_json() == {
        "error": "No KE-WP mappings available for RDF export"
    }


# ---------------------------------------------------------------------------
# Plan 32-06 (DEBT-05): sibling tests for KE-GO RDF export route.
# Same contract as the WP tests above, ported verbatim with go_mapping_model
# substitution. See Plan 32-06-PLAN.md for context.
# ---------------------------------------------------------------------------


class _EmptyGoMappingModel:
    """Stand-in for GoMappingModel that always reports zero rows."""

    def get_all_mappings(self):
        return []


def test_ke_go_rdf_returns_503_when_no_mappings(client, tmp_path, monkeypatch):
    """With zero GO mappings and an isolated cache dir, /exports/rdf/ke-go
    503s with the canonical error body and writes an empty placeholder file."""
    monkeypatch.setattr(main_bp_mod, "EXPORT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(main_bp_mod, "go_mapping_model", _EmptyGoMappingModel())

    response = client.get("/exports/rdf/ke-go")
    assert response.status_code == 503, (
        f"Expected 503 on empty graph, got {response.status_code}; "
        f"body={response.data!r}"
    )
    body = response.get_json()
    assert body == {"error": "No KE-GO mappings available for RDF export"}, (
        f"Body shape regression: {body!r}"
    )

    cache_file = tmp_path / "ke-go-mappings.ttl"
    assert cache_file.exists()
    assert cache_file.stat().st_size == 0, (
        f"Cache file is non-empty ({cache_file.stat().st_size} bytes) — "
        "this means generate_ke_go_turtle([]) emitted a non-empty "
        "prelude and was NOT short-circuited. The 503 check would "
        "bypass on subsequent requests."
    )


def test_ke_go_rdf_503_when_generator_emits_prelude_only(client, tmp_path, monkeypatch):
    """Guards against the case where generate_ke_go_turtle([]) returns
    a non-empty ``@prefix`` prelude. The route MUST short-circuit BEFORE
    invoking the generator on empty mappings, not rely on st_size of the
    serialised result.
    """
    monkeypatch.setattr(main_bp_mod, "EXPORT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(main_bp_mod, "go_mapping_model", _EmptyGoMappingModel())

    monkeypatch.setattr(
        "src.exporters.rdf_exporter.generate_ke_go_turtle",
        lambda mappings: (
            "@prefix dc: <http://purl.org/dc/elements/1.1/> .\n"
            if not mappings else ""
        ),
    )

    response = client.get("/exports/rdf/ke-go")
    assert response.status_code == 503, (
        f"Expected 503 even when generator emits prelude, got "
        f"{response.status_code}; body={response.data!r}"
    )
    assert response.get_json() == {
        "error": "No KE-GO mappings available for RDF export"
    }
