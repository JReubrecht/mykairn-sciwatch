"""
Service de notification Digest Email (via Brevo API v3) et Webhook vers myKairn Platform.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List

from mykairn_sciwatch.config import AppConfig
from mykairn_sciwatch.models import ClassifiedPublication, TopicProfile, WatchRunSummary


class DigestNotifier:
    """Envoie les alertes de veille scientifique par Email (Brevo) et/ou Webhook HTTP."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def send_email_digest(
        self,
        profile: TopicProfile,
        run_summary: WatchRunSummary,
        top_publications: List[ClassifiedPublication],
    ) -> bool:
        """Envoie un digest HTML par email via l'API REST Brevo v3 si BREVO_API_KEY est configurée."""
        if not self.config.brevo_api_key or not self.config.digest_to:
            return False

        items_html = []
        for p in top_publications[:8]:
            items_html.append(
                f"<li style='margin-bottom:14px;'>"
                f"<strong>[{p.overall_score}/100 | Grade {p.quality_grade} | {p.publication_type_label}]</strong> "
                f"<a href='{p.url}'>{p.title}</a> <em>({p.journal}, {p.publication_year})</em><br/>"
                f"<span style='color:#0f766e;'>Thème : {p.primary_theme_label} • Cible : {p.athlete_level_label}</span><br/>"
                f"<span>{p.summary_fr}</span><br/>"
                f"<strong>💡 Takeaway :</strong> {p.practical_takeaway}"
                f"</li>"
            )

        html_content = (
            f"<h2>🔬 myKairn SciWatch — {profile.name}</h2>"
            f"<p>Mode : <strong>{run_summary.mode.upper()}</strong> | "
            f"Publications analysées : <strong>{run_summary.classified_count}</strong> "
            f"(Nouvelles : {run_summary.new_inserted_count})</p>"
            f"<h3>Top Publications & Takeaways Coaching :</h3>"
            f"<ol>{''.join(items_html)}</ol>"
        )

        payload = {
            "sender": {
                "name": self.config.brevo_from_name,
                "email": self.config.brevo_from_email,
            },
            "to": [{"email": self.config.digest_to}],
            "subject": f"[myKairn SciWatch] {profile.name} ({run_summary.classified_count} publications)",
            "htmlContent": html_content,
        }

        try:
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "api-key": self.config.brevo_api_key,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False

    def push_webhook(self, knowledge_pack: Dict[str, Any]) -> bool:
        """Pousse le Knowledge Pack JSON vers MYKAIRN_WEBHOOK_URL si configuré."""
        if not self.config.mykairn_webhook_url:
            return False
        headers = {"Content-Type": "application/json"}
        if self.config.mykairn_webhook_secret:
            headers["X-SciWatch-Secret"] = self.config.mykairn_webhook_secret
        try:
            req = urllib.request.Request(
                self.config.mykairn_webhook_url,
                data=json.dumps(knowledge_pack).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False
