"""
Connecteur Crossref REST API & Flux RSS de revues scientifiques.
Permet d'enrichir la veille avec les derniers articles publiés par les revues
majeures (Sports Medicine, IJSPP, Frontiers, JAP, MSSE, etc.).
"""

from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from mykairn_sciwatch.connectors.base import clean_html_text, http_get_json, http_get_text, normalize_doi
from mykairn_sciwatch.models import RawPublication


class CrossrefRssConnector:
    """Client pour Crossref API (/works) et les flux RSS/Atom de revues scientifiques."""

    CROSSREF_URL = "https://api.crossref.org/works"

    def __init__(self, email: str = "contact@mykairn.fr") -> None:
        self.email = email

    def search_crossref(
        self,
        query: str,
        max_results: int = 15,
        start_year: int = 2015,
        lookback_days: Optional[int] = None,
    ) -> List[RawPublication]:
        """Recherche des publications dans Crossref avec filtre de date."""
        clean_q = (
            query.replace("AND", " ")
            .replace("OR", " ")
            .replace("(", " ")
            .replace(")", " ")
            .replace('"', " ")
        )
        clean_q = " ".join(clean_q.split()[:12])

        if lookback_days is not None and lookback_days > 0:
            since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        else:
            since = f"{start_year}-01-01"

        params = {
            "query.bibliographic": clean_q,
            "filter": f"from-pub-date:{since},type:journal-article",
            "rows": str(min(max_results, 30)),
            "mailto": self.email,
        }
        url = f"{self.CROSSREF_URL}?{urllib.parse.urlencode(params)}"
        try:
            data = http_get_json(url, timeout=15, retries=1)
        except Exception:
            return []

        items = data.get("message", {}).get("items", [])
        results: List[RawPublication] = []
        for item in items:
            parsed = self._parse_crossref_item(item, query_matched=query)
            if parsed:
                results.append(parsed)
        return results

    @staticmethod
    def _parse_crossref_item(item: Dict[str, Any], query_matched: str = "") -> Optional[RawPublication]:
        titles = item.get("title") or []
        title = clean_html_text(titles[0] if titles else "")
        if not title:
            return None

        doi = normalize_doi(item.get("DOI"))
        abstract = clean_html_text(str(item.get("abstract") or ""))

        container = item.get("container-title") or []
        journal = clean_html_text(container[0] if container else "")

        authors: List[str] = []
        for auth in (item.get("author") or [])[:12]:
            family = str(auth.get("family") or "").strip()
            given = str(auth.get("given") or "").strip()
            if family:
                authors.append(f"{family} {given[:1]}".strip())

        # Extraction date
        pub_year = 0
        pub_month = 1
        pub_day = 1
        for date_field in ("published-online", "published-print", "issued", "created"):
            date_parts = (item.get(date_field) or {}).get("date-parts", [])
            if date_parts and isinstance(date_parts[0], list) and date_parts[0]:
                parts = date_parts[0]
                if len(parts) >= 1 and isinstance(parts[0], int):
                    pub_year = parts[0]
                if len(parts) >= 2 and isinstance(parts[1], int):
                    pub_month = parts[1]
                if len(parts) >= 3 and isinstance(parts[2], int):
                    pub_day = parts[2]
                break

        if not pub_year:
            pub_year = datetime.now(timezone.utc).year
        pub_date = f"{pub_year:04d}-{pub_month:02d}-{pub_day:02d}"

        return RawPublication(
            source="crossref",
            external_id=f"crossref:{doi or title[:40]}",
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal,
            publication_date=pub_date,
            publication_year=pub_year,
            doi=doi,
            url=str(item.get("URL") or (f"https://doi.org/{doi}" if doi else "")),
            citation_count=int(item.get("is-referenced-by-count") or 0),
            raw_publication_types=[str(item.get("type") or "journal-article")],
            concepts=[str(s) for s in (item.get("subject") or [])[:6]],
            query_matched=query_matched,
        )

    def fetch_rss_feeds(self, feeds: List[Dict[str, str]]) -> List[RawPublication]:
        """Parse une liste de flux RSS/Atom de revues scientifiques."""
        results: List[RawPublication] = []
        for feed in feeds:
            feed_url = feed.get("url", "").strip()
            feed_name = feed.get("name", "RSS Journal")
            if not feed_url:
                continue
            try:
                xml_text = http_get_text(feed_url, timeout=10, retries=1)
                results.extend(self.parse_rss_xml(xml_text, journal_fallback=feed_name))
            except Exception:
                continue
        return results

    @staticmethod
    def parse_rss_xml(xml_text: str, journal_fallback: str = "RSS Feed") -> List[RawPublication]:
        """Parse un flux XML RSS 2.0, RDF ou Atom."""
        if not xml_text.strip():
            return []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        items: List[RawPublication] = []
        now_year = datetime.now(timezone.utc).year
        now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Parcours générique sans dépendre des préfixes de namespace XML
        for elem in root.iter():
            tag_local = elem.tag.split("}")[-1].lower()
            if tag_local not in ("item", "entry"):
                continue

            title = ""
            desc = ""
            link = ""
            doi: Optional[str] = None

            for child in elem:
                c_tag = child.tag.split("}")[-1].lower()
                c_text = (child.text or "").strip()
                if c_tag == "title" and c_text:
                    title = clean_html_text(c_text)
                elif c_tag in ("description", "summary", "content") and c_text:
                    desc = clean_html_text(c_text)
                elif c_tag == "link":
                    link = c_text or child.attrib.get("href", "").strip()
                elif c_tag in ("identifier", "doi") and "10." in c_text:
                    doi = normalize_doi(c_text)

            if not title:
                continue
            if not doi and "10." in link:
                idx = link.find("10.")
                doi = normalize_doi(link[idx:])

            items.append(
                RawPublication(
                    source="rss",
                    external_id=f"rss:{doi or title[:50]}",
                    title=title,
                    abstract=desc,
                    journal=journal_fallback,
                    publication_date=now_date,
                    publication_year=now_year,
                    doi=doi,
                    url=link or (f"https://doi.org/{doi}" if doi else ""),
                )
            )
        return items
