"""
Générateur modulaire de profils d'audit et de veille scientifique.
Permet d'initialiser une veille sur N'IMPORTE QUEL sujet (sport, médecine, IA, écologie, nutrition, etc.)
depuis la CLI ou le Dashboard Web.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from mykairn_sciwatch.models import ThemeConfig, TopicProfile
from mykairn_sciwatch.search_syntax import build_boolean_from_blocks, validate_boolean_query


def slugify(text: str) -> str:
    """Transforme un titre en slug normalisé (a-z0-9_)."""
    normalized = text.lower().strip()
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u",
        "ç": "c",
    }
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_") or "custom_topic"


DEFAULT_HIGH_IMPACT_JOURNALS = [
    "Nature",
    "Science",
    "The Lancet",
    "JAMA",
    "BMJ",
    "Sports Medicine",
    "British Journal of Sports Medicine",
    "PLOS ONE",
    "Scientific Reports",
]


def generate_topic_profile(
    name: str,
    description: str = "",
    domain: str = "general_science",
    seed_keywords: Optional[List[str]] = None,
    custom_themes: Optional[List[Dict[str, str]]] = None,
    audit_start_year: int = 2018,
    audit_end_year: Optional[int] = None,
    watch_lookback_days: int = 30,
    boolean_query: str = "",
    custom_queries: Optional[List[str]] = None,
    query_blocks: Optional[List[Dict[str, Any]]] = None,
    exclusion_keywords: Optional[List[str]] = None,
    high_impact_journals: Optional[List[str]] = None,
    enabled_sources: Optional[List[str]] = None,
    allowed_publication_types: Optional[List[str]] = None,
    humans_only: bool = False,
    open_access_only: bool = False,
    exclude_preprints: bool = False,
    strict_boolean: bool = True,
    search_languages: Optional[List[str]] = None,
    min_citations: int = 0,
    min_sample_size: int = 0,
    min_relevance_score: float = 10.0,
    min_quality_score: float = 0.0,
    max_results_per_source: int = 30,
    slug_override: Optional[str] = None,
) -> TopicProfile:
    """
    Génère automatiquement un TopicProfile complet, structuré et entièrement paramétrable
    à partir d'une équation booléenne scientifique, de blocs PICO ou de mots-clés.
    """
    slug = slugify(slug_override) if slug_override else slugify(name)
    cleaned_exclusions = [e.strip().lower() for e in (exclusion_keywords or []) if e and e.strip()]

    effective_boolean = (boolean_query or "").strip()
    if not effective_boolean and query_blocks:
        effective_boolean = build_boolean_from_blocks(query_blocks, cleaned_exclusions)

    extracted_pos: List[str] = []
    extracted_neg: List[str] = []
    if effective_boolean:
        validation = validate_boolean_query(effective_boolean)
        if not validation["valid"]:
            raise ValueError(validation["error"] or "Équation booléenne invalide.")
        effective_boolean = validation["normalized"] or effective_boolean
        extracted_pos = list(validation["positive_terms"])
        extracted_neg = list(validation["negative_terms"])

    keywords = [k.strip() for k in (seed_keywords or []) if k.strip()]
    if not keywords and extracted_pos:
        keywords = extracted_pos[:8]
    if not keywords:
        words = [w for w in re.split(r"[\s,;/-]+", name) if len(w) > 3]
        keywords = words if words else [name]

    # Construction de requêtes booléennes adaptées à PubMed, OpenAlex et Semantic Scholar
    queries: List[str] = []
    if effective_boolean:
        queries.append(effective_boolean)
    for cq in (custom_queries or []):
        cq_s = str(cq).strip()
        if cq_s and cq_s not in queries:
            queries.append(cq_s)

    if not queries:
        primary_kw = keywords[0]
        if len(keywords) == 1:
            quoted_primary = f'"{primary_kw}"' if " " in primary_kw else primary_kw
            queries = [
                f"{quoted_primary} AND (\"systematic review\" OR \"meta-analysis\" OR randomized)",
                quoted_primary,
            ]
        else:
            quoted = [f'"{k}"' if " " in k else k for k in keywords[:6]]
            or_clause = " OR ".join(quoted[1:])
            queries.append(f"{quoted[0]} AND ({or_clause})")
            for kw in keywords[:4]:
                q_kw = f'"{kw}"' if " " in kw else kw
                if q_kw not in queries:
                    queries.append(q_kw)
        if not effective_boolean and queries:
            effective_boolean = queries[0]

    merged_exclusions = list(
        dict.fromkeys(["retracted", "erratum", "corrigendum", *cleaned_exclusions, *extracted_neg])
    )
    merged_inclusion = list(dict.fromkeys([k.lower() for k in keywords] + extracted_pos))

    # Thèmes personnalisés ou thèmes méthodologiques universels pour tout audit scientifique
    themes: List[ThemeConfig] = []
    if custom_themes:
        for t in custom_themes:
            t_name = t.get("name", "Thème")
            t_kws = [
                k.strip().lower()
                for k in t.get("keywords", "").split(",")
                if k.strip()
            ]
            themes.append(
                ThemeConfig(
                    slug=slugify(t_name),
                    name=t_name,
                    description=t.get("description", f"Travaux relatifs à {t_name}"),
                    keywords=t_kws or [t_name.lower()],
                    weight=1.0,
                )
            )
    else:
        themes = [
            ThemeConfig(
                slug="mechanisms_fundamentals",
                name="Fondamentaux, Mécanismes & Modèles",
                description="Bases théoriques, physiologiques ou mécanistiques du domaine",
                keywords=["mechanism", "model", "theory", "physiology", "biomarker", "pathway", "fundamental"]
                + [k.lower() for k in keywords[:2]],
                weight=1.0,
            ),
            ThemeConfig(
                slug="interventions_protocols",
                name="Interventions, Protocoles & Efficacité",
                description="Études interventionnelles, essais contrôlés et protocoles appliqués",
                keywords=["intervention", "protocol", "trial", "randomized", "efficacy", "treatment", "training", "program"],
                weight=1.2,
            ),
            ThemeConfig(
                slug="performance_outcomes_metrics",
                name="Mesures, Performance & Résultats",
                description="Indicateurs de performance, métriques d'évaluation et résultats observés",
                keywords=["outcome", "performance", "metric", "assessment", "evaluation", "accuracy", "predict", "adaptation"],
                weight=1.1,
            ),
            ThemeConfig(
                slug="risks_safety_limitations",
                name="Risques, Prévention & Limites",
                description="Facteurs de risque, effets indésirables, prévention et sécurité",
                keywords=["risk", "injury", "adverse", "prevention", "safety", "fatigue", "failure", "complication"],
                weight=1.0,
            ),
            ThemeConfig(
                slug="reviews_guidelines_consensus",
                name="Synthèses, Recommandations & Consensus",
                description="Revues systématiques, méta-analyses et guides de bonnes pratiques",
                keywords=["systematic review", "meta-analysis", "guideline", "consensus", "recommendation", "best practice"],
                weight=1.2,
            ),
        ]

    target_scopes = {
        "all_levels": ["general", "all", "population", "adult", "broad", "universal"],
        "recreational_amateur": ["amateur", "recreational", "novice", "beginner", "community"],
        "trained_competitive": ["trained", "experienced", "advanced", "competitive", "specialist"],
        "elite_pro": ["elite", "professional", "expert", "high-level", "world-class"],
    }

    clean_sources = (
        [s.strip() for s in enabled_sources if str(s).strip()]
        if enabled_sources
        else ["pubmed", "openalex", "semantic_scholar", "crossref"]
    )
    clean_journals = (
        [str(j).strip() for j in high_impact_journals if str(j).strip()]
        if high_impact_journals
        else list(DEFAULT_HIGH_IMPACT_JOURNALS)
    )

    return TopicProfile(
        slug=slug,
        name=name,
        description=description or f"Audit et veille scientifique automatisée sur : {name}",
        domain=domain,
        language="fr",
        queries=queries,
        boolean_query=effective_boolean,
        query_blocks=list(query_blocks or []),
        inclusion_keywords=merged_inclusion,
        exclusion_keywords=merged_exclusions,
        high_impact_journals=clean_journals,
        rss_feeds=[],
        themes=themes,
        target_scopes=target_scopes,
        audit_start_year=audit_start_year,
        audit_end_year=audit_end_year,
        watch_lookback_days=watch_lookback_days,
        max_results_per_source=max(5, min(100, int(max_results_per_source))),
        min_relevance_score=float(min_relevance_score),
        enabled_sources=clean_sources,
        allowed_publication_types=[
            str(pt).strip() for pt in (allowed_publication_types or []) if str(pt).strip()
        ],
        humans_only=bool(humans_only),
        open_access_only=bool(open_access_only),
        exclude_preprints=bool(exclude_preprints),
        strict_boolean=bool(strict_boolean),
        search_languages=[str(l).strip().lower() for l in (search_languages or []) if str(l).strip()],
        min_citations=max(0, int(min_citations)),
        min_sample_size=max(0, int(min_sample_size)),
        min_quality_score=max(0.0, float(min_quality_score)),
        llm_system_prompt=(
            f"Tu es un directeur scientifique expert chargé d'auditer la littérature sur '{name}'. "
            "Synthétise chaque publication en français avec un regard critique sur la qualité méthodologique (EBM) "
            "et formule des recommandations concrètes et actionnables."
        ),
    )
