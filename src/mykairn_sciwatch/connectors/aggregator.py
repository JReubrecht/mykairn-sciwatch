"""
Agrégateur multi-sources et moteur de dédoublonnage / fusion bibliographique.
Fusionne les enregistrements issus de PubMed, OpenAlex, Semantic Scholar et Crossref/RSS
par DOI normalisé, PMID ou empreinte de titre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from mykairn_sciwatch.config import AppConfig
from mykairn_sciwatch.connectors.base import normalize_doi, normalize_title_key
from mykairn_sciwatch.connectors.crossref_rss import CrossrefRssConnector
from mykairn_sciwatch.connectors.openalex import OpenAlexConnector
from mykairn_sciwatch.connectors.pedro import PedroConnector
from mykairn_sciwatch.connectors.pubmed import PubMedConnector
from mykairn_sciwatch.connectors.semantic_scholar import SemanticScholarConnector
from mykairn_sciwatch.models import RawPublication, TopicProfile


@dataclass
class MergedPublicationRecord:
    """Publication unifiée après fusion des métadonnées multi-sources."""

    raw: RawPublication
    sources: List[str] = field(default_factory=list)


def _merge_into(target: MergedPublicationRecord, incoming: RawPublication) -> None:
    """Fusionne les métadonnées d'une publication entrante dans un enregistrement existant."""
    if incoming.source not in target.sources:
        target.sources.append(incoming.source)

    base = target.raw
    # Conserver le résumé le plus complet
    if len(incoming.abstract) > len(base.abstract):
        base.abstract = incoming.abstract

    # Identifiants
    if not base.doi and incoming.doi:
        base.doi = incoming.doi
    if not base.pmid and incoming.pmid:
        base.pmid = incoming.pmid

    # URL & PDF Open Access
    if not base.pdf_url and incoming.pdf_url:
        base.pdf_url = incoming.pdf_url
    if incoming.is_open_access:
        base.is_open_access = True
    if incoming.source == "pubmed" and incoming.url:
        base.url = incoming.url
    elif not base.url and incoming.url:
        base.url = incoming.url

    # Journal & Auteurs
    if not base.journal and incoming.journal:
        base.journal = incoming.journal
    if len(incoming.authors) > len(base.authors):
        base.authors = incoming.authors

    # Date plus précise (non 01-01)
    if base.publication_date.endswith("-01-01") and not incoming.publication_date.endswith("-01-01"):
        if incoming.publication_date:
            base.publication_date = incoming.publication_date

    # Citations (prendre le maximum observé entre OpenAlex, S2 et Crossref)
    if incoming.citation_count > base.citation_count:
        base.citation_count = incoming.citation_count
    if incoming.influential_citation_count > base.influential_citation_count:
        base.influential_citation_count = incoming.influential_citation_count
    if incoming.pedro_score is not None:
        if base.pedro_score is None or incoming.pedro_score > base.pedro_score:
            base.pedro_score = incoming.pedro_score

    # Union des types de publication, MeSH et concepts
    base.raw_publication_types = list(
        dict.fromkeys(base.raw_publication_types + incoming.raw_publication_types)
    )
    base.mesh_terms = list(dict.fromkeys(base.mesh_terms + incoming.mesh_terms))
    base.concepts = list(dict.fromkeys(base.concepts + incoming.concepts))


def deduplicate_publications(raw_list: List[RawPublication]) -> List[MergedPublicationRecord]:
    """
    Dédoublonne et fusionne une liste de RawPublication en utilisant une résolution multi-clés :
    1) DOI normalisé
    2) PMID
    3) Empreinte alphanumérique du titre
    """
    merged_records: List[MergedPublicationRecord] = []
    doi_index: Dict[str, int] = {}
    pmid_index: Dict[str, int] = {}
    title_index: Dict[str, int] = {}

    for item in raw_list:
        if not item.title or len(item.title.strip()) < 5:
            continue
        norm_doi = normalize_doi(item.doi)
        item.doi = norm_doi
        pmid = (item.pmid or "").strip() or None
        item.pmid = pmid
        title_key = normalize_title_key(item.title)

        existing_idx: Optional[int] = None
        if norm_doi and norm_doi in doi_index:
            existing_idx = doi_index[norm_doi]
        elif pmid and pmid in pmid_index:
            existing_idx = pmid_index[pmid]
        elif title_key and title_key in title_index:
            existing_idx = title_index[title_key]

        if existing_idx is not None:
            record = merged_records[existing_idx]
            _merge_into(record, item)
            if norm_doi:
                doi_index[norm_doi] = existing_idx
            if pmid:
                pmid_index[pmid] = existing_idx
            if title_key:
                title_index[title_key] = existing_idx
        else:
            new_idx = len(merged_records)
            merged_records.append(MergedPublicationRecord(raw=item, sources=[item.source]))
            if norm_doi:
                doi_index[norm_doi] = new_idx
            if pmid:
                pmid_index[pmid] = new_idx
            if title_key:
                title_index[title_key] = new_idx

    return merged_records


class MultiSourceAggregator:
    """Orchestrateur de collecte scientifique multi-sources (PubMed, OpenAlex, Semantic Scholar, Crossref/RSS)."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.pubmed = PubMedConnector(api_key=config.ncbi_api_key, email=config.ncbi_email)
        self.openalex = OpenAlexConnector(email=config.openalex_email)
        self.s2 = SemanticScholarConnector(api_key=config.s2_api_key)
        self.crossref = CrossrefRssConnector(email=config.openalex_email)
        self.pedro = PedroConnector(ncbi_api_key=config.ncbi_api_key, email=config.ncbi_email)

    def collect_for_profile(
        self,
        profile: TopicProfile,
        mode: str = "audit",
        lookback_days: Optional[int] = None,
        max_per_source: Optional[int] = None,
        enabled_sources: Optional[List[str]] = None,
    ) -> Tuple[List[MergedPublicationRecord], Dict[str, int]]:
        """
        Collecte les publications auprès de toutes les sources activées pour un TopicProfile.
        - En mode 'audit' : combine les articles pertinents récents ET les articles fondateurs les plus cités.
        - En mode 'watch' : cible les nouvelles parutions sur la fenêtre `lookback_days`.
        """
        sources = set(
            enabled_sources
            or profile.enabled_sources
            or ["pubmed", "openalex", "semantic_scholar", "crossref", "pedro", "rss"]
        )
        limit = max_per_source or profile.max_results_per_source
        days = lookback_days if mode == "watch" else None

        active_queries: List[str] = []
        if getattr(profile, "boolean_query", "").strip():
            active_queries.append(profile.boolean_query.strip())
        for q in profile.queries:
            q_s = str(q).strip()
            if q_s and q_s not in active_queries:
                active_queries.append(q_s)
        per_query_limit = max(6, limit // max(1, len(active_queries)))

        all_raw: List[RawPublication] = []
        counts: Dict[str, int] = {s: 0 for s in sources}

        end_year = getattr(profile, "audit_end_year", None)
        humans_only = bool(getattr(profile, "humans_only", False))
        open_access_only = bool(getattr(profile, "open_access_only", False))
        exclude_preprints = bool(getattr(profile, "exclude_preprints", False))
        allowed_pub_types = list(getattr(profile, "allowed_publication_types", []) or [])
        search_languages = list(getattr(profile, "search_languages", []) or [])
        min_citations = int(getattr(profile, "min_citations", 0) or 0)

        for query in active_queries:
            # 1. PubMed (NCBI Entrez)
            if "pubmed" in sources:
                try:
                    pm_sort = "pub+date" if mode == "watch" else "relevance"
                    pm_items = self.pubmed.search_and_fetch(
                        query=query,
                        max_results=per_query_limit,
                        start_year=profile.audit_start_year,
                        end_year=end_year,
                        lookback_days=days,
                        sort=pm_sort,
                        humans_only=humans_only,
                        open_access_only=open_access_only,
                        exclude_preprints=exclude_preprints,
                        allowed_pub_types=allowed_pub_types,
                        languages=search_languages,
                    )
                    all_raw.extend(pm_items)
                    counts["pubmed"] = counts.get("pubmed", 0) + len(pm_items)
                except Exception:
                    pass

            # 2. OpenAlex (Pertinence + Articles fondateurs les plus cités en mode Audit)
            if "openalex" in sources:
                try:
                    oa_sort = "publication_date:desc" if mode == "watch" else "relevance_score:desc"
                    oa_items = self.openalex.search_works(
                        query=query,
                        max_results=per_query_limit,
                        start_year=profile.audit_start_year,
                        end_year=end_year,
                        lookback_days=days,
                        sort=oa_sort,
                        open_access_only=open_access_only,
                        exclude_preprints=exclude_preprints,
                        min_citations=min_citations,
                        languages=search_languages,
                    )
                    all_raw.extend(oa_items)
                    counts["openalex"] = counts.get("openalex", 0) + len(oa_items)

                    if mode == "audit":
                        oa_top_cited = self.openalex.search_works(
                            query=query,
                            max_results=max(5, per_query_limit // 2),
                            start_year=profile.audit_start_year,
                            end_year=end_year,
                            lookback_days=None,
                            sort="cited_by_count:desc",
                            open_access_only=open_access_only,
                            exclude_preprints=exclude_preprints,
                            min_citations=min_citations,
                            languages=search_languages,
                        )
                        all_raw.extend(oa_top_cited)
                        counts["openalex"] = counts.get("openalex", 0) + len(oa_top_cited)
                except Exception:
                    pass

            # 3. Semantic Scholar
            if "semantic_scholar" in sources:
                try:
                    s2_items = self.s2.search_papers(
                        query=query,
                        max_results=max(5, per_query_limit // 2),
                        start_year=profile.audit_start_year,
                        end_year=end_year,
                        open_access_only=open_access_only,
                        min_citations=min_citations,
                        allowed_pub_types=allowed_pub_types,
                    )
                    all_raw.extend(s2_items)
                    counts["semantic_scholar"] = counts.get("semantic_scholar", 0) + len(s2_items)
                except Exception:
                    pass

            # 4. Crossref
            if "crossref" in sources:
                try:
                    cr_items = self.crossref.search_crossref(
                        query=query,
                        max_results=max(5, per_query_limit // 3),
                        start_year=profile.audit_start_year,
                        end_year=end_year,
                        lookback_days=days,
                        exclude_preprints=exclude_preprints,
                    )
                    all_raw.extend(cr_items)
                    counts["crossref"] = counts.get("crossref", 0) + len(cr_items)
                except Exception:
                    pass

            # 5. PEDro (Physiotherapy Evidence Database scope)
            if "pedro" in sources:
                try:
                    pedro_items = self.pedro.search_pedro(
                        query=query,
                        max_results=max(6, per_query_limit // 2),
                        start_year=profile.audit_start_year,
                        end_year=end_year,
                        lookback_days=days,
                        subdiscipline=str(getattr(profile, "pedro_subdiscipline", "") or ""),
                        therapy=str(getattr(profile, "pedro_therapy", "") or ""),
                        min_pedro_score=int(getattr(profile, "pedro_min_score", 0) or 0),
                        humans_only=humans_only,
                        open_access_only=open_access_only,
                        languages=search_languages,
                    )
                    all_raw.extend(pedro_items)
                    counts["pedro"] = counts.get("pedro", 0) + len(pedro_items)
                except Exception:
                    pass

        # 5. Flux RSS des revues configurées
        if "rss" in sources and profile.rss_feeds:
            try:
                rss_items = self.crossref.fetch_rss_feeds(profile.rss_feeds)
                all_raw.extend(rss_items)
                counts["rss"] = counts.get("rss", 0) + len(rss_items)
            except Exception:
                pass

        deduped = deduplicate_publications(all_raw)
        return deduped, counts
