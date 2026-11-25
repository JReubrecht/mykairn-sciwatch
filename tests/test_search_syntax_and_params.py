"""
Tests du moteur de syntaxe booléenne scientifique, de la compilation multi-sources,
des filtres méthodologiques 6D et des endpoints paramétrables REST.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from mykairn_sciwatch.classifier.engine import ScientificClassifier6D
from mykairn_sciwatch.config import AppConfig
from mykairn_sciwatch.connectors.aggregator import MergedPublicationRecord
from mykairn_sciwatch.models import RawPublication
from mykairn_sciwatch.profile_generator import generate_topic_profile
from mykairn_sciwatch.search_syntax import (
    build_boolean_from_blocks,
    compile_for_crossref,
    compile_for_openalex,
    compile_for_pubmed,
    compile_for_semantic_scholar_bulk,
    matches_boolean_query,
    validate_boolean_query,
)
from mykairn_sciwatch.storage.sqlite_store import SciWatchStore
from mykairn_sciwatch.web.server import create_http_server


class TestSearchSyntaxAndParams(unittest.TestCase):
    def test_boolean_validation_and_pico_builder(self) -> None:
        ok_res = validate_boolean_query(
            '("trail running" OR ultramarathon*) AND (HRV OR "heart rate variability"[TIAB]) NOT (mice OR rat)'
        )
        self.assertTrue(ok_res["valid"])
        self.assertIn("trail running", ok_res["positive_terms"])
        self.assertIn("mice", ok_res["negative_terms"])
        self.assertIn("rat", ok_res["negative_terms"])

        # Alias français + parenthèses imbriquées
        fr_res = validate_boolean_query('(endurance OU "course en montagne") ET ti:VO2max SAUF -dopage')
        self.assertTrue(fr_res["valid"])

        # Erreurs syntaxiques détectées
        bad_paren = validate_boolean_query('("trail running" AND (sleep OR HRV)')
        self.assertFalse(bad_paren["valid"])
        self.assertIsNotNone(bad_paren["error"])

        bad_quote = validate_boolean_query('"trail running AND sleep')
        self.assertFalse(bad_quote["valid"])

        bad_op = validate_boolean_query("AND trail")
        self.assertFalse(bad_op["valid"])

        equation = build_boolean_from_blocks(
            [
                {"operator": "OR", "field": "tiab", "terms": ["trail running", "ultramarathon*"]},
                {"operator": "OR", "field": "all", "terms": ["sleep", "HRV"]},
            ],
            exclusion_terms=["mice", "rat model"],
        )
        self.assertEqual(
            equation,
            '(tiab:"trail running" OR tiab:ultramarathon*) AND (sleep OR HRV) NOT (mice OR "rat model")',
        )

    def test_connector_compilers(self) -> None:
        q = '("trail running" OR ultra*) AND ti:downhill NOT mice'
        pm = compile_for_pubmed(
            q,
            humans_only=True,
            open_access_only=True,
            exclude_preprints=True,
            allowed_pub_types=["meta_analysis", "randomized_controlled_trial"],
            languages=["en"],
        )
        self.assertIn('"trail running"', pm)
        self.assertIn("ultra*", pm)
        self.assertIn("downhill[Title]", pm)
        self.assertIn("NOT mice", pm)
        self.assertIn('"humans"[MeSH Terms]', pm)
        self.assertIn('"Meta-Analysis"[Publication Type]', pm)
        self.assertIn('NOT "Preprint"[Publication Type]', pm)

        oa = compile_for_openalex(q)
        self.assertIn('"trail running" OR ultra', oa)
        self.assertIn("AND", oa)
        self.assertIn("NOT mice", oa)

        s2 = compile_for_semantic_scholar_bulk(q)
        self.assertIn("|", s2)
        self.assertIn("+", s2)
        self.assertIn("-mice", s2)

        cr = compile_for_crossref('au:Millet AND jo:"Sports Medicine" AND "trail running"')
        self.assertIn("Millet", cr.get("author", ""))
        self.assertIn("Sports Medicine", cr.get("container_title", ""))
        self.assertIn("trail running", cr.get("bibliographic", ""))

    def test_in_memory_matcher_and_sqlite_query(self) -> None:
        pub1 = RawPublication(
            source="pubmed",
            external_id="pmid:1",
            title="Heart Rate Variability and Sleep Deprivation in Ultra-Trail Runners",
            abstract="30 recreational humans participated in a randomized crossover field trial (n = 30, p < 0.01).",
            authors=["Millet GP", "Hurduc S"],
            journal="Sports Medicine",
            publication_date="2024-06-01",
            publication_year=2024,
            doi="10.1007/test-1",
            pmid="1",
            citation_count=25,
            raw_publication_types=["Randomized Controlled Trial"],
            mesh_terms=["Running", "Sleep Deprivation"],
            is_open_access=True,
        )
        pub2 = RawPublication(
            source="openalex",
            external_id="oa:2",
            title="Glycogen Depletion in Mice During Exhaustive Treadmill Running",
            abstract="Murine animal model evaluating muscle glycogenolysis in Wistar rats and mice.",
            authors=["Smith J"],
            journal="Lab Physiology",
            publication_date="2019-03-01",
            publication_year=2019,
            citation_count=4,
            raw_publication_types=["Preprint"],
            is_open_access=False,
        )

        self.assertTrue(matches_boolean_query(pub1, 'ti:"Heart Rate Variability" AND (sleep OR HRV) NOT mice'))
        self.assertTrue(matches_boolean_query(pub1, 'au:Millet AND jo:"Sports Medicine" AND therm* OR ultra*'))
        self.assertFalse(matches_boolean_query(pub2, 'running NOT (mice OR murine)'))

        prof = generate_topic_profile(
            name="Sommeil & VFC Trail",
            boolean_query='("ultra-trail" OR "trail runners") AND (sleep OR variability) NOT mice',
            audit_start_year=2020,
            audit_end_year=2025,
            humans_only=True,
            open_access_only=True,
            exclude_preprints=True,
            min_citations=10,
            min_sample_size=20,
            allowed_publication_types=["randomized_controlled_trial"],
        )

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            cfg = AppConfig(base_dir=Path(tmp))
            classifier = ScientificClassifier6D(cfg)
            c1 = classifier.classify_single(MergedPublicationRecord(raw=pub1, sources=["pubmed", "openalex"]), prof)
            c2 = classifier.classify_single(MergedPublicationRecord(raw=pub2, sources=["openalex"]), prof)
            self.assertIsNotNone(c1)
            self.assertIsNone(c2)
            assert c1 is not None

            store = SciWatchStore(cfg.db_path)
            store.upsert_publications([c1])

            hits = store.query_publications(
                topic_slug=prof.slug,
                search_query='au:Millet AND ("ultra-trail" OR "sleep deprivation"[MeSH]) NOT animal',
                year_from=2023,
                year_to=2025,
                min_citations=20,
                only_open_access=True,
                exclude_preprints=True,
            )
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].pmid, "1")

            misses = store.query_publications(
                topic_slug=prof.slug,
                search_query='au:Millet AND ti:swimming',
            )
            self.assertEqual(len(misses), 0)

    def test_rest_api_boolean_create_update_and_query(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp_dir = Path(tmp)
            cfg = AppConfig(base_dir=tmp_dir)
            cfg.api_secret = "test-secret"
            cfg.ensure_dirs()

            server = create_http_server(host="127.0.0.1", port=0, config=cfg)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                # 1. Invalid boolean query -> 400
                req_bad = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/profiles",
                    data=json.dumps({"name": "Bad Query", "boolean_query": '("trail" AND '}).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-SciWatch-Secret": cfg.api_secret,
                        "X-SciWatch-Role": "admin",
                    },
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx_bad:
                    urllib.request.urlopen(req_bad, timeout=5)
                self.assertEqual(ctx_bad.exception.code, 400)

                # 2. Valid parameterized create
                req_create = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/profiles",
                    data=json.dumps(
                        {
                            "name": "Hydratation Sodium Ultra",
                            "boolean_query": '(hydration OR sodium) AND ("ultra-trail" OR marathon) NOT mice',
                            "audit_start_year": 2018,
                            "audit_end_year": 2025,
                            "enabled_sources": ["pubmed", "openalex"],
                            "humans_only": True,
                            "open_access_only": True,
                            "exclude_preprints": True,
                            "min_citations": 5,
                            "max_results_per_source": 50,
                        }
                    ).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-SciWatch-Secret": cfg.api_secret,
                        "X-SciWatch-Role": "admin",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req_create, timeout=5) as resp:
                    self.assertEqual(resp.status, 201)
                    created = json.loads(resp.read().decode("utf-8"))["profile"]
                    self.assertEqual(created["audit_end_year"], 2025)
                    self.assertEqual(created["enabled_sources"], ["pubmed", "openalex"])
                    self.assertTrue(created["humans_only"])
                    self.assertTrue(created["open_access_only"])

                # 3. PUT /api/profiles updates parameters cleanly
                req_put = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/profiles",
                    data=json.dumps(
                        {
                            "topic": created["slug"],
                            "boolean_query": '("gut training" OR carbohydrate) AND "trail running" NOT mice',
                            "min_citations": 12,
                            "allowed_publication_types": ["meta_analysis", "randomized_controlled_trial"],
                        }
                    ).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-SciWatch-Secret": cfg.api_secret,
                        "X-SciWatch-Role": "admin",
                    },
                    method="PUT",
                )
                with urllib.request.urlopen(req_put, timeout=5) as resp:
                    self.assertEqual(resp.status, 200)
                    updated = json.loads(resp.read().decode("utf-8"))["profile"]
                    self.assertEqual(updated["min_citations"], 12)
                    self.assertIn("gut training", updated["boolean_query"])
                    self.assertEqual(
                        updated["allowed_publication_types"],
                        ["meta_analysis", "randomized_controlled_trial"],
                    )

                # 4. GET /api/publications exposes boolean_engine: True
                req_pubs = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/publications?topic={created['slug']}&q=hydration%20OR%20sodium",
                    headers={"X-SciWatch-Secret": cfg.api_secret, "X-SciWatch-Role": "reader"},
                )
                with urllib.request.urlopen(req_pubs, timeout=5) as resp:
                    pub_payload = json.loads(resp.read().decode("utf-8"))
                    self.assertTrue(pub_payload.get("boolean_engine"))
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
