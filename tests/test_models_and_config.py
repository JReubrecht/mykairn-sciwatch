"""
Tests des modèles, du chargement des profils YAML et du générateur modulaire de sujets.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mykairn_sciwatch.config import (
    list_topic_profiles,
    load_topic_profile,
    resolve_profile,
    save_topic_profile,
)
from mykairn_sciwatch.profile_generator import generate_topic_profile, slugify


class TestModelsAndConfig(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(slugify("Coaching & Trail Running (Élite/Amateur)"), "coaching_trail_running_elite_amateur")
        self.assertEqual(slugify("   "), "custom_topic")

    def test_builtin_trail_profile_loads(self) -> None:
        profiles_dir = Path(__file__).resolve().parent.parent / "profiles"
        trail = resolve_profile("trail_running_coaching", profiles_dir)
        self.assertEqual(trail.slug, "trail_running_coaching")
        self.assertGreaterEqual(len(trail.themes), 8)
        self.assertGreaterEqual(len(trail.queries), 4)
        self.assertIn("all_levels", trail.target_scopes)
        self.assertIn("recreational_amateur", trail.target_scopes)

    def test_generate_and_save_any_topic_profile(self) -> None:
        prof = generate_topic_profile(
            name="Impact du Sommeil et de la VFC en Ultra-Trail",
            description="Audit sur la privation de sommeil et la récupération autonome",
            domain="chronobiology_sport",
            seed_keywords=["sleep deprivation", "heart rate variability", "ultramarathon"],
            audit_start_year=2017,
        )
        self.assertEqual(prof.slug, "impact_du_sommeil_et_de_la_vfc_en_ultra_trail")
        self.assertGreaterEqual(len(prof.queries), 2)
        self.assertGreaterEqual(len(prof.themes), 4)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            saved_path = save_topic_profile(prof, tmp_dir)
            self.assertTrue(saved_path.is_file())
            reloaded = load_topic_profile(saved_path)
            self.assertEqual(reloaded.slug, prof.slug)
            self.assertEqual(reloaded.name, prof.name)
            all_profs = list_topic_profiles(tmp_dir)
            self.assertEqual(len(all_profs), 1)


if __name__ == "__main__":
    unittest.main()
