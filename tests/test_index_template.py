"""Jinja-render smoke tests for templates/index.html.

Phase 27 (Reactome Pathway Viewer) — Wave 0 verification of RVIEW-01 (a):
the #reactome-inline-embed block exists in the rendered DOM and sits between
#duplicate-warning-reactome and #reactome-confidence-guide inside
#reactome-tab-content.
"""


def test_reactome_inline_embed_block_present(client):
    """RVIEW-01 (a): #reactome-inline-embed and its frame exist in rendered HTML."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.data
    assert b'id="reactome-inline-embed"' in body
    assert b'id="reactome-inline-embed-frame"' in body
    # 280px container height (D-02 visual parity with WP)
    assert b"height:280px" in body or b"height: 280px" in body


def test_reactome_inline_embed_block_placement(client):
    """RVIEW-01 (a): block sits between #duplicate-warning-reactome and #reactome-confidence-guide."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    idx_dup = body.find('id="duplicate-warning-reactome"')
    idx_embed = body.find('id="reactome-inline-embed"')
    idx_guide = body.find('id="reactome-confidence-guide"')
    assert idx_dup != -1 and idx_embed != -1 and idx_guide != -1
    assert idx_dup < idx_embed < idx_guide, (
        f"Expected order duplicate-warning-reactome < reactome-inline-embed < "
        f"reactome-confidence-guide; got positions {idx_dup}, {idx_embed}, {idx_guide}"
    )
