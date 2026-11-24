"""
Serveur HTTP/REST API multithread léger (bibliothèque standard Python) pour le Dashboard myKairn SciWatch.
"""

from __future__ import annotations

import hmac
import json
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

_VALID_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_RUN_LOCK = threading.Lock()
_MAX_POST_BYTES = 65_536
_PROXY_HEADERS = ("CF-Connecting-IP", "CF-Ray", "X-Forwarded-For", "X-Forwarded-Host", "Forwarded")

from mykairn_sciwatch.config import AppConfig, list_topic_profiles, resolve_profile, save_topic_profile
from mykairn_sciwatch.pipeline import SciWatchPipeline
from mykairn_sciwatch.profile_generator import generate_topic_profile
from mykairn_sciwatch.reporting.exporters import (
    export_to_csv,
    export_to_json,
    export_to_mykairn_knowledge_pack,
)
from mykairn_sciwatch.reporting.markdown_report import generate_markdown_report
from mykairn_sciwatch.web.dashboard_ui import DASHBOARD_HTML


class SciWatchHTTPRequestHandler(BaseHTTPRequestHandler):
    """Gestionnaire HTTP pour le Dashboard Web et l'API REST myKairn SciWatch."""

    pipeline: SciWatchPipeline

    def log_message(self, fmt: str, *args: Any) -> None:
        # Journalisation sobre compatible journalctl systemd
        print(f"[SciWatch-Web] {self.address_string()} - {fmt % args}")

    def _authenticate_request(self) -> Optional[str]:
        """Retourne 'admin', 'reader' ou None selon le secret HMAC et la provenance réseau."""
        cfg = self.pipeline.config
        header_secret = (self.headers.get("X-SciWatch-Secret") or "").strip()
        auth_hdr = (self.headers.get("Authorization") or "").strip()
        bearer_secret = auth_hdr[7:].strip() if auth_hdr.lower().startswith("bearer ") else ""
        provided = header_secret or bearer_secret

        req_role = (self.headers.get("X-SciWatch-Role") or "").strip().lower()
        resolved_role = "admin" if req_role == "admin" else "reader"

        has_proxy_headers = any(bool(self.headers.get(h)) for h in _PROXY_HEADERS)
        client_ip = self.client_address[0] if self.client_address else ""

        if cfg.api_secret:
            if provided and hmac.compare_digest(
                provided.encode("utf-8"), cfg.api_secret.encode("utf-8")
            ):
                return resolved_role
            if (
                not has_proxy_headers
                and cfg.allow_lan_direct
                and cfg.trusted_lan_prefixes
                and client_ip.startswith(cfg.trusted_lan_prefixes)
            ):
                # Accès direct LAN maison (192.168.x.x / 10.x.x.x) autorisé sans clé
                return "admin"
            return None

        # Sans SCIWATCH_API_SECRET (tests/dev local), respecte X-SciWatch-Role si fourni
        return resolved_role if req_role in ("admin", "reader") else "admin"

    def _validate_slug_param(self, raw: Optional[str]) -> Optional[str]:
        if raw is None or raw == "":
            return None
        val = raw.strip()
        if not _VALID_SLUG_RE.match(val):
            return "__INVALID__"
        return val

    def _send_security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        origin = (self.headers.get("Origin") or "").strip()
        allowed_origin = self.pipeline.config.cors_allowed_origin
        if origin and allowed_origin and origin == allowed_origin:
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_text(
        self,
        text: str,
        content_type: str = "text/html; charset=utf-8",
        status: int = 200,
        filename: Optional[str] = None,
    ) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = urllib.parse.parse_qs(parsed.query)

        def q_val(key: str, default: str = "") -> str:
            vals = qs.get(key)
            return vals[0] if vals else default

        if path == "/api/health":
            auth_role = self._authenticate_request()
            if auth_role is None:
                self._send_json({"status": "ok", "service": "mykairn-sciwatch"})
                return
            profiles = list_topic_profiles(self.pipeline.config.profiles_dir)
            self._send_json(
                {
                    "status": "ok",
                    "service": "mykairn-sciwatch",
                    "version": "1.0.0",
                    "profiles_count": len(profiles),
                    "llm_enabled": self.pipeline.classifier.llm.is_enabled,
                    "llm_provider": self.pipeline.config.llm_provider,
                }
            )
            return

        role = self._authenticate_request()
        if role is None:
            self._send_json({"error": "Non autorisé — clé SciWatch requise."}, status=401)
            return

        if path == "/":
            self._send_text(DASHBOARD_HTML)
            return

        if path == "/api/profiles":
            profiles = list_topic_profiles(self.pipeline.config.profiles_dir)
            self._send_json({"profiles": [p.to_dict() for p in profiles]})
            return

        if path == "/api/analytics":
            topic = self._validate_slug_param(q_val("topic") or None)
            if topic == "__INVALID__":
                self._send_json({"error": "Identifiant de sujet invalide."}, status=400)
                return
            analytics = self.pipeline.store.get_analytics(topic_slug=topic)
            self._send_json(analytics)
            return

        if path == "/api/publications":
            topic = self._validate_slug_param(q_val("topic") or None)
            if topic == "__INVALID__":
                self._send_json({"error": "Identifiant de sujet invalide."}, status=400)
                return
            theme = q_val("theme") or None
            pub_type = q_val("type") or None
            athlete_level = q_val("athlete_level") or None
            grade = q_val("grade") or None
            search_q = q_val("q") or None
            sort_by = q_val("sort", "overall_score")
            min_q = float(q_val("min_quality", "0") or 0)
            min_s = float(q_val("min_scope", "0") or 0)
            limit = min(500, max(1, int(q_val("limit", "150") or 150)))

            pubs = self.pipeline.store.query_publications(
                topic_slug=topic,
                theme=theme,
                publication_type=pub_type,
                athlete_level=athlete_level,
                quality_grade=grade,
                min_quality=min_q,
                min_scope=min_s,
                search_query=search_q,
                sort_by=sort_by,
                limit=limit,
            )
            self._send_json({"count": len(pubs), "publications": [p.to_dict() for p in pubs]})
            return

        if path == "/api/runs":
            topic = self._validate_slug_param(q_val("topic") or None)
            if topic == "__INVALID__":
                self._send_json({"error": "Identifiant de sujet invalide."}, status=400)
                return
            runs = self.pipeline.store.list_runs(topic_slug=topic)
            self._send_json({"runs": runs})
            return

        if path == "/api/export":
            topic = self._validate_slug_param(q_val("topic", "trail_running_coaching"))
            if not topic or topic == "__INVALID__":
                self._send_json({"error": "Identifiant de sujet invalide."}, status=400)
                return
            fmt = q_val("format", "json").lower()
            pubs = self.pipeline.store.query_publications(topic_slug=topic, limit=1000)
            analytics = self.pipeline.store.get_analytics(topic_slug=topic)

            if fmt == "csv":
                csv_text = export_to_csv(pubs)
                self._send_text(
                    csv_text,
                    content_type="text/csv; charset=utf-8",
                    filename=f"{topic}_sciwatch.csv",
                )
                return

            if fmt == "markdown":
                md_file = self.pipeline.config.reports_dir / f"{topic}_latest.md"
                if md_file.is_file():
                    md_text = md_file.read_text(encoding="utf-8")
                else:
                    profile = resolve_profile(topic, self.pipeline.config.profiles_dir)
                    from mykairn_sciwatch.models import WatchRunSummary

                    dummy_run = WatchRunSummary(
                        run_id="export",
                        topic_slug=topic,
                        mode="audit",
                        started_at="",
                        finished_at="",
                        status="completed",
                        raw_fetched_count=len(pubs),
                        deduplicated_count=len(pubs),
                        classified_count=len(pubs),
                        new_inserted_count=0,
                        updated_count=0,
                        sources_breakdown={},
                        themes_breakdown={},
                        types_breakdown={},
                    )
                    generated = generate_markdown_report(
                        profile, pubs, analytics, dummy_run, self.pipeline.config.reports_dir
                    )
                    md_text = generated.read_text(encoding="utf-8")
                self._send_text(
                    md_text,
                    content_type="text/markdown; charset=utf-8",
                    filename=f"{topic}_report.md",
                )
                return

            if fmt == "mykairn":
                profile = resolve_profile(topic, self.pipeline.config.profiles_dir)
                pack = export_to_mykairn_knowledge_pack(profile, pubs)
                self._send_json(pack)
                return

            json_text = export_to_json(pubs, analytics=analytics)
            self._send_text(
                json_text,
                content_type="application/json; charset=utf-8",
                filename=f"{topic}_sciwatch.json",
            )
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        role = self._authenticate_request()
        if role is None:
            self._send_json({"error": "Non autorisé — clé SciWatch requise."}, status=401)
            return
        if role != "admin":
            self._send_json({"error": "Action réservée à l'administrateur."}, status=403)
            return

        try:
            content_len = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            self._send_json({"error": "Invalid Content-Length"}, status=400)
            return
        if content_len < 0 or content_len > _MAX_POST_BYTES:
            self._send_json({"error": "Payload trop volumineux (max 64 Ko)."}, status=413)
            return

        raw_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, status=400)
            return

        if path == "/api/run":
            topic = self._validate_slug_param(str(body.get("topic", "trail_running_coaching")))
            if not topic or topic == "__INVALID__":
                self._send_json({"error": "Identifiant de sujet invalide."}, status=400)
                return
            mode = str(body.get("mode", "audit"))
            if mode not in ("audit", "watch"):
                self._send_json({"error": "Mode invalide (audit ou watch)."}, status=400)
                return
            days = body.get("lookback_days")
            max_per_source = body.get("max_per_source")

            if not _RUN_LOCK.acquire(blocking=False):
                self._send_json({"error": "Un audit ou une veille est déjà en cours."}, status=409)
                return
            try:
                summary = self.pipeline.run_for_profile(
                    profile_or_slug=topic,
                    mode=mode,
                    lookback_days=int(days) if days else None,
                    max_per_source=int(max_per_source) if max_per_source else None,
                )
                self._send_json(summary.to_dict())
            except Exception as err:
                self._send_json({"status": "failed", "error": str(err)}, status=500)
            finally:
                _RUN_LOCK.release()
            return

        if path == "/api/profiles":
            name = str(body.get("name", "")).strip()
            if not name:
                self._send_json({"error": "Le champ 'name' est obligatoire"}, status=400)
                return
            keywords = body.get("keywords") or []
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",") if k.strip()]
            domain = str(body.get("domain", "general_science"))
            description = str(body.get("description", ""))
            start_year = int(body.get("audit_start_year", 2016))

            profile = generate_topic_profile(
                name=name,
                description=description,
                domain=domain,
                seed_keywords=keywords,
                audit_start_year=start_year,
            )
            saved_path = save_topic_profile(profile, self.pipeline.config.profiles_dir)
            self._send_json(
                {
                    "status": "created",
                    "path": str(saved_path),
                    "profile": profile.to_dict(),
                },
                status=201,
            )
            return

        self._send_json({"error": "Not found"}, status=404)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def create_http_server(
    host: str = "0.0.0.0",
    port: int = 8095,
    config: Optional[AppConfig] = None,
) -> ThreadingHTTPServer:
    """Instancie le serveur ThreadingHTTPServer configuré avec SciWatchPipeline."""
    cfg = config or AppConfig()
    pipeline = SciWatchPipeline(cfg)

    class BoundHandler(SciWatchHTTPRequestHandler):
        pass

    BoundHandler.pipeline = pipeline
    return ReusableThreadingHTTPServer((host, port), BoundHandler)


def run_web_server(
    host: str = "0.0.0.0",
    port: int = 8095,
    config: Optional[AppConfig] = None,
) -> None:
    """Lance le serveur Web du Dashboard myKairn SciWatch."""
    server = create_http_server(host=host, port=port, config=config)
    print(f"🔬 Dashboard myKairn SciWatch démarré sur http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur myKairn SciWatch.")
    finally:
        server.server_close()
