"""
Moteur de classification et de scoring scientifique 6D (Evidence-Based Medicine & Sports Science).

Dimensions évaluées pour chaque publication :
  D1. Type de publication & Niveau de preuve EBM (Méta-analyse, Revue systématique, RCT, Cohorte, etc.)
  D2. Thème principal & Sous-thèmes (selon la taxonomie du TopicProfile actif)
  D3. Score de Qualité Méthodologique (/100) & Grade (A+, A, B, C, D)
  D4. Score de Portée & Applicabilité Terrain (/100), Niveau d'athlète cible & Cadre d'étude
  D5. Date, Score de Fraîcheur (/100) & Détection d'Article Fondateur
  D6. Score Global Composite (/100) & Synthèse Actionnable en Français (Résultats, Takeaway Coaching, Limites)
"""

from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from mykairn_sciwatch.classifier.llm_enricher import LLMEnricher
from mykairn_sciwatch.config import AppConfig
from mykairn_sciwatch.connectors.aggregator import MergedPublicationRecord
from mykairn_sciwatch.models import (
    ATHLETE_SCOPE_LABELS,
    PUBLICATION_TYPES_EBM,
    ClassifiedPublication,
    RawPublication,
    TopicProfile,
)
from mykairn_sciwatch.search_syntax import matches_boolean_query


# Recommandations pratiques de coaching par thème (enrichies dynamiquement avec les résultats de l'article)
THEME_COACHING_TEMPLATES: Dict[str, str] = {
    "periodization_training_load": (
        "Intégrer ces repères dans la planification macro/micro-cyclique : surveiller le couple charge interne (RPE/FC) "
        "et charge externe (volume horaire + D+/D-) en individualisant la progression selon le niveau de l'athlète."
    ),
    "physiology_energetics_durability": (
        "Prendre en compte la dérive physiologique (durabilité) et pas uniquement les seuils mesurés à l'état frais "
        "pour calibrer les zones d'intensité sur trail court, long et ultra."
    ),
    "biomechanics_uphill_downhill_poles": (
        "Programmer un conditionnement excentrique progressif (descentes spécifiques, renforcement pliométrique/isométrique) "
        "et entraîner la technique de bâtons en montée pour préserver la fonction neuromusculaire."
    ),
    "nutrition_hydration_gi": (
        "Planifier un protocole de 'gut training' progressif à l'entraînement (glucides multi-transporteurs, hydratation et sodium) "
        "adapté à la durée de l'épreuve et à la tolérance digestive individuelle."
    ),
    "injury_prevention_recovery_sleep": (
        "Croiser les indicateurs de récupération (sommeil, VFC/HRV, fatigue perçue, disponibilité énergétique) "
        "afin d'ajuster la charge avant l'apparition de surmenage ou de blessure de surcharge."
    ),
    "psychology_pacing_cognition": (
        "Adapter la stratégie de pacing au profil topographique et intégrer des routines de gestion de la fatigue mentale "
        "et de l'effort perçu (RPE) sur les sections techniques ou nocturnes."
    ),
    "athlete_populations_levels_female_master": (
        "Individualiser l'accompagnement selon le profil de l'athlète (volume disponible chez l'amateur, spécificités "
        "hormonales/énergétiques féminines, temps de récupération neuromusculaire chez l'athlète Master)."
    ),
    "environment_altitude_heat_cold": (
        "Anticiper les contraintes thermiques et d'altitude via une acclimatation dédiée (10-14 jours) et un ajustement "
        "des allures, du refroidissement et de la stratégie hydrique."
    ),
}


class ScientificClassifier6D:
    """Moteur de classification multi-dimensionnelle 6D."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or AppConfig()
        self.llm = LLMEnricher(self.config)

    def classify_batch(
        self,
        records: List[MergedPublicationRecord],
        profile: TopicProfile,
        max_llm_calls: int = 10,
    ) -> List[ClassifiedPublication]:
        """Classe, filtre et score un lot de publications fusionnées pour un TopicProfile."""
        classified: List[ClassifiedPublication] = []
        for rec in records:
            item = self.classify_single(rec, profile)
            if item is not None:
                classified.append(item)

        # Tri par score global décroissant
        classified.sort(key=lambda x: x.overall_score, reverse=True)

        # Enrichissement LLM optionnel sur les meilleures publications si une clé API est active
        if self.llm.is_enabled and max_llm_calls > 0:
            for pub in classified[:max_llm_calls]:
                self.llm.enrich_publication(pub, profile)

        return classified

    def classify_single(
        self,
        record: MergedPublicationRecord,
        profile: TopicProfile,
    ) -> Optional[ClassifiedPublication]:
        """Évalue une publication sur les 6 dimensions. Retourne None si hors-sujet ou exclue."""
        raw = record.raw
        full_text_lower = f"{raw.title} {raw.abstract} {' '.join(raw.mesh_terms)} {' '.join(raw.concepts)}".lower()

        # 0. Filtres temporels, d'exclusion, booléen strict, et critères méthodologiques paramétrés
        end_year = getattr(profile, "audit_end_year", None)
        if end_year and raw.publication_year and raw.publication_year > end_year:
            return None
        if profile.audit_start_year and raw.publication_year and raw.publication_year < profile.audit_start_year:
            return None

        if self._is_excluded(full_text_lower, profile):
            return None

        if getattr(profile, "open_access_only", False) and not (raw.is_open_access or raw.pdf_url):
            return None

        min_cit = int(getattr(profile, "min_citations", 0) or 0)
        if min_cit > 0 and raw.citation_count < min_cit:
            return None

        if getattr(profile, "humans_only", False) and self._is_animal_or_invitro_only(full_text_lower):
            return None

        bool_q = (getattr(profile, "boolean_query", "") or "").strip()
        if bool_q and getattr(profile, "strict_boolean", True):
            if not matches_boolean_query(raw, bool_q):
                return None

        relevance_score = self._compute_relevance(raw, full_text_lower, profile)
        if relevance_score < profile.min_relevance_score:
            return None

        # D1. Type de publication & Niveau de preuve EBM
        pub_type_key = self._detect_publication_type(raw, full_text_lower)
        if getattr(profile, "exclude_preprints", False) and pub_type_key == "preprint":
            return None

        allowed_types = list(getattr(profile, "allowed_publication_types", []) or [])
        if allowed_types and pub_type_key not in allowed_types:
            return None

        ebm_info = PUBLICATION_TYPES_EBM.get(pub_type_key, PUBLICATION_TYPES_EBM["original_research"])

        # D2. Thème principal, thèmes secondaires & tags
        primary_slug, primary_label, secondary_slugs, matched_tags = self._classify_themes(
            raw, full_text_lower, profile
        )

        # Extraction de la taille d'échantillon (n=...) et du cadre d'étude
        sample_size = self._extract_sample_size(raw.abstract)
        min_sample = int(getattr(profile, "min_sample_size", 0) or 0)
        if min_sample > 0:
            if sample_size is not None and sample_size < min_sample:
                return None
            if sample_size is None and pub_type_key not in ("meta_analysis", "systematic_review"):
                return None

        study_setting = self._detect_study_setting(full_text_lower, pub_type_key)

        # D3. Score de Qualité Méthodologique (/100)
        quality_score, quality_grade, quality_breakdown = self._compute_quality_score(
            raw=raw,
            full_text_lower=full_text_lower,
            ebm_info=ebm_info,
            sample_size=sample_size,
            profile=profile,
        )
        min_qual = float(getattr(profile, "min_quality_score", 0.0) or 0.0)
        if min_qual > 0 and quality_score < min_qual:
            return None

        # D4. Score de Portée, Applicabilité Terrain & Niveau d'Athlète (/100)
        athlete_level, athlete_level_label = self._detect_athlete_scope(full_text_lower, profile)
        scope_score, scope_level = self._compute_scope_score(
            raw=raw,
            full_text_lower=full_text_lower,
            athlete_level=athlete_level,
            study_setting=study_setting,
            sample_size=sample_size,
            pub_type_key=pub_type_key,
        )

        # D5. Fraîcheur & Caractère Fondateur
        freshness_score, is_foundational = self._compute_freshness_and_foundational(raw)

        # D6. Score Global Composite (/100)
        temporal_factor = max(freshness_score, 88.0 if is_foundational else freshness_score)
        overall_score = round(
            0.42 * quality_score + 0.35 * scope_score + 0.23 * temporal_factor,
            1,
        )
        overall_score = min(100.0, max(0.0, overall_score))

        # Génération de la synthèse structurée en français (déterministe EBM)
        summary_fr, practical_takeaway, key_findings, limitations = self._generate_french_synthesis(
            raw=raw,
            pub_type_key=pub_type_key,
            ebm_info=ebm_info,
            primary_slug=primary_slug,
            primary_label=primary_label,
            athlete_level_label=athlete_level_label,
            sample_size=sample_size,
            study_setting=study_setting,
            is_foundational=is_foundational,
        )

        uid = self._build_uid(raw)

        return ClassifiedPublication(
            uid=uid,
            topic_slug=profile.slug,
            title=raw.title,
            abstract=raw.abstract,
            authors=raw.authors,
            journal=raw.journal or "Revue Scientifique",
            publication_date=raw.publication_date,
            publication_year=raw.publication_year,
            doi=raw.doi,
            pmid=raw.pmid,
            url=raw.url or (f"https://doi.org/{raw.doi}" if raw.doi else ""),
            pdf_url=raw.pdf_url,
            sources=record.sources,
            citation_count=raw.citation_count,
            influential_citation_count=raw.influential_citation_count,
            is_open_access=raw.is_open_access,
            mesh_terms=raw.mesh_terms[:15],
            concepts=raw.concepts[:12],
            publication_type=pub_type_key,
            publication_type_label=ebm_info["label"],
            evidence_level=ebm_info["evidence_level"],
            evidence_tier=int(ebm_info["tier"]),
            primary_theme=primary_slug,
            primary_theme_label=primary_label,
            secondary_themes=secondary_slugs,
            tags=matched_tags[:10],
            quality_score=quality_score,
            quality_grade=quality_grade,
            quality_breakdown=quality_breakdown,
            scope_score=scope_score,
            scope_level=scope_level,
            athlete_level=athlete_level,
            athlete_level_label=athlete_level_label,
            sample_size=sample_size,
            study_setting=study_setting,
            freshness_score=freshness_score,
            is_foundational=is_foundational,
            overall_score=overall_score,
            relevance_score=relevance_score,
            summary_fr=summary_fr,
            practical_takeaway=practical_takeaway,
            key_findings=key_findings,
            limitations=limitations,
            classification_method="deterministic_ebm",
        )

    @staticmethod
    def _build_uid(raw: RawPublication) -> str:
        if raw.doi:
            base = f"doi:{raw.doi.lower()}"
        elif raw.pmid:
            base = f"pmid:{raw.pmid}"
        else:
            base = f"title:{raw.title.lower().strip()}"
        return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _is_animal_or_invitro_only(full_text_lower: str) -> bool:
        animal_markers = (
            "mice",
            "mouse",
            "murine",
            "rat model",
            "wistar",
            "sprague-dawley",
            "rodent",
            "zebrafish",
            "drosophila",
            "porcine",
            "in vitro",
        )
        human_markers = (
            "human",
            "humans",
            "athlete",
            "athletes",
            "runner",
            "runners",
            "participant",
            "participants",
            "patient",
            "patients",
            "subjects",
            "men",
            "women",
            "male",
            "female",
            "adult",
        )
        has_animal = any(re.search(rf"\b{re.escape(m)}\b", full_text_lower) for m in animal_markers)
        if not has_animal:
            return False
        has_human = any(re.search(rf"\b{re.escape(h)}\b", full_text_lower) for h in human_markers)
        return not has_human

    @staticmethod
    def _is_excluded(full_text_lower: str, profile: TopicProfile) -> bool:
        for exc in profile.exclusion_keywords:
            pattern = rf"\b{re.escape(exc.lower())}\b"
            if re.search(pattern, full_text_lower):
                return True
        return False

    @staticmethod
    def _compute_relevance(raw: RawPublication, full_text_lower: str, profile: TopicProfile) -> float:
        title_lower = raw.title.lower()
        score = 0.0

        bool_q = (getattr(profile, "boolean_query", "") or "").strip()
        if bool_q and matches_boolean_query(raw, bool_q):
            score += 18.0
        else:
            for q_item in profile.queries:
                if q_item.strip() and matches_boolean_query(raw, q_item):
                    score += 14.0
                    break

        for kw in profile.inclusion_keywords:
            kw_l = kw.lower()
            if kw_l in title_lower:
                score += 14.0
            elif kw_l in full_text_lower:
                score += 6.0

        for theme in profile.themes:
            for tkw in theme.keywords:
                tkw_l = tkw.lower()
                if tkw_l in title_lower:
                    score += 5.0 * theme.weight
                elif tkw_l in full_text_lower:
                    score += 2.0 * theme.weight

        return round(min(100.0, score), 1)

    @staticmethod
    def _detect_publication_type(raw: RawPublication, full_text_lower: str) -> str:
        raw_types_joined = " ".join(raw.raw_publication_types).lower()
        title_lower = raw.title.lower()
        combined = f"{raw_types_joined} {title_lower} {full_text_lower}"

        # 1. Méta-analyse
        if "meta-analysis" in combined or "meta analysis" in combined:
            return "meta_analysis"

        # 2. Consensus / Position Stand
        if any(
            term in combined
            for term in ("consensus statement", "position stand", "expert consensus", "clinical practice guideline")
        ):
            return "consensus_statement"

        # 3. Revue systématique
        if any(
            term in combined
            for term in ("systematic review", "scoping review", "prisma", "umbrella review")
        ):
            return "systematic_review"

        # 4. Essai contrôlé randomisé (RCT)
        if any(
            term in combined
            for term in (
                "randomized controlled trial",
                "randomised controlled trial",
                "randomized crossover",
                "randomised crossover",
                "double-blind",
                "placebo-controlled",
                "randomly assigned",
                "randomly allocated",
            )
        ):
            return "randomized_controlled_trial"

        # 5. Essai contrôlé / expérimental
        if any(
            term in raw_types_joined
            for term in ("clinical trial", "controlled clinical trial", "comparative study")
        ) or any(
            term in full_text_lower
            for term in ("crossover design", "counterbalanced", "experimental group", "training intervention")
        ):
            return "controlled_trial"

        # 6. Étude de cas
        if (
            "case reports" in raw_types_joined
            or "case study" in title_lower
            or "case report" in title_lower
            or "case series" in title_lower
        ):
            return "case_study"

        # 7. Prépublication
        if "preprint" in raw_types_joined or any(
            srv in (raw.journal or "").lower() for srv in ("medrxiv", "biorxiv", "sportrxiv", "research square")
        ):
            return "preprint"

        # 8. Revue narrative
        if "review" in raw_types_joined or "review" in title_lower:
            return "narrative_review"

        # 9. Cohorte / longitudinale
        if any(
            term in full_text_lower
            for term in ("cohort", "longitudinal", "prospective study", "weeks of training", "season-long")
        ):
            return "cohort_study"

        # 10. Étude observationnelle / terrain
        if any(
            term in full_text_lower
            for term in ("observational", "cross-sectional", "survey", "questionnaire", "during an ultra", "field study")
        ):
            return "observational_study"

        return "original_research"

    @staticmethod
    def _classify_themes(
        raw: RawPublication,
        full_text_lower: str,
        profile: TopicProfile,
    ) -> Tuple[str, str, List[str], List[str]]:
        if not profile.themes:
            return "general", "Général", [], []

        title_lower = raw.title.lower()
        mesh_lower = " ".join(raw.mesh_terms + raw.concepts).lower()

        theme_scores: List[Tuple[float, str, str]] = []
        matched_tags: List[str] = []

        for theme in profile.themes:
            t_score = 0.0
            for kw in theme.keywords:
                kw_l = kw.lower()
                hit = False
                if kw_l in title_lower:
                    t_score += 6.0 * theme.weight
                    hit = True
                if kw_l in mesh_lower:
                    t_score += 4.0 * theme.weight
                    hit = True
                if kw_l in full_text_lower:
                    t_score += 2.0 * theme.weight
                    hit = True
                if hit and kw_l not in matched_tags:
                    matched_tags.append(kw_l)
            theme_scores.append((t_score, theme.slug, theme.name))

        theme_scores.sort(key=lambda x: x[0], reverse=True)
        best_score, primary_slug, primary_name = theme_scores[0]
        if best_score <= 0:
            primary_slug = profile.themes[0].slug
            primary_name = profile.themes[0].name

        secondary_slugs = [
            slug for score, slug, _ in theme_scores[1:3] if score >= max(4.0, best_score * 0.35)
        ]
        return primary_slug, primary_name, secondary_slugs, matched_tags

    @staticmethod
    def _extract_sample_size(abstract: str) -> Optional[int]:
        if not abstract:
            return None

        patterns = [
            r"\b[nN]\s*=\s*(\d{1,6})\b",
            r"\b(\d{1,5})\s+(?:trail\s+)?(?:runners|athletes|participants|subjects|finishers|men|women|females|males|studies|trials)\b",
            r"\bsample\s+of\s+(\d{1,5})\b",
            r"\bincluded\s+(\d{1,5})\s+(?:studies|participants|runners|athletes)\b",
        ]
        candidates: List[int] = []
        for pat in patterns:
            for match in re.finditer(pat, abstract, flags=re.IGNORECASE):
                try:
                    val = int(match.group(1))
                    # Éviter de confondre une année (2015-2029) ou distance (100 km) si isolé
                    if 3 <= val <= 150000 and not (1990 <= val <= 2030):
                        candidates.append(val)
                except ValueError:
                    continue
        return max(candidates) if candidates else None

    @staticmethod
    def _detect_study_setting(full_text_lower: str, pub_type_key: str) -> str:
        if pub_type_key in ("meta_analysis", "systematic_review", "consensus_statement", "narrative_review"):
            return "Mixte / Synthèse"
        field_markers = (
            "field study",
            "during a",
            "during an",
            "actual race",
            "competition",
            "mountain marathon",
            "ultra-trail du mont-blanc",
            "utmb",
            "in-race",
            "outdoor",
            "trail race",
            "real-world",
        )
        lab_markers = (
            "treadmill",
            "laboratory",
            "ergometer",
            "environmental chamber",
            "incremental test",
        )
        has_field = any(m in full_text_lower for m in field_markers)
        has_lab = any(m in full_text_lower for m in lab_markers)
        if has_field and has_lab:
            return "Mixte (Laboratoire + Terrain)"
        if has_field:
            return "Terrain / Course réelle"
        if has_lab:
            return "Laboratoire"
        return "Terrain / Empirique"

    @staticmethod
    def _compute_quality_score(
        raw: RawPublication,
        full_text_lower: str,
        ebm_info: Dict[str, object],
        sample_size: Optional[int],
        profile: TopicProfile,
    ) -> Tuple[float, str, Dict[str, float]]:
        # 1. Design d'étude EBM (/35)
        ebm_pts = float(ebm_info.get("base_quality", 19))

        # 2. Taille d'échantillon (/18)
        if sample_size is None:
            sample_pts = 8.0 if int(ebm_info.get("tier", 3)) <= 2 else 6.0
        elif sample_size >= 200:
            sample_pts = 18.0
        elif sample_size >= 60:
            sample_pts = 15.0
        elif sample_size >= 25:
            sample_pts = 12.5
        elif sample_size >= 12:
            sample_pts = 10.0
        else:
            sample_pts = 7.0

        # 3. Prestige du journal & indexation (/17)
        journal_lower = (raw.journal or "").lower()
        journal_pts = 8.0
        for hi_j in profile.high_impact_journals:
            if hi_j.lower() in journal_lower:
                journal_pts = 15.0
                break
        if raw.doi:
            journal_pts += 1.0
        if raw.pmid:
            journal_pts += 1.0
        journal_pts = min(17.0, journal_pts)

        # 4. Impact bibliométrique & vélocité de citations (/18)
        now_year = datetime.now(timezone.utc).year
        age_years = max(1, now_year - (raw.publication_year or now_year) + 1)
        velocity = raw.citation_count / age_years
        if raw.citation_count > 0:
            cit_pts = min(16.0, 4.0 * math.log1p(velocity) + 1.5 * math.log1p(raw.citation_count))
        else:
            # Articles très récents (<= 1 an) ne sont pas pénalisés sévèrement
            cit_pts = 7.0 if age_years <= 2 else 3.0
        if raw.influential_citation_count > 0:
            cit_pts = min(18.0, cit_pts + min(3.0, raw.influential_citation_count * 0.5))

        # 5. Rigueur méthodologique & statistique (/12)
        rigor_pts = 3.0
        rigor_markers = [
            (r"\bp\s*[<=>]\s*0\.\d+", 2.0),
            (r"\b95%\s*(?:ci|confidence interval)\b", 2.5),
            (r"\b(?:effect size|cohen's d|hedges' g|eta-squared|r\s*=\s*0\.\d+)\b", 2.5),
            (r"\b(?:control group|placebo|crossover|blinded|prisma)\b", 2.0),
        ]
        for pattern, bonus in rigor_markers:
            if re.search(pattern, full_text_lower):
                rigor_pts += bonus
        if len(raw.abstract) > 600:
            rigor_pts += 1.0
        rigor_pts = min(12.0, rigor_pts)

        total = round(min(100.0, ebm_pts + sample_pts + journal_pts + cit_pts + rigor_pts), 1)

        if total >= 82:
            grade = "A+"
        elif total >= 72:
            grade = "A"
        elif total >= 60:
            grade = "B"
        elif total >= 48:
            grade = "C"
        else:
            grade = "D"

        breakdown = {
            "ebm_design": round(ebm_pts, 1),
            "sample_size": round(sample_pts, 1),
            "journal_indexing": round(journal_pts, 1),
            "citation_impact": round(cit_pts, 1),
            "methodological_rigor": round(rigor_pts, 1),
        }
        return total, grade, breakdown

    @staticmethod
    def _detect_athlete_scope(full_text_lower: str, profile: TopicProfile) -> Tuple[str, str]:
        matched_levels: List[str] = []
        scopes_map = profile.target_scopes or {}

        for scope_key, keywords in scopes_map.items():
            for kw in keywords:
                if kw.lower() in full_text_lower:
                    matched_levels.append(scope_key)
                    break

        unique_levels = list(dict.fromkeys(matched_levels))

        # Priorité aux populations spécifiques si mentionnées explicitement dans l'étude
        if "all_levels" in unique_levels or (
            "recreational_amateur" in unique_levels and "elite_pro" in unique_levels
        ):
            key = "all_levels"
        elif "female_athlete" in unique_levels and len(unique_levels) == 1:
            key = "female_athlete"
        elif "master_athlete" in unique_levels and len(unique_levels) == 1:
            key = "master_athlete"
        elif "recreational_amateur" in unique_levels:
            key = "recreational_amateur"
        elif "trained_competitive" in unique_levels:
            key = "trained_competitive"
        elif "elite_pro" in unique_levels:
            key = "elite_pro"
        else:
            key = "all_levels"

        return key, ATHLETE_SCOPE_LABELS.get(key, ATHLETE_SCOPE_LABELS["all_levels"])

    @staticmethod
    def _compute_scope_score(
        raw: RawPublication,
        full_text_lower: str,
        athlete_level: str,
        study_setting: str,
        sample_size: Optional[int],
        pub_type_key: str,
    ) -> Tuple[float, str]:
        score = 45.0

        # Validité écologique (terrain / course réelle ou synthèse)
        if "Terrain" in study_setting or "Mixte" in study_setting:
            score += 16.0
        else:
            score += 8.0

        # Portée selon le niveau d'athlète (valoriser l'applicabilité large "tous niveaux" et amateur)
        if athlete_level in ("all_levels", "recreational_amateur", "trained_competitive"):
            score += 16.0
        else:
            score += 11.0

        # Présence de métriques directement utilisables par un coach sur le terrain
        practical_markers = (
            "heart rate",
            "rpe",
            "rating of perceived exertion",
            "pacing",
            "pace",
            "training load",
            "training volume",
            "g/h",
            "carbohydrate",
            "hydration",
            "sleep",
            "hrv",
            "poles",
            "downhill",
            "strength training",
            "tapering",
            "recovery",
        )
        hits = sum(1 for m in practical_markers if m in full_text_lower)
        score += min(16.0, hits * 3.2)

        # Bonus revues systématiques / consensus / échantillon large / Open Access
        if pub_type_key in ("meta_analysis", "systematic_review", "consensus_statement"):
            score += 5.0
        if sample_size and sample_size >= 40:
            score += 3.0
        if raw.is_open_access:
            score += 2.0

        score = round(min(100.0, score), 1)
        if score >= 78:
            level = "Forte (Application Terrain Directe)"
        elif score >= 62:
            level = "Modérée (Transférable au Coaching)"
        else:
            level = "Spécifique / Exploratoire (Labo)"
        return score, level

    @staticmethod
    def _compute_freshness_and_foundational(raw: RawPublication) -> Tuple[float, bool]:
        now_year = datetime.now(timezone.utc).year
        pub_year = raw.publication_year or now_year
        age = max(0, now_year - pub_year)

        if age == 0:
            freshness = 100.0
        elif age == 1:
            freshness = 94.0
        elif age == 2:
            freshness = 86.0
        elif age == 3:
            freshness = 78.0
        elif age <= 5:
            freshness = 68.0
        elif age <= 8:
            freshness = 55.0
        else:
            freshness = max(35.0, 55.0 - (age - 8) * 3.0)

        velocity = raw.citation_count / max(1, age + 1)
        is_foundational = bool(raw.citation_count >= 45 or (age >= 2 and velocity >= 10.0))
        return round(freshness, 1), is_foundational

    @staticmethod
    def _generate_french_synthesis(
        raw: RawPublication,
        pub_type_key: str,
        ebm_info: Dict[str, object],
        primary_slug: str,
        primary_label: str,
        athlete_level_label: str,
        sample_size: Optional[int],
        study_setting: str,
        is_foundational: bool,
    ) -> Tuple[str, str, List[str], str]:
        sample_str = f" (n={sample_size})" if sample_size else ""
        foundational_str = " [Article Fondateur de Référence]" if is_foundational else ""

        # Extraction des phrases clés du résumé (Conclusions / Résultats)
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", raw.abstract or "")
            if len(s.strip()) > 35
        ]

        conclusion_sentences: List[str] = []
        result_sentences: List[str] = []
        for s in sentences:
            s_low = s.lower()
            if any(
                k in s_low
                for k in (
                    "conclusion",
                    "conclude",
                    "suggest",
                    "recommend",
                    "practical application",
                    "these findings",
                    "in summary",
                    "overall,",
                    "demonstrate that",
                )
            ):
                conclusion_sentences.append(s)
            elif any(
                k in s_low
                for k in (
                    "significant",
                    "increased",
                    "decreased",
                    "improved",
                    "associated with",
                    "correlated",
                    "p <",
                    "p=",
                    "%",
                )
            ):
                result_sentences.append(s)

        if not result_sentences and sentences:
            result_sentences = sentences[1:3] if len(sentences) > 1 else sentences[:1]
        if not conclusion_sentences and sentences:
            conclusion_sentences = [sentences[-1]]

        summary_fr = (
            f"{ebm_info['label']}{sample_str} publiée dans {raw.journal or 'une revue internationale'} "
            f"({raw.publication_year}){foundational_str}, portant sur le thème « {primary_label} » "
            f"dans un cadre « {study_setting} » (cible : {athlete_level_label}). "
        )
        if conclusion_sentences:
            summary_fr += f"Conclusion principale : {conclusion_sentences[-1]}"

        base_takeaway = THEME_COACHING_TEMPLATES.get(
            primary_slug,
            "Exploiter ces résultats pour ajuster les protocoles d'accompagnement et de suivi selon la réponse individuelle.",
        )
        practical_takeaway = f"[{athlete_level_label}] {base_takeaway}"

        key_findings = (result_sentences[:2] + conclusion_sentences[:1])[:3]
        if not key_findings:
            key_findings = [raw.title]

        # Limites méthodologiques déterminées selon le design EBM et la taille d'échantillon
        tier = int(ebm_info.get("tier", 3))
        if tier == 1:
            limitations = (
                "Hétérogénéité potentielle des protocoles inclus entre les études primaires ; "
                "adapter les valeurs moyennes à la tolérance individuelle de l'athlète."
            )
        elif sample_size and sample_size < 20:
            limitations = (
                f"Échantillon restreint (n={sample_size}) : puissance statistique limitée, "
                "valider la transférabilité sur le terrain avant généralisation."
            )
        elif "Laboratoire" in study_setting:
            limitations = (
                "Protocole réalisé en conditions contrôlées de laboratoire : "
                "intégrer les contraintes de terrain (dénivelé technique, météo, fatigue cumulée)."
            )
        elif pub_type_key in ("observational_study", "cohort_study"):
            limitations = (
                "Design observationnel : met en évidence des associations de terrain pertinentes "
                "sans prouver à lui seul un lien de causalité strict."
            )
        else:
            limitations = (
                "Tenir compte de la variabilité inter-individuelle et du niveau d'entraînement initial "
                "lors de la transposition en coaching."
            )

        return summary_fr, practical_takeaway, key_findings, limitations
