"""
RDF/Turtle export for KE-WP and KE-GO mapping datasets.

Pure Python module — no Flask dependency. Uses rdflib Graph for valid
Turtle serialisation with full Phase 2/3 provenance columns.
"""
import logging

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import DCTERMS, XSD

logger = logging.getLogger(__name__)

KEWP = Namespace("https://ke-wp-mapping.org/vocab#")
MAPPING = Namespace("https://ke-wp-mapping.org/mapping/")


def generate_ke_wp_turtle(mappings, min_confidence=None) -> str:
    """Generate Turtle content for KE-WP mappings.

    Parameters
    ----------
    mappings:
        List of dicts from MappingModel.get_all_mappings(). Each dict is
        expected to contain: uuid, ke_id, ke_title, wp_id, wp_title,
        confidence_level, approved_by_curator, approved_at_curator,
        suggestion_score.
    min_confidence:
        Optional lowercase string (e.g. "high"). Rows whose confidence_level
        does not match are excluded.

    Returns
    -------
    str
        Turtle-formatted string parseable by rdflib. Empty graph skeleton if
        no rows survive filtering.
    """
    if min_confidence:
        mappings = [
            r for r in mappings
            if r.get("confidence_level", "").lower() == min_confidence
        ]

    g = Graph()
    g.bind("ke-wp", KEWP)
    g.bind("dcterms", DCTERMS)
    g.bind("mapping", MAPPING)

    for row in mappings:
        if not row.get("uuid"):
            continue

        uri = MAPPING[row["uuid"]]
        g.add((uri, RDF.type, KEWP.KeyEventPathwayMapping))
        g.add((uri, DCTERMS.identifier, Literal(row["uuid"])))
        g.add((uri, KEWP.keyEventId, Literal(row["ke_id"])))
        g.add((uri, KEWP.keyEventName, Literal(row["ke_title"])))
        g.add((uri, KEWP.pathwayId, Literal(row["wp_id"])))
        g.add((uri, KEWP.pathwayTitle, Literal(row["wp_title"])))
        g.add((uri, KEWP.confidenceLevel, Literal(row["confidence_level"])))

        if row.get("approved_by_curator"):
            g.add((uri, DCTERMS.creator, Literal(row["approved_by_curator"])))

        if row.get("approved_at_curator"):
            g.add((
                uri,
                DCTERMS.date,
                Literal(row["approved_at_curator"], datatype=XSD.dateTime),
            ))

        if row.get("suggestion_score") is not None:
            g.add((
                uri,
                KEWP.suggestionScore,
                Literal(float(row["suggestion_score"]), datatype=XSD.decimal),
            ))

    return g.serialize(format="turtle")


def generate_ke_go_turtle(mappings, min_confidence=None) -> str:
    """Generate Turtle content for KE-GO mappings.

    Parameters
    ----------
    mappings:
        List of dicts from GoMappingModel.get_all_mappings(). Each dict is
        expected to contain: uuid, ke_id, ke_title, go_id, go_name,
        confidence_level, approved_by_curator, approved_at_curator,
        suggestion_score.
    min_confidence:
        Optional lowercase string for confidence filtering.

    Returns
    -------
    str
        Turtle-formatted string parseable by rdflib.
    """
    if min_confidence:
        mappings = [
            r for r in mappings
            if r.get("confidence_level", "").lower() == min_confidence
        ]

    g = Graph()
    g.bind("ke-wp", KEWP)
    g.bind("dcterms", DCTERMS)
    g.bind("mapping", MAPPING)

    for row in mappings:
        if not row.get("uuid"):
            continue

        uri = MAPPING[row["uuid"]]
        g.add((uri, RDF.type, KEWP.KeyEventGOMapping))
        g.add((uri, DCTERMS.identifier, Literal(row["uuid"])))
        g.add((uri, KEWP.keyEventId, Literal(row["ke_id"])))
        g.add((uri, KEWP.keyEventName, Literal(row["ke_title"])))
        g.add((uri, KEWP.goTermId, Literal(row["go_id"])))
        g.add((uri, KEWP.goTermName, Literal(row["go_name"])))
        g.add((uri, KEWP.confidenceLevel, Literal(row["confidence_level"])))

        if row.get("approved_by_curator"):
            g.add((uri, DCTERMS.creator, Literal(row["approved_by_curator"])))

        if row.get("approved_at_curator"):
            g.add((
                uri,
                DCTERMS.date,
                Literal(row["approved_at_curator"], datatype=XSD.dateTime),
            ))

        if row.get("suggestion_score") is not None:
            g.add((
                uri,
                KEWP.suggestionScore,
                Literal(float(row["suggestion_score"]), datatype=XSD.decimal),
            ))

    return g.serialize(format="turtle")
