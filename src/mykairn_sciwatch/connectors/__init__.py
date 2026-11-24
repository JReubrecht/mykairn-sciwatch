"""
Connecteurs scientifiques multi-sources (PubMed, OpenAlex, Semantic Scholar, Crossref/RSS)
et moteur de dédoublonnage / fusion bibliographique.
"""

from mykairn_sciwatch.connectors.aggregator import MultiSourceAggregator, deduplicate_publications
from mykairn_sciwatch.connectors.crossref_rss import CrossrefRssConnector
from mykairn_sciwatch.connectors.openalex import OpenAlexConnector
from mykairn_sciwatch.connectors.pubmed import PubMedConnector
from mykairn_sciwatch.connectors.semantic_scholar import SemanticScholarConnector

__all__ = [
    "PubMedConnector",
    "OpenAlexConnector",
    "SemanticScholarConnector",
    "CrossrefRssConnector",
    "MultiSourceAggregator",
    "deduplicate_publications",
]
