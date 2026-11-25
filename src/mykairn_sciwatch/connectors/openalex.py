"""
Connecteur OpenAlex REST API (https://api.openalex.org/works).
Couvre tous les domaines scientifiques (sciences du sport, médecine, IA, ingénierie, écologie),
fournit le nombre de citations, le statut Open Access, les concepts et reconstruit le résumé intégral.
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from mykairn_sciwatch.connectors.base import clean_html_text, http_get_json, normalize_doi
from mykairn_sciwatch.models import RawPublication
from mykairn_sciwatch.search_syntax import compile_for_openalex


def reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    """Reconstruit le texte d'un résumé à partir de l'index inversé OpenAlex."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    pos_map: Dict[int, str] = {}
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            for pos in positions:
                if isinstance(pos, int):
                    pos_map[pos] = word
    if not pos_map:
        return ""
    ordered = [pos_map[idx] for idx in sorted(pos_map.keys())]
    return clean_html_text(" ".join(ordered))


def parse_openalex_work(work: Dict[str, Any], query_matched: str = "") -> Optional[RawPublication]:
    """Convertit un objet Work OpenAlex en RawPublication."""
    title = clean_html_text(work.get("title") or work.get("display_name") or "")
    if not title:
        return None

    oa_id = str(work.get("id", "")).split("/")[-1]
    doi = normalize_doi(work.get("doi"))

    ids = work.get("ids") or {}
    pmid_raw = str(ids.get("pmid") or "")
    pmid = pmid_raw.rstrip("/").split("/")[-1] if pmid_raw else None
    if pmid and not pmid.isdigit():
        pmid = None

    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))

    # Journal / Source
    journal = ""
    primary_loc = work.get("primary_location") or {}
    source_info = primary_loc.get("source") or {}
    if source_info.get("display_name"):
        journal = str(source_info["display_name"])

    # Auteurs
    authors: List[str] = []
    for auth in (work.get("authorships") or [])[:12]:
        a_obj = auth.get("author") or {}
        if a_obj.get("display_name"):
            authors.append(str(a_obj["display_name"]))

    pub_date = str(work.get("publication_date") or "")
    pub_year = int(work.get("publication_year") or 0)
    if not pub_year and len(pub_date) >= 4 and pub_date[:4].isdigit():
        pub_year = int(pub_date[:4])
    if not pub_date and pub_year:
        pub_date = f"{pub_year:04d}-01-01"

    cited_by = int(work.get("cited_by_count") or 0)

    # Types et concepts
    pub_types: List[str] = []
    if work.get("type"):
        pub_types.append(str(work["type"]))
    if work.get("type_crossref"):
        pub_types.append(str(work["type_crossref"]))

    concepts: List[str] = []
    for topic in (work.get("topics") or [])[:6]:
        if topic.get("display_name"):
            concepts.append(str(topic["display_name"]))
    for concept in (work.get("concepts") or [])[:6]:
        if concept.get("display_name"):
            concepts.append(str(concept["display_name"]))

    oa_info = work.get("open_access") or {}
    is_oa = bool(oa_info.get("is_oa"))
    pdf_url = oa_info.get("oa_url") or primary_loc.get("pdf_url")

    landing_url = (
        primary_loc.get("landing_page_url")
        or (f"https://doi.org/{doi}" if doi else "")
        or str(work.get("id") or "")
    )

    return RawPublication(
        source="openalex",
        external_id=f"openalex:{oa_id}",
        title=title,
        abstract=abstract,
        authors=authors,
        journal=journal,
        publication_date=pub_date,
        publication_year=pub_year,
        doi=doi,
        pmid=pmid,
        url=landing_url,
        pdf_url=pdf_url,
        citation_count=cited_by,
        raw_publication_types=list(dict.fromkeys(pub_types)),
        concepts=list(dict.fromkeys(concepts)),
        is_open_access=is_oa,
        query_matched=query_matched,
    )


class OpenAlexConnector:
    """Client pour l'API OpenAlex Works (Polite Pool avec mailto)."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, email: str = "contact@mykairn.fr") -> None:
        self.email = email

    def search_works(
        self,
        query: str,
        max_results: int = 25,
        start_year: int = 2015,
        end_year: Optional[int] = None,
        lookback_days: Optional[int] = None,
        sort: str = "relevance_score:desc",
        open_access_only: bool = False,
        exclude_preprints: bool = False,
        min_citations: int = 0,
        languages: Optional[List[str]] = None,
    ) -> List[RawPublication]:
        """Interroge OpenAlex Works avec équation booléenne (AND/OR/NOT, parenthèses) et filtres avancés."""
        compiled_q = compile_for_openalex(query)
        filters = ["has_abstract:true"]
        if lookback_days is not None and lookback_days > 0:
            since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
            filters.append(f"from_publication_date:{since}")
        elif start_year > 0:
            filters.append(f"from_publication_date:{start_year}-01-01")
        if end_year and end_year > 0:
            filters.append(f"to_publication_date:{end_year}-12-31")
        if open_access_only:
            filters.append("is_oa:true")
        if exclude_preprints:
            filters.append("type:!preprint")
        if min_citations > 0:
            filters.append(f"cited_by_count:>{min_citations - 1}")
        if languages:
            clean_langs = [l.strip().lower() for l in languages if l.strip()]
            if clean_langs:
                filters.append(f"language:{'|'.join(clean_langs)}")

        params = {
            "search": compiled_q,
            "filter": ",".join(filters),
            "per-page": str(min(max_results, 50)),
            "sort": sort,
            "mailto": self.email,
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        data = http_get_json(url)
        results: List[RawPublication] = []
        for item in data.get("results", []):
            parsed = parse_openalex_work(item, query_matched=query)
            if parsed:
                results.append(parsed)
        return results
