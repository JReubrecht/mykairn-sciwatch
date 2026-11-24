"""
Tests du moteur de classification et de scoring 6D (Type EBM, Thème, Qualité, Portée, Fraîcheur, Synthèse).
"""

from __future__ import annotations

import unittest
from pathlib import Path

from mykairn_sciwatch.classifier.engine import ScientificClassifier6D
from mykairn_sciwatch.config import AppConfig, resolve_profile
from mykairn_sciwatch.connectors.aggregator import MergedPublicationRecord
from mykairn_sciwatch.models import RawPublication


class TestClassifier6D(unittest.TestCase):
    def setUp(self) -> None:
        self.profiles_dir = Path(__file__).resolve().parent.parent / "profiles"
        self.profile = resolve_profile("trail_running_coaching", self.profiles_dir)
        self.classifier = ScientificClassifier6D(AppConfig())

    def test_classify_high_quality_meta_analysis_all_levels(self) -> None:
        raw = RawPublication(
            source="pubmed",
            external_id="pmid:39001",
            title="Carbohydrate Intake, Gut Training, and Gastrointestinal Symptoms in Recreational and Elite Ultra-Trail Runners: A Systematic Review and Meta-Analysis",
            abstract=(
                "Background: Gastrointestinal distress affects ultra-trail performance. "
                "Methods: Following PRISMA guidelines, we analyzed 24 studies (n = 680 runners, including recreational and elite athletes). "
                "Results: Multi-transportable carbohydrate intake (90 g/h) with gut training significantly reduced gastrointestinal symptoms "
                "(p < 0.001, 95% CI, effect size d = 0.82) during actual trail race conditions. "
                "Conclusions: We recommend progressive gut training at 60-90 g/h for all levels of trail runners."
            ),
            authors=["Costa RJS", "Jeukendrup AE", "Burke LM"],
            journal="Sports Medicine",
            publication_date="2025-05-10",
            publication_year=2025,
            doi="10.1007/s40279-025-02100-z",
            pmid="39001",
            citation_count=55,
            influential_citation_count=9,
            raw_publication_types=["Meta-Analysis", "Systematic Review"],
            mesh_terms=["Running", "Carbohydrates", "Gastrointestinal Tract"],
            is_open_access=True,
        )
        record = MergedPublicationRecord(raw=raw, sources=["pubmed", "openalex"])
        classified = self.classifier.classify_single(record, self.profile)
        self.assertIsNotNone(classified)
        assert classified is not None

        # D1: EBM Type
        self.assertEqual(classified.publication_type, "meta_analysis")
        self.assertEqual(classified.evidence_tier, 1)

        # D2: Theme
        self.assertEqual(classified.primary_theme, "nutrition_hydration_gi")

        # D3: Quality
        self.assertGreaterEqual(classified.quality_score, 82.0)
        self.assertEqual(classified.quality_grade, "A+")
        self.assertEqual(classified.sample_size, 680)

        # D4: Scope & Athlete Level
        self.assertEqual(classified.athlete_level, "all_levels")
        self.assertGreaterEqual(classified.scope_score, 78.0)

        # D5: Freshness & Foundational
        self.assertTrue(classified.is_foundational)
        self.assertGreaterEqual(classified.freshness_score, 90.0)

        # D6: Overall & French Takeaways
        self.assertGreaterEqual(classified.overall_score, 85.0)
        self.assertIn("Méta-Analyse", classified.summary_fr)
        self.assertIn("gut training", classified.practical_takeaway.lower())

    def test_excludes_animal_or_off_topic_studies(self) -> None:
        raw_mouse = RawPublication(
            source="pubmed",
            external_id="pmid:999",
            title="Treadmill downhill running in mice alters skeletal muscle inflammation",
            abstract="We studied 24 mice on a rodent treadmill.",
            publication_year=2025,
        )
        rec = MergedPublicationRecord(raw=raw_mouse, sources=["pubmed"])
        self.assertIsNone(self.classifier.classify_single(rec, self.profile))


if __name__ == "__main__":
    unittest.main()
