"""
Tests de la base SQLite, des exporteurs (Markdown, CSV, JSON, myKairn Knowledge Pack) et du serveur API REST.
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
from mykairn_sciwatch.config import AppConfig, resolve_profile
from mykairn_sciwatch.connectors.aggregator import MergedPublicationRecord
from mykairn_sciwatch.models import RawPublication, WatchRunSummary
from mykairn_sciwatch.reporting.exporters import (
    export_to_csv,
    export_to_json,
    export_to_mykairn_knowledge_pack,
)
from mykairn_sciwatch.reporting.markdown_report import generate_markdown_report
from mykairn_sciwatch.storage.sqlite_store import SciWatchStore
from mykairn_sciwatch.web.server import create_http_server


class TestStoragePipelineAndApi(unittest.TestCase):
    def test_sqlite_store_and_reports_and_api(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp_dir = Path(tmp)
            cfg = AppConfig(base_dir=tmp_dir)
            cfg.db_path = tmp_dir / "data" / "test_sciwatch.db"
            cfg.reports_dir = tmp_dir / "reports"
            cfg.profiles_dir = Path(__file__).resolve().parent.parent / "profiles"
            cfg.ensure_dirs()

            profile = resolve_profile("trail_running_coaching", cfg.profiles_dir)
            classifier = ScientificClassifier6D(cfg)

            sample_raw = RawPublication(
                source="pubmed",
                external_id="pmid:40100",
                title="Downhill Running Biomechanics, Eccentric Muscle Damage and Pole Usage in Amateur Trail Runners: A Randomized Controlled Trial",
                abstract=(
                    "Methods: 36 recreational trail runners were randomly assigned to a downhill training protocol with or without poles. "
                    "Results: Using poles reduced neuromuscular fatigue and heart rate drift (p < 0.01). "
                    "Conclusions: Coaches should integrate pole technique and progressive downhill sessions."
                ),
                authors=["Vercruyssen F", "Easthope C"],
                journal="International Journal of Sports Physiology and Performance",
                publication_date="2025-04-01",
                publication_year=2025,
                doi="10.1123/ijspp.2025-0042",
                pmid="40100",
                citation_count=18,
                raw_publication_types=["Randomized Controlled Trial"],
                is_open_access=True,
            )
            pub = classifier.classify_single(
                MergedPublicationRecord(raw=sample_raw, sources=["pubmed", "openalex"]),
                profile,
            )
            self.assertIsNotNone(pub)
            assert pub is not None

            store = SciWatchStore(cfg.db_path)
            ins, upd = store.upsert_publications([pub])
            self.assertEqual(ins, 1)
            self.assertEqual(upd, 0)

            # Second upsert updates existing record
            ins2, upd2 = store.upsert_publications([pub])
            self.assertEqual(ins2, 0)
            self.assertEqual(upd2, 1)

            queried = store.query_publications(
                topic_slug="trail_running_coaching",
                theme="biomechanics_uphill_downhill_poles",
            )
            self.assertEqual(len(queried), 1)
            self.assertEqual(queried[0].publication_type, "randomized_controlled_trial")

            analytics = store.get_analytics("trail_running_coaching")
            self.assertEqual(analytics["total_publications"], 1)

            # Test Reports & Exports
            run_summary = WatchRunSummary(
                run_id="test-run-1",
                topic_slug=profile.slug,
                mode="audit",
                started_at="2026-11-24T10:00:00Z",
                finished_at="2026-11-24T10:01:00Z",
                status="completed",
                raw_fetched_count=1,
                deduplicated_count=1,
                classified_count=1,
                new_inserted_count=1,
                updated_count=0,
                sources_breakdown={"pubmed": 1},
                themes_breakdown={pub.primary_theme: 1},
                types_breakdown={pub.publication_type: 1},
            )
            store.record_run(run_summary)

            md_path = generate_markdown_report(profile, queried, analytics, run_summary, cfg.reports_dir)
            self.assertTrue(md_path.is_file())
            self.assertIn("Takeaway Coaching", md_path.read_text(encoding="utf-8"))

            csv_text = export_to_csv(queried, cfg.reports_dir / "out.csv")
            self.assertIn("randomized_controlled_trial", csv_text)

            json_text = export_to_json(queried, analytics, cfg.reports_dir / "out.json")
            self.assertIn("10.1123/ijspp.2025-0042", json_text)

            pack = export_to_mykairn_knowledge_pack(profile, queried, cfg.reports_dir / "pack.json")
            self.assertEqual(pack["schema_version"], "mykairn-sciwatch-pack/v1")
            self.assertEqual(len(pack["evidence_cards"]), 1)

            # Test Web Server REST API on ephemeral port
            server = create_http_server(host="127.0.0.1", port=0, config=cfg)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5) as resp:
                    health = json.loads(resp.read().decode("utf-8"))
                    self.assertEqual(health["status"], "ok")

                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/publications?topic=trail_running_coaching",
                    timeout=5,
                ) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    self.assertEqual(data["count"], 1)
            finally:
                server.shutdown()
                server.server_close()

    def test_api_security_secret_roles_lan_and_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp_dir = Path(tmp)
            cfg = AppConfig(base_dir=tmp_dir)
            cfg.db_path = tmp_dir / "data" / "test_sec.db"
            cfg.reports_dir = tmp_dir / "reports"
            cfg.profiles_dir = Path(__file__).resolve().parent.parent / "profiles"
            cfg.api_secret = "super-secret-token-xyz"
            cfg.allow_lan_direct = True
            cfg.trusted_lan_prefixes = ("192.168.",)
            cfg.ensure_dirs()

            server = create_http_server(host="127.0.0.1", port=0, config=cfg)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                # 1. /api/health stays public but minimal when unauthenticated
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5) as resp:
                    health = json.loads(resp.read().decode("utf-8"))
                    self.assertEqual(health["status"], "ok")
                    self.assertNotIn("llm_provider", health)

                # 2. Unauthenticated GET /api/profiles -> 401
                with self.assertRaises(urllib.error.HTTPError) as ctx401:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/api/profiles", timeout=5)
                self.assertEqual(ctx401.exception.code, 401)

                # 3. Proxy headers spoof even from 127.0.0.1 -> still 401 without secret
                req_proxy = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/profiles",
                    headers={"CF-Connecting-IP": "192.168.1.50"},
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx_proxy:
                    urllib.request.urlopen(req_proxy, timeout=5)
                self.assertEqual(ctx_proxy.exception.code, 401)

                # 4. Valid secret + reader role -> 200 on GET, 403 on POST /api/run & /api/profiles
                req_reader_get = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/profiles",
                    headers={"X-SciWatch-Secret": cfg.api_secret, "X-SciWatch-Role": "reader"},
                )
                with urllib.request.urlopen(req_reader_get, timeout=5) as resp:
                    self.assertEqual(resp.status, 200)

                req_reader_post = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/run",
                    data=b'{"topic":"trail_running_coaching","mode":"watch"}',
                    headers={
                        "Content-Type": "application/json",
                        "X-SciWatch-Secret": cfg.api_secret,
                        "X-SciWatch-Role": "reader",
                    },
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx403:
                    urllib.request.urlopen(req_reader_post, timeout=5)
                self.assertEqual(ctx403.exception.code, 403)

                # 5. Path traversal attempt in topic -> 400
                req_traversal = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/export?topic=../../etc/passwd&format=markdown",
                    headers={"X-SciWatch-Secret": cfg.api_secret, "X-SciWatch-Role": "reader"},
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx400:
                    urllib.request.urlopen(req_traversal, timeout=5)
                self.assertEqual(ctx400.exception.code, 400)

                # 6. DELETE /api/profiles: reader -> 403, admin on temp profile -> 200
                req_del_reader = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/profiles?topic=temp_del_test",
                    headers={"X-SciWatch-Secret": cfg.api_secret, "X-SciWatch-Role": "reader"},
                    method="DELETE",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx_del_403:
                    urllib.request.urlopen(req_del_reader, timeout=5)
                self.assertEqual(ctx_del_403.exception.code, 403)

                cfg.profiles_dir = tmp_dir / "profiles"
                cfg.profiles_dir.mkdir(parents=True, exist_ok=True)
                req_create = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/profiles",
                    data=json.dumps({"name": "Temp Del Test", "keywords": ["trail", "sleep"]}).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-SciWatch-Secret": cfg.api_secret,
                        "X-SciWatch-Role": "admin",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req_create, timeout=5) as resp:
                    self.assertEqual(resp.status, 201)
                    created_slug = json.loads(resp.read().decode("utf-8"))["profile"]["slug"]

                req_del_admin = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/profiles?topic={created_slug}",
                    headers={"X-SciWatch-Secret": cfg.api_secret, "X-SciWatch-Role": "admin"},
                    method="DELETE",
                )
                with urllib.request.urlopen(req_del_admin, timeout=5) as resp:
                    self.assertEqual(resp.status, 200)
                    del_payload = json.loads(resp.read().decode("utf-8"))
                    self.assertEqual(del_payload["status"], "deleted")
                    self.assertEqual(del_payload["removed_files"], 1)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
