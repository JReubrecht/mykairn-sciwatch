"""
Connecteur PEDro (Physiotherapy Evidence Database — pedro.org.au) & Importateur RIS officiel.

Conformité Fair Use (`https://pedro.org.au/english/about-us/fair-use/`):
- Aucun scraping automatisé ou robot sur search.pedro.org.au.
- La collecte automatique interroge les API ouvertes autorisées (PubMed Entrez + OpenAlex)
  avec le filtre méthodologique validé PEDro (RCT, Essais cliniques contrôlés, Revues systématiques,
  Méta-analyses et Guides de pratique clinique en physiothérapie/rééducation/thérapie par l'exercice),
  complétée par l'import direct de fichiers `.ris` exportés par l'utilisateur depuis `search.pedro.org.au`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from mykairn_sciwatch.connectors.base import clean_html_text, normalize_doi
from mykairn_sciwatch.connectors.openalex import OpenAlexConnector
from mykairn_sciwatch.connectors.pubmed import PubMedConnector
from mykairn_sciwatch.models import RawPublication
from mykairn_sciwatch.search_syntax import (
    PEDRO_SUBDISCIPLINES,
    PEDRO_THERAPIES,
    compile_for_pedro_pubmed,
)


PEDRO_RELEVANCE_TERMS = (
    "physiotherap",
    "physical therapy",
    "rehabilit",
    "exercise therapy",
    "manual therapy",
    "eccentric",
    "strength training",
    "stretching",
    "neuromuscular",
    "injury prevention",
    "tendinopath",
    "musculoskeletal",
    "orthotic",
    "taping",
    "cryotherapy",
    "balneotherapy",
    "mobility",
    "range of motion",
    "propriocept",
)

PEDRO_JOURNALS = (
    "journal of physiotherapy",
    "jospt",
    "journal of orthopaedic & sports physical therapy",
    "physical therapy",
    "british journal of sports medicine",
    "physical therapy in sport",
    "clinical rehabilitation",
    "archives of physical medicine and rehabilitation",
    "manual therapy",
    "musculoskeletal science and practice",
    "sports medicine",
    "scandinavian journal of medicine",
)


def estimate_pedro_scale_10(raw: RawPublication) -> Optional[int]:
    """
    Estime un score indicatif sur l'échelle PEDro (/10) à partir des marqueurs
    méthodologiques explicitement décrits dans le titre/résumé/types d'étude.
    Retourne None pour les revues systématiques/guides (notés N/A sur PEDro).
    """
    if raw.pedro_score is not None:
        return raw.pedro_score

    types_l = " ".join(raw.raw_publication_types).lower()
    text = f"{raw.title} {raw.abstract}".lower()

    if any(k in types_l or k in raw.title.lower() for k in ("systematic review", "meta-analysis", "guideline", "practice guideline")):
        return None

    is_trial = (
        "randomized controlled trial" in types_l
        or "randomised controlled trial" in types_l
        or "clinical trial" in types_l
        or "controlled clinical trial" in types_l
        or "randomized" in text
        or "randomised" in text
        or "randomly assigned" in text
        or "randomly allocated" in text
    )
    if not is_trial:
        return None

    score = 0
    if "random" in text:
        score += 1  # Item 2: Random allocation
    if "concealed" in text or "sealed envelope" in text or "central allocation" in text:
        score += 1  # Item 3: Concealed allocation
    if "baseline" in text and any(w in text for w in ("similar", "comparable", "no difference", "matched")):
        score += 1  # Item 4: Baseline comparability
    if "double-blind" in text or "double blind" in text or "triple-blind" in text:
        score += 2  # Items 5 & 6/7
    elif "single-blind" in text or "assessor blind" in text or "blinded assessor" in text or "blind" in text:
        score += 1  # Item 7: Blind assessors
    if any(w in text for w in ("follow-up", "dropout", "attrition", "retention", "completed the")):
        score += 1  # Item 8: Adequate follow-up
    if "intention-to-treat" in text or "intention to treat" in text or "itt" in re.findall(r"\bitt\b", text):
        score += 1  # Item 9: Intention-to-treat analysis
    if any(w in text for w in ("between-group", "between group", "p <", "p=", "compared with control", "versus control")):
        score += 1  # Item 10: Between-group statistical comparisons
    if any(w in text for w in ("95% ci", "confidence interval", "effect size", "mean difference", "sd", "iqr")):
        score += 1  # Item 11: Point estimates and variability

    return max(2, min(10, score))


class PedroConnector:
    """
    Client spécialisé pour le périmètre PEDro (Physiotherapy Evidence Database).
    Utilise PubMed Entrez + OpenAlex avec filtre méthodologique physiothérapie/EBM.
    """

    def __init__(self, ncbi_api_key: str = "", email: str = "contact@mykairn.fr") -> None:
        self.pubmed = PubMedConnector(api_key=ncbi_api_key, email=email)
        self.openalex = OpenAlexConnector(email=email)

    def search_pedro(
        self,
        query: str,
        max_results: int = 20,
        start_year: int = 2015,
        end_year: Optional[int] = None,
        lookback_days: Optional[int] = None,
        subdiscipline: str = "",
        therapy: str = "",
        min_pedro_score: int = 0,
        humans_only: bool = True,
        open_access_only: bool = False,
        languages: Optional[List[str]] = None,
    ) -> List[RawPublication]:
        """Collecte des essais cliniques, revues systématiques et guides du champ PEDro."""
        pm_query = compile_for_pedro_pubmed(
            query,
            subdiscipline=subdiscipline,
            therapy=therapy,
            humans_only=humans_only,
            open_access_only=open_access_only,
            languages=languages,
        )

        collected: List[RawPublication] = []
        try:
            pm_items = self.pubmed.search_and_fetch(
                query=pm_query,
                max_results=max_results,
                start_year=start_year,
                end_year=end_year,
                lookback_days=lookback_days,
                sort="relevance" if not lookback_days else "pub+date",
            )
            for item in pm_items:
                item.source = "pedro"
                if "PEDro-Indexed Scope" not in item.concepts:
                    item.concepts.append("PEDro Physiotherapy")
                estimated = estimate_pedro_scale_10(item)
                if estimated is not None:
                    item.pedro_score = estimated
                collected.append(item)
        except Exception:
            pass

        # Complément OpenAlex ciblé physiothérapie/rééducation si peu de résultats PubMed
        if len(collected) < max(4, max_results // 2):
            try:
                sub_kw = ""
                if subdiscipline and subdiscipline in PEDRO_SUBDISCIPLINES:
                    sub_kw = PEDRO_SUBDISCIPLINES[subdiscipline].get("pubmed", "")
                th_kw = ""
                if therapy and therapy in PEDRO_THERAPIES:
                    th_kw = PEDRO_THERAPIES[therapy].get("pubmed", "")
                oa_aug = f'({query}) AND ("physiotherapy" OR "physical therapy" OR "rehabilitation" OR "randomized controlled trial" OR "systematic review")'
                if sub_kw:
                    oa_aug = f"({oa_aug}) AND ({sub_kw})"
                if th_kw:
                    oa_aug = f"({oa_aug}) AND ({th_kw})"
                oa_items = self.openalex.search_works(
                    query=oa_aug,
                    max_results=max(6, max_results // 2),
                    start_year=start_year,
                    end_year=end_year,
                    lookback_days=lookback_days,
                    open_access_only=open_access_only,
                    languages=languages,
                )
                for item in oa_items:
                    text_l = f"{item.title} {item.abstract} {item.journal}".lower()
                    if any(k in text_l for k in PEDRO_RELEVANCE_TERMS) or any(j in item.journal.lower() for j in PEDRO_JOURNALS):
                        item.source = "pedro"
                        if "PEDro Physiotherapy" not in item.concepts:
                            item.concepts.append("PEDro Physiotherapy")
                        estimated = estimate_pedro_scale_10(item)
                        if estimated is not None:
                            item.pedro_score = estimated
                        collected.append(item)
            except Exception:
                pass

        if min_pedro_score > 0:
            filtered: List[RawPublication] = []
            for item in collected:
                if item.pedro_score is not None and item.pedro_score < min_pedro_score:
                    continue
                filtered.append(item)
            return filtered[:max_results]

        return collected[:max_results]


def parse_pedro_ris(ris_text: str) -> List[RawPublication]:
    """
    Parse un fichier d'export `.ris` téléchargé depuis `https://search.pedro.org.au` (« Save results »).
    Extrait automatiquement le score PEDro officiel (/10), DOI, PMID, URL pedro.org.au, auteurs et résumé.
    """
    if not ris_text or not ris_text.strip():
        return []

    records_raw: List[Dict[str, List[str]]] = []
    current: Dict[str, List[str]] = {}
    last_tag: Optional[str] = None

    for raw_line in ris_text.splitlines():
        line = raw_line.rstrip("\r\n")
        m = re.match(r"^([A-Z0-9]{2})\s{1,2}-\s?(.*)$", line)
        if m:
            tag = m.group(1).upper()
            val = m.group(2).strip()
            if tag == "TY":
                if current:
                    records_raw.append(current)
                current = {"TY": [val]}
                last_tag = "TY"
            elif tag == "ER":
                if current:
                    records_raw.append(current)
                current = {}
                last_tag = None
            else:
                current.setdefault(tag, []).append(val)
                last_tag = tag
        elif last_tag and line.strip() and current:
            # Ligne de continuation multi-lignes
            current[last_tag][-1] = f"{current[last_tag][-1]} {line.strip()}".strip()

    if current:
        records_raw.append(current)

    results: List[RawPublication] = []
    for idx, rec in enumerate(records_raw):
        title = clean_html_text(
            " ".join(rec.get("TI") or rec.get("T1") or [])
        ).replace("[with consumer summary]", "").strip()
        if not title:
            continue

        authors = [a.strip() for a in (rec.get("AU") or rec.get("A1") or []) if a.strip()]
        journal = clean_html_text(" ".join(rec.get("JO") or rec.get("JF") or rec.get("T2") or []))
        abstract = clean_html_text(" ".join(rec.get("AB") or rec.get("N2") or []))
        notes_list = rec.get("N1") or []
        notes_joined = " ".join(notes_list)
        keywords = [k.strip() for k in (rec.get("KW") or []) if k.strip()]

        # Année de publication
        pub_year = 0
        for py_raw in (rec.get("PY") or rec.get("Y1") or []):
            ym = re.search(r"(\d{4})", py_raw)
            if ym:
                pub_year = int(ym.group(1))
                break

        # DOI & URL PEDro
        doi: Optional[str] = None
        for do_raw in (rec.get("DO") or []):
            cand = normalize_doi(do_raw)
            if cand:
                doi = cand
                break
        if not doi:
            m_doi = re.search(r"(10\.\d{4,9}/[^\s,;]+)", f"{notes_joined} {' '.join(rec.get('UR') or [])}")
            if m_doi:
                doi = normalize_doi(m_doi.group(1))

        urls = [u.strip() for u in (rec.get("UR") or []) if u.strip()]
        pedro_url = next((u for u in urls if "pedro.org.au" in u.lower()), urls[0] if urls else "")
        if not pedro_url and doi:
            pedro_url = f"https://doi.org/{doi}"

        # ID PEDro si présent dans URL ou notes
        pedro_id = ""
        m_id = re.search(r"record-detail/(\d+)", pedro_url)
        if m_id:
            pedro_id = m_id.group(1)

        # Score PEDro officiel (X/10)
        pedro_score: Optional[int] = None
        score_hay = f"{notes_joined} {abstract} {' '.join(keywords)}"
        m_score = re.search(r"\b(\d{1,2})\s*/\s*10\b", score_hay)
        if m_score:
            val_sc = int(m_score.group(1))
            if 0 <= val_sc <= 10:
                pedro_score = val_sc

        # Type d'étude PEDro
        raw_types: List[str] = ["PEDro"]
        combined_type_hint = f"{notes_joined} {' '.join(keywords)} {title}".lower()
        if "systematic review" in combined_type_hint or "meta-analysis" in combined_type_hint:
            raw_types.append("Systematic Review")
        elif "practice guideline" in combined_type_hint or "guideline" in combined_type_hint:
            raw_types.append("Practice Guideline")
        else:
            raw_types.append("Randomized Controlled Trial")

        pub = RawPublication(
            source="pedro",
            external_id=f"pedro:{pedro_id or doi or idx}",
            title=title,
            abstract=abstract or notes_joined,
            authors=authors[:12],
            journal=journal or "PEDro",
            publication_date=f"{pub_year:04d}-01-01" if pub_year else "",
            publication_year=pub_year,
            doi=doi,
            url=pedro_url,
            raw_publication_types=raw_types,
            concepts=list(dict.fromkeys(["PEDro Physiotherapy", *keywords[:8]])),
            pedro_score=pedro_score,
            query_matched="pedro_ris_import",
        )
        if pub.pedro_score is None:
            pub.pedro_score = estimate_pedro_scale_10(pub)
        results.append(pub)

    return results
