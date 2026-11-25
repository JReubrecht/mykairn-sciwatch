"""
Serveur HTTP/REST API multithread léger (bibliothèque standard Python) pour le Dashboard myKairn SciWatch.
"""

from __future__ import annotations

import hmac
import json
import re
import threading
import urllib.parse
from dataclasses import replace as dc_replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

_VALID_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_RUN_LOCK = threading.Lock()
_MAX_POST_BYTES = 524_288
_PROXY_HEADERS = ("CF-Connecting-IP", "CF-Ray", "X-Forwarded-For", "X-Forwarded-Host", "Forwarded")

from mykairn_sciwatch.config import AppConfig, list_topic_profiles, resolve_profile, save_topic_profile
from mykairn_sciwatch.connectors.aggregator import deduplicate_publications
from mykairn_sciwatch.connectors.pedro import parse_pedro_ris
from mykairn_sciwatch.pipeline import SciWatchPipeline
from mykairn_sciwatch.profile_generator import generate_topic_profile
from mykairn_sciwatch.reporting.exporters import (
    export_to_csv,
    export_to_json,
    export_to_mykairn_knowledge_pack,
)
from mykairn_sciwatch.reporting.markdown_report import generate_markdown_report
from mykairn_sciwatch.search_syntax import build_boolean_from_blocks, validate_boolean_query
from mykairn_sciwatch.web.dashboard_ui import DASHBOARD_HTML


def _parse_bool_flag(val: Any, default: bool = False) -> bool:
    if val is None or val == "":
        return default
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _parse_str_list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        return [s.strip() for s in val.split(",") if s.strip()]
    return []


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
            min_cit = int(q_val("min_citations", "0") or 0)
            min_n = int(q_val("min_sample_size", "0") or 0)
            year_from_raw = q_val("year_from")
            year_to_raw = q_val("year_to")
            year_from = int(year_from_raw) if year_from_raw and year_from_raw.isdigit() else None
            year_to = int(year_to_raw) if year_to_raw and year_to_raw.isdigit() else None
            only_foundational = _parse_bool_flag(q_val("only_foundational"), False)
            only_open_access = _parse_bool_flag(q_val("only_open_access"), False)
            exclude_preprints = _parse_bool_flag(q_val("exclude_preprints"), False)
            source_param = q_val("source")
            sources_filter = _parse_str_list(source_param) if source_param else None
            limit = min(500, max(1, int(q_val("limit", "150") or 150)))

            query_warning: Optional[str] = None
            if search_q:
                val_res = validate_boolean_query(search_q)
                if not val_res["valid"]:
                    query_warning = val_res["error"]

            pubs = self.pipeline.store.query_publications(
                topic_slug=topic,
                theme=theme,
                publication_type=pub_type,
                athlete_level=athlete_level,
                quality_grade=grade,
                min_quality=min_q,
                min_scope=min_s,
                min_citations=min_cit,
                min_sample_size=min_n,
                year_from=year_from,
                year_to=year_to,
                search_query=search_q,
                only_foundational=only_foundational,
                only_open_access=only_open_access,
                exclude_preprints=exclude_preprints,
                sources_filter=sources_filter,
                sort_by=sort_by,
                limit=limit,
            )
            payload: Dict[str, Any] = {
                "count": len(pubs),
                "publications": [p.to_dict() for p in pubs],
                "boolean_engine": True,
            }
            if query_warning:
                payload["query_warning"] = query_warning
            self._send_json(payload)
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
            req_sources = _parse_str_list(body.get("enabled_sources")) or None
            override_bool = str(body.get("boolean_query", "") or "").strip()
            if override_bool:
                v_bool = validate_boolean_query(override_bool)
                if not v_bool["valid"]:
                    self._send_json({"error": f"Équation booléenne invalide : {v_bool['error']}"}, status=400)
                    return

            if not _RUN_LOCK.acquire(blocking=False):
                self._send_json({"error": "Un audit ou une veille est déjà en cours."}, status=409)
                return
            try:
                base_profile = resolve_profile(topic, self.pipeline.config.profiles_dir)
                replace_kwargs: Dict[str, Any] = {}
                if override_bool:
                    replace_kwargs["boolean_query"] = override_bool
                    if not body.get("queries"):
                        replace_kwargs["queries"] = [override_bool]
                if isinstance(body.get("queries"), list) and body["queries"]:
                    replace_kwargs["queries"] = [str(q).strip() for q in body["queries"] if str(q).strip()]
                if body.get("audit_start_year"):
                    replace_kwargs["audit_start_year"] = int(body["audit_start_year"])
                if "audit_end_year" in body:
                    raw_ey = body.get("audit_end_year")
                    replace_kwargs["audit_end_year"] = int(raw_ey) if raw_ey not in (None, "", 0) else None
                if "allowed_publication_types" in body:
                    replace_kwargs["allowed_publication_types"] = _parse_str_list(body.get("allowed_publication_types"))
                if "humans_only" in body:
                    replace_kwargs["humans_only"] = _parse_bool_flag(body.get("humans_only"), False)
                if "open_access_only" in body:
                    replace_kwargs["open_access_only"] = _parse_bool_flag(body.get("open_access_only"), False)
                if "exclude_preprints" in body:
                    replace_kwargs["exclude_preprints"] = _parse_bool_flag(body.get("exclude_preprints"), False)
                if "strict_boolean" in body:
                    replace_kwargs["strict_boolean"] = _parse_bool_flag(body.get("strict_boolean"), True)
                if "search_languages" in body:
                    replace_kwargs["search_languages"] = _parse_str_list(body.get("search_languages"))
                if "min_citations" in body and body.get("min_citations") is not None:
                    replace_kwargs["min_citations"] = max(0, int(body["min_citations"]))
                if "min_sample_size" in body and body.get("min_sample_size") is not None:
                    replace_kwargs["min_sample_size"] = max(0, int(body["min_sample_size"]))
                if "min_quality_score" in body and body.get("min_quality_score") is not None:
                    replace_kwargs["min_quality_score"] = max(0.0, float(body["min_quality_score"]))
                if "min_relevance_score" in body and body.get("min_relevance_score") is not None:
                    replace_kwargs["min_relevance_score"] = max(0.0, float(body["min_relevance_score"]))
                if "pedro_subdiscipline" in body:
                    replace_kwargs["pedro_subdiscipline"] = str(body.get("pedro_subdiscipline") or "").strip()
                if "pedro_therapy" in body:
                    replace_kwargs["pedro_therapy"] = str(body.get("pedro_therapy") or "").strip()
                if "pedro_min_score" in body and body.get("pedro_min_score") is not None:
                    replace_kwargs["pedro_min_score"] = max(0, min(10, int(body["pedro_min_score"])))

                effective_profile = dc_replace(base_profile, **replace_kwargs) if replace_kwargs else base_profile
                if _parse_bool_flag(body.get("persist_overrides"), False) and replace_kwargs:
                    save_topic_profile(effective_profile, self.pipeline.config.profiles_dir)

                summary = self.pipeline.run_for_profile(
                    profile_or_slug=effective_profile,
                    mode=mode,
                    lookback_days=int(days) if days else None,
                    max_per_source=int(max_per_source) if max_per_source else None,
                    enabled_sources=req_sources,
                )
                result_payload = summary.to_dict()
                if (
                    self.pipeline.config.mykairn_webhook_url
                    and self.pipeline.config.mykairn_webhook_secret
                ):
                    try:
                        all_pubs = self.pipeline.store.query_publications(
                            topic_slug=effective_profile.slug,
                            limit=500,
                        )
                        pack = export_to_mykairn_knowledge_pack(effective_profile, all_pubs)
                        result_payload["webhook_synced"] = self.pipeline.notifier.push_webhook(pack)
                    except Exception:
                        result_payload["webhook_synced"] = False
                self._send_json(result_payload)
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
            keywords = _parse_str_list(body.get("keywords"))
            boolean_query = str(body.get("boolean_query", "") or "").strip()
            query_blocks = body.get("query_blocks") if isinstance(body.get("query_blocks"), list) else []
            if not keywords and not boolean_query and not query_blocks:
                self._send_json(
                    {"error": "Renseignez des mots-clés, des blocs PICO ou une équation booléenne."},
                    status=400,
                )
                return
            domain = str(body.get("domain", "general_science"))
            description = str(body.get("description", ""))
            start_year = int(body.get("audit_start_year", 2016) or 2016)
            raw_end = body.get("audit_end_year")
            end_year = int(raw_end) if raw_end not in (None, "", 0) else None
            slug_override = self._validate_slug_param(body.get("slug") or None)
            if slug_override == "__INVALID__":
                self._send_json({"error": "Identifiant de sujet invalide."}, status=400)
                return

            try:
                profile = generate_topic_profile(
                    name=name,
                    description=description,
                    domain=domain,
                    seed_keywords=keywords,
                    audit_start_year=start_year,
                    audit_end_year=end_year,
                    watch_lookback_days=int(body.get("watch_lookback_days", 30) or 30),
                    boolean_query=boolean_query,
                    custom_queries=_parse_str_list(body.get("queries")) or (
                        [str(q).strip() for q in body.get("queries", []) if str(q).strip()]
                        if isinstance(body.get("queries"), list)
                        else None
                    ),
                    query_blocks=query_blocks,
                    exclusion_keywords=_parse_str_list(body.get("exclusion_keywords")),
                    high_impact_journals=_parse_str_list(body.get("high_impact_journals")) or None,
                    enabled_sources=_parse_str_list(body.get("enabled_sources")) or None,
                    allowed_publication_types=_parse_str_list(body.get("allowed_publication_types")),
                    humans_only=_parse_bool_flag(body.get("humans_only"), False),
                    open_access_only=_parse_bool_flag(body.get("open_access_only"), False),
                    exclude_preprints=_parse_bool_flag(body.get("exclude_preprints"), False),
                    strict_boolean=_parse_bool_flag(body.get("strict_boolean"), True),
                    search_languages=_parse_str_list(body.get("search_languages")),
                    min_citations=int(body.get("min_citations", 0) or 0),
                    min_sample_size=int(body.get("min_sample_size", 0) or 0),
                    min_relevance_score=float(body.get("min_relevance_score", 10.0) or 10.0),
                    min_quality_score=float(body.get("min_quality_score", 0.0) or 0.0),
                    max_results_per_source=int(body.get("max_results_per_source", 30) or 30),
                    pedro_subdiscipline=str(body.get("pedro_subdiscipline", "") or "").strip(),
                    pedro_therapy=str(body.get("pedro_therapy", "") or "").strip(),
                    pedro_min_score=max(0, min(10, int(body.get("pedro_min_score", 0) or 0))),
                    slug_override=slug_override,
                )
            except ValueError as err:
                self._send_json({"error": str(err)}, status=400)
                return

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

        if path == "/api/import-ris":
            topic = self._validate_slug_param(str(body.get("topic", "trail_running_coaching")))
            if not topic or topic == "__INVALID__":
                self._send_json({"error": "Identifiant de sujet invalide."}, status=400)
                return
            ris_text = str(body.get("ris_text", "") or "")
            if not ris_text.strip():
                self._send_json({"error": "Contenu RIS vide."}, status=400)
                return
            try:
                profile = resolve_profile(topic, self.pipeline.config.profiles_dir)
                raw_items = parse_pedro_ris(ris_text)
                if not raw_items:
                    self._send_json({"error": "Aucune notice valide détectée dans ce fichier RIS."}, status=400)
                    return
                merged = deduplicate_publications(raw_items)
                # Pour l'import manuel explicite depuis PEDro, on relâche les filtres d'exclusion de collecte auto
                profile_relaxed = dc_replace(
                    profile,
                    strict_boolean=False,
                    min_relevance_score=0.0,
                    pedro_min_score=0,
                    open_access_only=False,
                    humans_only=False,
                    min_citations=0,
                    min_sample_size=0,
                    min_quality_score=0.0,
                    allowed_publication_types=[],
                )
                classified = self.pipeline.classifier.classify_batch(
                    records=merged,
                    profile=profile_relaxed,
                    max_llm_calls=5,
                )
                inserted, updated = self.pipeline.store.upsert_publications(classified)
                self._send_json(
                    {
                        "status": "imported",
                        "topic": topic,
                        "parsed_count": len(raw_items),
                        "classified_count": len(classified),
                        "inserted": inserted,
                        "updated": updated,
                    },
                    status=200,
                )
            except FileNotFoundError:
                self._send_json({"error": f"Sujet '{topic}' introuvable."}, status=404)
            except Exception as err:
                self._send_json({"error": f"Échec import RIS : {err}"}, status=500)
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_PUT(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = urllib.parse.parse_qs(parsed.query)

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

        if path != "/api/profiles":
            self._send_json({"error": "Not found"}, status=404)
            return

        raw_topic = str(body.get("topic") or body.get("slug") or (qs.get("topic") or [""])[0]).strip()
        topic = self._validate_slug_param(raw_topic)
        if not topic or topic == "__INVALID__":
            self._send_json({"error": "Identifiant de sujet invalide."}, status=400)
            return

        try:
            existing = resolve_profile(topic, self.pipeline.config.profiles_dir)
        except FileNotFoundError:
            self._send_json({"error": f"Sujet '{topic}' introuvable."}, status=404)
            return

        new_bool = str(body.get("boolean_query", existing.boolean_query) or "").strip()
        new_blocks = body.get("query_blocks", existing.query_blocks)
        if not new_bool and isinstance(new_blocks, list) and new_blocks:
            exc_for_build = _parse_str_list(body.get("exclusion_keywords", existing.exclusion_keywords))
            new_bool = build_boolean_from_blocks(new_blocks, exc_for_build)

        if new_bool:
            val = validate_boolean_query(new_bool)
            if not val["valid"]:
                self._send_json({"error": f"Équation booléenne invalide : {val['error']}"}, status=400)
                return
            new_bool = val["normalized"] or new_bool

        raw_queries = body.get("queries")
        if isinstance(raw_queries, list):
            next_queries = [str(q).strip() for q in raw_queries if str(q).strip()]
        else:
            next_queries = list(existing.queries)
        if new_bool and new_bool not in next_queries:
            next_queries = [new_bool, *[q for q in next_queries if q != existing.boolean_query]]

        raw_end = body.get("audit_end_year", existing.audit_end_year)
        next_end_year = int(raw_end) if raw_end not in (None, "", 0) else None

        updated = dc_replace(
            existing,
            name=str(body.get("name", existing.name)).strip() or existing.name,
            description=str(body.get("description", existing.description)),
            domain=str(body.get("domain", existing.domain)),
            boolean_query=new_bool,
            query_blocks=list(new_blocks) if isinstance(new_blocks, list) else existing.query_blocks,
            queries=next_queries or ([new_bool] if new_bool else existing.queries),
            inclusion_keywords=(
                [k.lower() for k in _parse_str_list(body.get("keywords"))]
                if "keywords" in body
                else (
                    [k.lower() for k in _parse_str_list(body.get("inclusion_keywords"))]
                    if "inclusion_keywords" in body
                    else existing.inclusion_keywords
                )
            ),
            exclusion_keywords=(
                [k.lower() for k in _parse_str_list(body.get("exclusion_keywords"))]
                if "exclusion_keywords" in body
                else existing.exclusion_keywords
            ),
            high_impact_journals=(
                _parse_str_list(body.get("high_impact_journals"))
                if "high_impact_journals" in body
                else existing.high_impact_journals
            ),
            audit_start_year=int(body.get("audit_start_year", existing.audit_start_year) or existing.audit_start_year),
            audit_end_year=next_end_year,
            watch_lookback_days=int(body.get("watch_lookback_days", existing.watch_lookback_days) or existing.watch_lookback_days),
            max_results_per_source=max(
                5,
                min(100, int(body.get("max_results_per_source", existing.max_results_per_source) or existing.max_results_per_source)),
            ),
            min_relevance_score=float(body.get("min_relevance_score", existing.min_relevance_score)),
            enabled_sources=(
                _parse_str_list(body.get("enabled_sources")) or existing.enabled_sources
                if "enabled_sources" in body
                else existing.enabled_sources
            ),
            allowed_publication_types=(
                _parse_str_list(body.get("allowed_publication_types"))
                if "allowed_publication_types" in body
                else existing.allowed_publication_types
            ),
            humans_only=_parse_bool_flag(body.get("humans_only"), existing.humans_only)
            if "humans_only" in body
            else existing.humans_only,
            open_access_only=_parse_bool_flag(body.get("open_access_only"), existing.open_access_only)
            if "open_access_only" in body
            else existing.open_access_only,
            exclude_preprints=_parse_bool_flag(body.get("exclude_preprints"), existing.exclude_preprints)
            if "exclude_preprints" in body
            else existing.exclude_preprints,
            strict_boolean=_parse_bool_flag(body.get("strict_boolean"), existing.strict_boolean)
            if "strict_boolean" in body
            else existing.strict_boolean,
            search_languages=(
                _parse_str_list(body.get("search_languages"))
                if "search_languages" in body
                else existing.search_languages
            ),
            min_citations=max(0, int(body.get("min_citations", existing.min_citations) or 0)),
            min_sample_size=max(0, int(body.get("min_sample_size", existing.min_sample_size) or 0)),
            min_quality_score=max(0.0, float(body.get("min_quality_score", existing.min_quality_score) or 0.0)),
            pedro_subdiscipline=str(body.get("pedro_subdiscipline", existing.pedro_subdiscipline) or "").strip(),
            pedro_therapy=str(body.get("pedro_therapy", existing.pedro_therapy) or "").strip(),
            pedro_min_score=max(0, min(10, int(body.get("pedro_min_score", existing.pedro_min_score) or 0))),
        )
        saved_path = save_topic_profile(updated, self.pipeline.config.profiles_dir)
        self._send_json(
            {
                "status": "updated",
                "path": str(saved_path),
                "profile": updated.to_dict(),
            },
            status=200,
        )

    def do_DELETE(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = urllib.parse.parse_qs(parsed.query)

        role = self._authenticate_request()
        if role is None:
            self._send_json({"error": "Non autorisé — clé SciWatch requise."}, status=401)
            return
        if role != "admin":
            self._send_json({"error": "Action réservée à l'administrateur."}, status=403)
            return

        if path == "/api/profiles":
            raw_topic = (qs.get("topic") or [""])[0]
            topic = self._validate_slug_param(raw_topic)
            if not topic or topic == "__INVALID__":
                self._send_json({"error": "Identifiant de sujet invalide."}, status=400)
                return

            removed_files = 0
            for ext in (".yaml", ".yml", ".json"):
                candidate = self.pipeline.config.profiles_dir / f"{topic}{ext}"
                if candidate.is_file():
                    candidate.unlink()
                    removed_files += 1

            for rep in self.pipeline.config.reports_dir.glob(f"{topic}_*"):
                if rep.is_file():
                    rep.unlink()

            db_deleted = self.pipeline.store.delete_topic(topic)
            if removed_files == 0 and db_deleted["deleted_publications"] == 0 and db_deleted["deleted_runs"] == 0:
                self._send_json({"error": f"Sujet '{topic}' introuvable."}, status=404)
                return

            self._send_json(
                {
                    "status": "deleted",
                    "topic": topic,
                    "removed_files": removed_files,
                    **db_deleted,
                },
                status=200,
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
