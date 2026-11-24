"""
Générateur modulaire de profils d'audit et de veille scientifique.
Permet d'initialiser une veille sur N'IMPORTE QUEL sujet (sport, médecine, IA, écologie, nutrition, etc.)
depuis la CLI ou le Dashboard Web.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from mykairn_sciwatch.models import ThemeConfig, TopicProfile


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


def generate_topic_profile(
    name: str,
    description: str = "",
    domain: str = "general_science",
    seed_keywords: Optional[List[str]] = None,
    custom_themes: Optional[List[Dict[str, str]]] = None,
    audit_start_year: int = 2018,
    watch_lookback_days: int = 30,
) -> TopicProfile:
    """
    Génère automatiquement un TopicProfile complet, structuré et prêt à auditer
    à partir d'un nom de sujet et d'une liste de mots-clés.
    """
    slug = slugify(name)
    keywords = [k.strip() for k in (seed_keywords or []) if k.strip()]
    if not keywords:
        # Extraction automatique depuis le titre
        words = [w for w in re.split(r"[\s,;/-]+", name) if len(w) > 3]
        keywords = words if words else [name]

    # Construction de requêtes booléennes adaptées à PubMed, OpenAlex et Semantic Scholar
    primary_kw = keywords[0]
    queries: List[str] = []
    if len(keywords) == 1:
        queries = [
            f'"{primary_kw}" AND (systematic review OR meta-analysis OR randomized)',
            f'"{primary_kw}"',
        ]
    else:
        quoted = [f'"{k}"' if " " in k else k for k in keywords[:6]]
        or_clause = " OR ".join(quoted[1:])
        queries.append(f"{quoted[0]} AND ({or_clause})")
        for kw in keywords[:4]:
            queries.append(f'"{kw}"' if " " in kw else kw)

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

    return TopicProfile(
        slug=slug,
        name=name,
        description=description or f"Audit et veille scientifique automatisée sur : {name}",
        domain=domain,
        language="fr",
        queries=queries,
        inclusion_keywords=[k.lower() for k in keywords],
        exclusion_keywords=["retracted", "erratum", "corrigendum"],
        high_impact_journals=[
            "Nature",
            "Science",
            "The Lancet",
            "JAMA",
            "BMJ",
            "Sports Medicine",
            "British Journal of Sports Medicine",
            "PLOS ONE",
            "Scientific Reports",
        ],
        rss_feeds=[],
        themes=themes,
        target_scopes=target_scopes,
        audit_start_year=audit_start_year,
        watch_lookback_days=watch_lookback_days,
        max_results_per_source=30,
        min_relevance_score=10.0,
        llm_system_prompt=(
            f"Tu es un directeur scientifique expert chargé d'auditer la littérature sur '{name}'. "
            "Synthétise chaque publication en français avec un regard critique sur la qualité méthodologique (EBM) "
            "et formule des recommandations concrètes et actionnables."
        ),
    )
