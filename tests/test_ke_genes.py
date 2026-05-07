"""Phase 28 — Parser unit tests for get_genes_from_ke().

Covers:
- Strict-triple dict shape (D-02)
- Partial-binding skip (D-04)
- (ncbi, hgnc, symbol) dedupe
- NCBI IRI tail extraction
- HTTP error path returns []
"""
from unittest.mock import MagicMock, patch

from src.suggestions.ke_genes import get_genes_from_ke


def _mock_response(bindings, status_code=200):
    """Build a MagicMock simulating a SPARQL JSON response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"results": {"bindings": bindings}}
    mock_resp.text = ""
    return mock_resp


@patch("src.suggestions.ke_genes.requests.post")
def test_returns_strict_triple_dicts(mock_post):
    """All three fields populated -> exactly one dict in result with NCBI tail extracted."""
    mock_post.return_value = _mock_response([
        {
            "hgnc": {"value": "11892"},
            "symbol": {"value": "TNF"},
            "ncbi": {"value": "https://identifiers.org/ncbigene/7124"},
        },
    ])
    result = get_genes_from_ke("KE 55", "http://test/sparql", None)
    assert result == [{"ncbi": "7124", "hgnc": "11892", "symbol": "TNF"}]


@patch("src.suggestions.ke_genes.requests.post")
def test_drops_partial_bindings(mock_post):
    """D-04 — bindings missing any of the three fields are dropped silently."""
    mock_post.return_value = _mock_response([
        {  # complete — kept
            "hgnc": {"value": "11892"},
            "symbol": {"value": "TNF"},
            "ncbi": {"value": "https://identifiers.org/ncbigene/7124"},
        },
        {  # missing ncbi — dropped
            "hgnc": {"value": "9999"},
            "symbol": {"value": "FOO"},
        },
        {  # missing hgnc — dropped
            "symbol": {"value": "BAR"},
            "ncbi": {"value": "https://identifiers.org/ncbigene/9"},
        },
        {  # missing symbol — dropped
            "hgnc": {"value": "1234"},
            "ncbi": {"value": "https://identifiers.org/ncbigene/100"},
        },
    ])
    result = get_genes_from_ke("KE 55", "http://test/sparql", None)
    assert len(result) == 1
    assert result[0]["symbol"] == "TNF"


@patch("src.suggestions.ke_genes.requests.post")
def test_dedupes_on_triple(mock_post):
    """Identical (ncbi, hgnc, symbol) tuples collapse to one dict."""
    binding = {
        "hgnc": {"value": "11892"},
        "symbol": {"value": "TNF"},
        "ncbi": {"value": "https://identifiers.org/ncbigene/7124"},
    }
    mock_post.return_value = _mock_response([binding, binding, binding])
    result = get_genes_from_ke("KE 55", "http://test/sparql", None)
    assert len(result) == 1


@patch("src.suggestions.ke_genes.requests.post")
def test_extracts_ncbi_id_from_iri(mock_post):
    """NCBI IRI tail extraction (rsplit('/',1)[-1]) yields bare ID."""
    mock_post.return_value = _mock_response([
        {
            "hgnc": {"value": "7872"},
            "symbol": {"value": "NOS1"},
            "ncbi": {"value": "https://identifiers.org/ncbigene/4842"},
        },
    ])
    result = get_genes_from_ke("KE 55", "http://test/sparql", None)
    assert result[0]["ncbi"] == "4842"


@patch("src.suggestions.ke_genes.requests.post")
def test_returns_empty_list_on_http_error(mock_post):
    """Non-200 response -> [] with no exception."""
    mock_post.return_value = _mock_response([], status_code=500)
    result = get_genes_from_ke("KE 55", "http://test/sparql", None)
    assert result == []
