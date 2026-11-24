"""
Connecteur PubMed / NCBI Entrez E-Utilities (ESearch + EFetch XML).
Récupère les métadonnées complètes : PMID, DOI, Titre, Résumé structuré, Auteurs,
Journal, Date, Types de publication (MeSH/PubMed) et descripteurs MeSH.
"""

from __future__ import annotations

import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from mykairn_sciwatch.connectors.base import clean_html_text, http_get_json, http_get_text, normalize_doi
from mykairn_sciwatch.models import RawPublication


MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def parse_pubmed_xml(xml_text: str, query_matched: str = "") -> List[RawPublication]:
    """Parse un flux XML PubmedArticleSet retourné par EFetch."""
    if not xml_text.strip():
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    results: List[RawPublication] = []
    for article_elem in root.findall(".//PubmedArticle"):
        medline = article_elem.find("MedlineCitation")
        if medline is None:
            continue
        pmid_elem = medline.find("PMID")
        pmid = pmid_elem.text.strip() if (pmid_elem is not None and pmid_elem.text) else ""
        if not pmid:
            continue

        art = medline.find("Article")
        if art is None:
            continue

        # Titre
        title_elem = art.find("ArticleTitle")
        raw_title = "".join(title_elem.itertext()) if title_elem is not None else ""
        title = clean_html_text(raw_title).rstrip(".")
        if not title:
            continue

        # Résumé (avec support des sections structurées BACKGROUND, METHODS, RESULTS, CONCLUSIONS)
        abstract_parts: List[str] = []
        for ab_node in art.findall(".//Abstract/AbstractText"):
            label = ab_node.attrib.get("Label") or ab_node.attrib.get("NlmCategory")
            part_text = clean_html_text("".join(ab_node.itertext()))
            if part_text:
                if label and label.upper() not in ("UNLABELLED", "UNASSIGNED"):
                    abstract_parts.append(f"{label.title()}: {part_text}")
                else:
                    abstract_parts.append(part_text)
        abstract = " ".join(abstract_parts)

        # Journal
        journal_title = ""
        j_elem = art.find("Journal/Title")
        if j_elem is not None and j_elem.text:
            journal_title = clean_html_text(j_elem.text)
        else:
            iso_elem = art.find("Journal/ISOAbbreviation")
            if iso_elem is not None and iso_elem.text:
                journal_title = clean_html_text(iso_elem.text)

        # Date de publication
        pub_year = 0
        pub_month = "01"
        pub_day = "01"
        pub_date_node = art.find("Journal/JournalIssue/PubDate")
        if pub_date_node is not None:
            y_node = pub_date_node.find("Year")
            if y_node is not None and y_node.text and y_node.text.isdigit():
                pub_year = int(y_node.text)
            else:
                medline_date = pub_date_node.find("MedlineDate")
                if medline_date is not None and medline_date.text:
                    for token in medline_date.text.split():
                        if len(token) >= 4 and token[:4].isdigit():
                            pub_year = int(token[:4])
                            break
            m_node = pub_date_node.find("Month")
            if m_node is not None and m_node.text:
                m_raw = m_node.text.strip().lower()[:3]
                if m_raw.isdigit():
                    pub_month = f"{int(m_raw):02d}"
                elif m_raw in MONTH_MAP:
                    pub_month = MONTH_MAP[m_raw]
            d_node = pub_date_node.find("Day")
            if d_node is not None and d_node.text and d_node.text.strip().isdigit():
                pub_day = f"{int(d_node.text.strip()):02d}"

        # ArticleDate (électronique) si plus précise
        art_date_node = art.find("ArticleDate")
        if art_date_node is not None:
            ay = art_date_node.find("Year")
            am = art_date_node.find("Month")
            ad = art_date_node.find("Day")
            if ay is not None and ay.text and ay.text.isdigit():
                if pub_year == 0:
                    pub_year = int(ay.text)
                if am is not None and am.text and am.text.isdigit():
                    pub_month = f"{int(am.text):02d}"
                if ad is not None and ad.text and ad.text.isdigit():
                    pub_day = f"{int(ad.text):02d}"

        if pub_year == 0:
            pub_year = datetime.now(timezone.utc).year
        publication_date = f"{pub_year:04d}-{pub_month}-{pub_day}"

        # Auteurs
        authors: List[str] = []
        for auth in art.findall(".//AuthorList/Author"):
            last = auth.findtext("LastName", "").strip()
            init = auth.findtext("Initials", "").strip() or auth.findtext("ForeName", "").strip()
            if last:
                authors.append(f"{last} {init}".strip())

        # Types de publication PubMed
        pub_types: List[str] = []
        for pt in art.findall(".//PublicationTypeList/PublicationType"):
            if pt.text and pt.text.strip():
                pub_types.append(pt.text.strip())

        # Termes MeSH
        mesh_terms: List[str] = []
        for mh in medline.findall(".//MeshHeadingList/MeshHeading/DescriptorName"):
            if mh.text and mh.text.strip():
                mesh_terms.append(mh.text.strip())

        # Mots-clés auteur
        for kw in medline.findall(".//KeywordList/Keyword"):
            if kw.text and kw.text.strip():
                mesh_terms.append(kw.text.strip())

        # DOI & PMC (Open Access)
        doi: Optional[str] = None
        pmc_id: Optional[str] = None
        for id_node in article_elem.findall(".//PubmedData/ArticleIdList/ArticleId"):
            id_type = id_node.attrib.get("IdType", "").lower()
            if id_type == "doi" and id_node.text:
                doi = normalize_doi(id_node.text)
            elif id_type == "pmc" and id_node.text:
                pmc_id = id_node.text.strip()

        if not doi:
            for eloc in art.findall("ELocationID"):
                if eloc.attrib.get("EIdType", "").lower() == "doi" and eloc.text:
                    doi = normalize_doi(eloc.text)

        pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/pdf/" if pmc_id else None

        results.append(
            RawPublication(
                source="pubmed",
                external_id=f"pmid:{pmid}",
                title=title,
                abstract=abstract,
                authors=authors[:12],
                journal=journal_title,
                publication_date=publication_date,
                publication_year=pub_year,
                doi=doi,
                pmid=pmid,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                pdf_url=pdf_url,
                citation_count=0,
                raw_publication_types=pub_types,
                mesh_terms=list(dict.fromkeys(mesh_terms)),
                is_open_access=bool(pmc_id),
                query_matched=query_matched,
            )
        )

    return results


class PubMedConnector:
    """Client pour l'API NCBI Entrez E-Utilities (PubMed)."""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, api_key: str = "", email: str = "contact@mykairn.fr") -> None:
        self.api_key = api_key
        self.email = email

    def search_and_fetch(
        self,
        query: str,
        max_results: int = 25,
        start_year: int = 2015,
        lookback_days: Optional[int] = None,
        sort: str = "relevance",
    ) -> List[RawPublication]:
        """Recherche des PMIDs avec ESearch puis récupère leurs fiches XML avec EFetch."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": str(max_results),
            "sort": sort,
            "email": self.email,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        if lookback_days is not None and lookback_days > 0:
            since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y/%m/%d")
            today = datetime.now(timezone.utc).strftime("%Y/%m/%d")
            params["mindate"] = since
            params["maxdate"] = today
            params["datetype"] = "pdat"
        elif start_year > 0:
            params["mindate"] = f"{start_year}/01/01"
            params["maxdate"] = "3000/12/31"
            params["datetype"] = "pdat"

        esearch_url = f"{self.BASE_URL}/esearch.fcgi?{urllib.parse.urlencode(params)}"
        data = http_get_json(esearch_url)
        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        # Respect du rate limit NCBI (3 req/s sans clé, 10 req/s avec clé)
        time.sleep(0.15 if self.api_key else 0.35)

        efetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml",
            "email": self.email,
        }
        if self.api_key:
            efetch_params["api_key"] = self.api_key

        efetch_url = f"{self.BASE_URL}/efetch.fcgi?{urllib.parse.urlencode(efetch_params)}"
        xml_text = http_get_text(efetch_url)
        return parse_pubmed_xml(xml_text, query_matched=query)
