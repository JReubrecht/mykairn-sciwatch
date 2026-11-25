"""
Connecteur Semantic Scholar Academic Graph API.
Apporte les citations influentes (influentialCitationCount), les résumés TL;DR
et les types d'études académiques.
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mykairn_sciwatch.connectors.base import clean_html_text, http_get_json, normalize_doi
from mykairn_sciwatch.models import RawPublication
from mykairn_sciwatch.search_syntax import (
    S2_PUBLICATION_TYPES,
    compile_for_semantic_scholar_basic,
    compile_for_semantic_scholar_bulk,
)


class SemanticScholarConnector:
    """Client pour Semantic Scholar Graph API v1 (/paper/search/bulk booléen + repli /paper/search)."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    BULK_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
    FIELDS = (
        "paperId,externalIds,url,title,abstract,venue,year,publicationDate,"
        "citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,"
        "publicationTypes,fieldsOfStudy,tldr,authors"
    )

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def search_papers(
        self,
        query: str,
        max_results: int = 20,
        start_year: int = 2015,
        end_year: Optional[int] = None,
        open_access_only: bool = False,
        min_citations: int = 0,
        allowed_pub_types: Optional[List[str]] = None,
    ) -> List[RawPublication]:
        """Recherche des articles sur Semantic Scholar avec support booléen natif (/bulk)."""
        current_year = datetime.now(timezone.utc).year
        upper_year = end_year if (end_year and end_year >= start_year) else current_year
        headers: Dict[str, str] = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        bulk_query = compile_for_semantic_scholar_bulk(query)
        s2_types = list(
            dict.fromkeys(
                S2_PUBLICATION_TYPES[pt]
                for pt in (allowed_pub_types or [])
                if pt in S2_PUBLICATION_TYPES
            )
        )

        bulk_params: Dict[str, str] = {
            "query": bulk_query,
            "fields": self.FIELDS,
            "year": f"{start_year}-{upper_year}",
        }
        if open_access_only:
            bulk_params["openAccessPdf"] = "true"
        if min_citations > 0:
            bulk_params["minCitationCount"] = str(min_citations)
        if s2_types:
            bulk_params["publicationTypes"] = ",".join(s2_types)

        limit = min(max_results, 40)
        items: List[Dict[str, Any]] = []
        bulk_url = f"{self.BULK_URL}?{urllib.parse.urlencode(bulk_params)}"
        try:
            data = http_get_json(bulk_url, headers=headers, timeout=15, retries=1)
            items = list(data.get("data") or [])[:limit]
        except Exception:
            items = []

        if not items:
            compact_query = compile_for_semantic_scholar_basic(query)
            if compact_query:
                basic_params: Dict[str, str] = {
                    "query": compact_query,
                    "limit": str(limit),
                    "fields": self.FIELDS,
                    "year": f"{start_year}-{upper_year}",
                }
                if open_access_only:
                    basic_params["openAccessPdf"] = "true"
                if min_citations > 0:
                    basic_params["minCitationCount"] = str(min_citations)
                if s2_types:
                    basic_params["publicationTypes"] = ",".join(s2_types)
                url = f"{self.BASE_URL}?{urllib.parse.urlencode(basic_params)}"
                try:
                    data = http_get_json(url, headers=headers, timeout=15, retries=1)
                    items = list(data.get("data") or [])[:limit]
                except Exception:
                    return []

        results: List[RawPublication] = []
        for item in items:
            parsed = self._parse_item(item, query_matched=query)
            if parsed:
                results.append(parsed)
        return results

    @staticmethod
    def _parse_item(item: Dict[str, Any], query_matched: str = "") -> Optional[RawPublication]:
        title = clean_html_text(item.get("title") or "")
        if not title:
            return None

        paper_id = str(item.get("paperId") or "")
        ext_ids = item.get("externalIds") or {}
        doi = normalize_doi(ext_ids.get("DOI"))
        pmid = str(ext_ids.get("PubMed") or "").strip() or None

        abstract = clean_html_text(item.get("abstract") or "")
        if not abstract:
            tldr = item.get("tldr") or {}
            if isinstance(tldr, dict) and tldr.get("text"):
                abstract = clean_html_text(str(tldr["text"]))

        authors = [
            str(a.get("name"))
            for a in (item.get("authors") or [])[:12]
            if isinstance(a, dict) and a.get("name")
        ]

        pub_year = int(item.get("year") or 0)
        pub_date = str(item.get("publicationDate") or "")
        if not pub_date and pub_year:
            pub_date = f"{pub_year:04d}-01-01"

        oa_pdf = item.get("openAccessPdf") or {}
        pdf_url = oa_pdf.get("url") if isinstance(oa_pdf, dict) else None

        pub_types = [str(pt) for pt in (item.get("publicationTypes") or []) if pt]
        concepts = [str(f) for f in (item.get("fieldsOfStudy") or []) if f]

        return RawPublication(
            source="semantic_scholar",
            external_id=f"s2:{paper_id}",
            title=title,
            abstract=abstract,
            authors=authors,
            journal=clean_html_text(str(item.get("venue") or "")),
            publication_date=pub_date,
            publication_year=pub_year,
            doi=doi,
            pmid=pmid,
            url=str(item.get("url") or (f"https://doi.org/{doi}" if doi else "")),
            pdf_url=pdf_url,
            citation_count=int(item.get("citationCount") or 0),
            influential_citation_count=int(item.get("influentialCitationCount") or 0),
            raw_publication_types=pub_types,
            concepts=concepts,
            is_open_access=bool(item.get("isOpenAccess")),
            query_matched=query_matched,
        )
