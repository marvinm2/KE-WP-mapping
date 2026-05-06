"""
RDF/Turtle export for KE-WP and KE-GO mapping datasets.

Pure Python module — no Flask dependency. Uses rdflib Graph for valid
Turtle serialisation with full Phase 2/3 provenance columns.
"""
import logging

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import DCTERMS, XSD

logger = logging.getLogger(__name__)

VOCAB = Namespace("https://ke-wp-mapping.org/vocab#")
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
    g.bind("ke-wp", VOCAB)
    g.bind("dcterms", DCTERMS)
    g.bind("mapping", MAPPING)

    for row in mappings:
        if not row.get("uuid"):
            continue

        uri = MAPPING[row["uuid"]]
        g.add((uri, RDF.type, VOCAB.KeyEventPathwayMapping))
        g.add((uri, DCTERMS.identifier, Literal(row["uuid"])))
        g.add((uri, VOCAB.keyEventId, Literal(row["ke_id"])))
        g.add((uri, VOCAB.keyEventName, Literal(row["ke_title"])))
        g.add((uri, VOCAB.pathwayId, Literal(row["wp_id"])))
        g.add((uri, VOCAB.pathwayTitle, Literal(row["wp_title"])))
        g.add((uri, VOCAB.confidenceLevel, Literal(row["confidence_level"])))

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
                VOCAB.suggestionScore,
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
    g.bind("ke-wp", VOCAB)
    g.bind("dcterms", DCTERMS)
    g.bind("mapping", MAPPING)

    for row in mappings:
        if not row.get("uuid"):
            continue

        uri = MAPPING[row["uuid"]]
        g.add((uri, RDF.type, VOCAB.KeyEventGOMapping))
        g.add((uri, DCTERMS.identifier, Literal(row["uuid"])))
        g.add((uri, VOCAB.keyEventId, Literal(row["ke_id"])))
        g.add((uri, VOCAB.keyEventName, Literal(row["ke_title"])))
        g.add((uri, VOCAB.goTermId, Literal(row["go_id"])))
        g.add((uri, VOCAB.goTermName, Literal(row["go_name"])))
        g.add((uri, VOCAB.confidenceLevel, Literal(row["confidence_level"])))

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
                VOCAB.suggestionScore,
                Literal(float(row["suggestion_score"]), datatype=XSD.decimal),
            ))

        if row.get("go_direction"):
            g.add((uri, VOCAB.goDirection, Literal(row["go_direction"])))

        if row.get("go_namespace"):
            g.add((uri, VOCAB.goNamespace, Literal(row["go_namespace"])))

    return g.serialize(format="turtle")


def generate_ke_reactome_turtle(mappings, min_confidence=None, reactome_metadata=None) -> str:
    """Generate Turtle content for KE-Reactome mappings.

    Mirrors generate_ke_go_turtle. Drops goDirection/goNamespace; adds
    species, pathwayDescription (from optional reactome_metadata dict
    keyed by reactome_id).

    Parameters
    ----------
    mappings:
        List of dicts from ReactomeMappingModel.get_all_mappings(). Each
        dict is expected to contain: uuid, ke_id, ke_title, reactome_id,
        pathway_name, species, confidence_level, approved_by_curator,
        approved_at_curator, suggestion_score.
    min_confidence:
        Optional lowercase string for confidence filtering (e.g. "high").
    reactome_metadata:
        Optional dict keyed by reactome_id; each value may carry a
        ``description`` key, which (when present) is emitted as a
        ``vocab#pathwayDescription`` triple.

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
    g.bind("ke-wp", VOCAB)
    g.bind("dcterms", DCTERMS)
    g.bind("mapping", MAPPING)

    for row in mappings:
        if not row.get("uuid"):
            continue

        uri = MAPPING[row["uuid"]]
        g.add((uri, RDF.type, VOCAB.KeyEventReactomeMapping))
        g.add((uri, DCTERMS.identifier, Literal(row["uuid"])))
        g.add((uri, VOCAB.keyEventId, Literal(row["ke_id"])))
        g.add((uri, VOCAB.keyEventName, Literal(row["ke_title"])))
        g.add((uri, VOCAB.reactomeId, Literal(row["reactome_id"])))
        g.add((uri, VOCAB.pathwayName, Literal(row["pathway_name"])))
        g.add((uri, VOCAB.confidenceLevel, Literal(row["confidence_level"])))

        if row.get("species"):
            g.add((uri, VOCAB.species, Literal(row["species"])))

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
                VOCAB.suggestionScore,
                Literal(float(row["suggestion_score"]), datatype=XSD.decimal),
            ))

        if reactome_metadata:
            meta = reactome_metadata.get(row["reactome_id"])
            if meta and meta.get("description"):
                g.add((uri, VOCAB.pathwayDescription, Literal(meta["description"])))

    return g.serialize(format="turtle")
