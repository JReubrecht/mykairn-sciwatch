"""
Modèles de données de myKairn SciWatch (Publications, Classification 6D, Profils de veille, Runs).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ==============================================================================
# Constantes & Taxonomie EBM (Evidence-Based Medicine / Sports Science)
# ==============================================================================

PUBLICATION_TYPES_EBM: Dict[str, Dict[str, Any]] = {
    "meta_analysis": {
        "label": "Méta-Analyse",
        "evidence_level": "Niveau 1A (Preuve Élevée)",
        "tier": 1,
        "base_quality": 35,
    },
    "systematic_review": {
        "label": "Revue Systématique",
        "evidence_level": "Niveau 1B (Preuve Élevée)",
        "tier": 1,
        "base_quality": 32,
    },
    "randomized_controlled_trial": {
        "label": "Essai Contrôlé Randomisé (RCT)",
        "evidence_level": "Niveau 2A (Interventionnel Fort)",
        "tier": 2,
        "base_quality": 30,
    },
    "controlled_trial": {
        "label": "Étude Expérimentale / Essai Contrôlé",
        "evidence_level": "Niveau 2B (Interventionnel)",
        "tier": 2,
        "base_quality": 26,
    },
    "consensus_statement": {
        "label": "Consensus International / Position Stand",
        "evidence_level": "Niveau 2C (Consensus d'Experts)",
        "tier": 2,
        "base_quality": 28,
    },
    "cohort_study": {
        "label": "Étude de Cohorte / Longitudinale",
        "evidence_level": "Niveau 3A (Observationnel Longitudinal)",
        "tier": 3,
        "base_quality": 23,
    },
    "observational_study": {
        "label": "Étude Observationnelle / Terrain",
        "evidence_level": "Niveau 3B (Observationnel)",
        "tier": 3,
        "base_quality": 20,
    },
    "narrative_review": {
        "label": "Revue Narrative / Synthèse",
        "evidence_level": "Niveau 4A (Synthèse Critique)",
        "tier": 4,
        "base_quality": 18,
    },
    "case_study": {
        "label": "Étude de Cas / Série de Cas",
        "evidence_level": "Niveau 4B (Cas Terrain)",
        "tier": 4,
        "base_quality": 14,
    },
    "preprint": {
        "label": "Prépublication (Preprint)",
        "evidence_level": "Niveau 5 (Non revu par les pairs)",
        "tier": 5,
        "base_quality": 10,
    },
    "original_research": {
        "label": "Article de Recherche Originale",
        "evidence_level": "Niveau 3 (Recherche Empirique)",
        "tier": 3,
        "base_quality": 19,
    },
}

ATHLETE_SCOPE_LABELS: Dict[str, str] = {
    "all_levels": "Tous niveaux (Débutant à Élite)",
    "recreational_amateur": "Débutant / Récréatif / Amateur",
    "trained_competitive": "Entraîné / Compétiteur Régional-National",
    "elite_pro": "Élite / International / Pro",
    "female_athlete": "Athlètes Féminines",
    "master_athlete": "Athlètes Masters / Vétérans (40+)",
    "youth_junior": "Jeunes / Espoirs",
    "general_population": "Population Générale / Transversal",
}


@dataclass
class ThemeConfig:
    """Configuration d'un thème dans un profil de veille."""

    slug: str
    name: str
    description: str
    keywords: List[str] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class TopicProfile:
    """Profil déclaratif d'un sujet d'audit ou de veille scientifique."""

    slug: str
    name: str
    description: str
    domain: str = "sports_science"
    language: str = "fr"
    queries: List[str] = field(default_factory=list)
    boolean_query: str = ""
    query_blocks: List[Dict[str, Any]] = field(default_factory=list)
    inclusion_keywords: List[str] = field(default_factory=list)
    exclusion_keywords: List[str] = field(default_factory=list)
    high_impact_journals: List[str] = field(default_factory=list)
    rss_feeds: List[Dict[str, str]] = field(default_factory=list)
    themes: List[ThemeConfig] = field(default_factory=list)
    target_scopes: Dict[str, List[str]] = field(default_factory=dict)
    audit_start_year: int = 2015
    audit_end_year: Optional[int] = None
    watch_lookback_days: int = 30
    max_results_per_source: int = 40
    min_relevance_score: float = 15.0
    enabled_sources: List[str] = field(
        default_factory=lambda: ["pubmed", "openalex", "semantic_scholar", "crossref"]
    )
    allowed_publication_types: List[str] = field(default_factory=list)
    humans_only: bool = False
    open_access_only: bool = False
    exclude_preprints: bool = False
    strict_boolean: bool = True
    search_languages: List[str] = field(default_factory=list)
    min_citations: int = 0
    min_sample_size: int = 0
    min_quality_score: float = 0.0
    llm_system_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RawPublication:
    """Publication brute collectée depuis un connecteur (PubMed, OpenAlex, Semantic Scholar, Crossref/RSS)."""

    source: str
    external_id: str
    title: str
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    journal: str = ""
    publication_date: str = ""  # YYYY-MM-DD
    publication_year: int = 0
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: str = ""
    pdf_url: Optional[str] = None
    citation_count: int = 0
    influential_citation_count: int = 0
    raw_publication_types: List[str] = field(default_factory=list)
    mesh_terms: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    is_open_access: bool = False
    query_matched: str = ""


@dataclass
class ClassifiedPublication:
    """Publication dédoublonnée, classée et scorée selon la grille 6D."""

    uid: str
    topic_slug: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    publication_date: str
    publication_year: int
    doi: Optional[str]
    pmid: Optional[str]
    url: str
    pdf_url: Optional[str]
    sources: List[str]
    citation_count: int
    influential_citation_count: int
    is_open_access: bool
    mesh_terms: List[str]
    concepts: List[str]

    # --- Dimension 1 : Type de publication & Niveau de preuve EBM ---
    publication_type: str  # clé dans PUBLICATION_TYPES_EBM
    publication_type_label: str
    evidence_level: str
    evidence_tier: int  # 1 (plus fort) à 5

    # --- Dimension 2 : Thème & Sous-thèmes ---
    primary_theme: str  # slug du thème
    primary_theme_label: str
    secondary_themes: List[str]
    tags: List[str]

    # --- Dimension 3 : Qualité méthodologique (/100) ---
    quality_score: float
    quality_grade: str  # A+, A, B, C, D
    quality_breakdown: Dict[str, float]

    # --- Dimension 4 : Portée & Applicabilité Terrain (/100) ---
    scope_score: float
    scope_level: str  # "Forte (Terrain/Directe)", "Modérée (Transférable)", "Théorique / Labo"
    athlete_level: str  # clé dans ATHLETE_SCOPE_LABELS
    athlete_level_label: str
    sample_size: Optional[int]
    study_setting: str  # "Terrain / Course réelle", "Laboratoire", "Mixte / Synthèse"

    # --- Dimension 5 : Date, Fraîcheur & Caractère Fondateur ---
    freshness_score: float
    is_foundational: bool  # True si classique très cité

    # --- Dimension 6 : Score Global & Synthèse Actionnable ("Takeaways") ---
    overall_score: float
    relevance_score: float
    summary_fr: str
    practical_takeaway: str
    key_findings: List[str]
    limitations: str
    classification_method: str  # "hybrid_llm" ou "deterministic_ebm"

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WatchRunSummary:
    """Résumé d'exécution d'un audit ou d'une veille."""

    run_id: str
    topic_slug: str
    mode: str  # "audit" ou "watch"
    started_at: str
    finished_at: str
    status: str  # "completed", "failed"
    raw_fetched_count: int
    deduplicated_count: int
    classified_count: int
    new_inserted_count: int
    updated_count: int
    sources_breakdown: Dict[str, int]
    themes_breakdown: Dict[str, int]
    types_breakdown: Dict[str, int]
    report_path: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
