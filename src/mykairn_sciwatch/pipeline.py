"""
Pipeline d'orchestration principal de myKairn SciWatch :
Collecte multi-sources -> Dédoublonnage -> Classification & Scoring 6D -> Stockage SQLite -> Rapports & Notifications.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from mykairn_sciwatch.classifier.engine import ScientificClassifier6D
from mykairn_sciwatch.config import AppConfig, resolve_profile
from mykairn_sciwatch.connectors.aggregator import MultiSourceAggregator
from mykairn_sciwatch.models import TopicProfile, WatchRunSummary
from mykairn_sciwatch.reporting.exporters import (
    export_to_csv,
    export_to_json,
    export_to_mykairn_knowledge_pack,
)
from mykairn_sciwatch.reporting.markdown_report import generate_markdown_report
from mykairn_sciwatch.reporting.notifier import DigestNotifier
from mykairn_sciwatch.storage.sqlite_store import SciWatchStore


class SciWatchPipeline:
    """Orchestrateur bout-en-bout d'un Audit État de l'Art ou d'une Veille Continue."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or AppConfig()
        self.config.ensure_dirs()
        self.store = SciWatchStore(self.config.db_path)
        self.aggregator = MultiSourceAggregator(self.config)
        self.classifier = ScientificClassifier6D(self.config)
        self.notifier = DigestNotifier(self.config)

    def run_for_profile(
        self,
        profile_or_slug: str | TopicProfile,
        mode: str = "audit",
        lookback_days: Optional[int] = None,
        max_per_source: Optional[int] = None,
        enabled_sources: Optional[List[str]] = None,
        send_notifications: bool = False,
    ) -> WatchRunSummary:
        """Exécute un cycle complet d'audit ou de veille sur un profil donné."""
        if isinstance(profile_or_slug, TopicProfile):
            profile = profile_or_slug
        else:
            profile = resolve_profile(profile_or_slug, self.config.profiles_dir)

        run_id = f"{profile.slug}-{mode}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        days = lookback_days if lookback_days is not None else profile.watch_lookback_days

        try:
            # 1. Collecte multi-sources & dédoublonnage
            merged_records, sources_counts = self.aggregator.collect_for_profile(
                profile=profile,
                mode=mode,
                lookback_days=days if mode == "watch" else None,
                max_per_source=max_per_source,
                enabled_sources=enabled_sources,
            )
            raw_total = sum(sources_counts.values())

            # 2. Classification & Scoring 6D
            classified_pubs = self.classifier.classify_batch(
                records=merged_records,
                profile=profile,
            )

            # 3. Persistance SQLite
            inserted, updated = self.store.upsert_publications(classified_pubs)

            # 4. Récupération du corpus complet du sujet en base pour générer des rapports exhaustifs
            all_topic_pubs = self.store.query_publications(
                topic_slug=profile.slug,
                sort_by="overall_score",
                limit=1000,
            )
            analytics = self.store.get_analytics(topic_slug=profile.slug)

            themes_breakdown: Dict[str, int] = {
                item["slug"]: item["count"] for item in analytics.get("by_theme", [])
            }
            types_breakdown: Dict[str, int] = {
                item["key"]: item["count"] for item in analytics.get("by_publication_type", [])
            }

            finished_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            summary = WatchRunSummary(
                run_id=run_id,
                topic_slug=profile.slug,
                mode=mode,
                started_at=started_at,
                finished_at=finished_at,
                status="completed",
                raw_fetched_count=raw_total,
                deduplicated_count=len(merged_records),
                classified_count=len(classified_pubs),
                new_inserted_count=inserted,
                updated_count=updated,
                sources_breakdown=sources_counts,
                themes_breakdown=themes_breakdown,
                types_breakdown=types_breakdown,
            )

            # 5. Génération automatique des livrables (Markdown, CSV, JSON, myKairn Knowledge Pack)
            md_path = generate_markdown_report(
                profile=profile,
                publications=all_topic_pubs,
                analytics=analytics,
                run_summary=summary,
                reports_dir=self.config.reports_dir,
            )
            export_to_csv(
                publications=all_topic_pubs,
                output_path=self.config.reports_dir / f"{profile.slug}_latest.csv",
            )
            export_to_json(
                publications=all_topic_pubs,
                analytics=analytics,
                output_path=self.config.reports_dir / f"{profile.slug}_latest.json",
            )
            knowledge_pack = export_to_mykairn_knowledge_pack(
                profile=profile,
                publications=all_topic_pubs,
                output_path=self.config.reports_dir / f"{profile.slug}_mykairn_pack.json",
            )

            summary.report_path = str(md_path)
            self.store.record_run(summary)

            # 6. Notifications optionnelles (Email Brevo / Webhook myKairn)
            if send_notifications:
                self.notifier.send_email_digest(profile, summary, all_topic_pubs)
                self.notifier.push_webhook(knowledge_pack)

            return summary

        except Exception as err:
            finished_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            failed_summary = WatchRunSummary(
                run_id=run_id,
                topic_slug=profile.slug,
                mode=mode,
                started_at=started_at,
                finished_at=finished_at,
                status="failed",
                raw_fetched_count=0,
                deduplicated_count=0,
                classified_count=0,
                new_inserted_count=0,
                updated_count=0,
                sources_breakdown={},
                themes_breakdown={},
                types_breakdown={},
                error_message=str(err),
            )
            self.store.record_run(failed_summary)
            raise
