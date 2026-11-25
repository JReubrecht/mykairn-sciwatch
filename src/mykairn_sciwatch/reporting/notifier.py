"""
Service de notification Digest Email (via Brevo API v3) et Webhook vers myKairn Platform.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
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
                f"<li style='margin-bottom:16px;padding:12px;background:#FFFFFF;border:1px solid #E2E8F0;border-left:4px solid #1E4D6B;border-radius:8px;'>"
                f"<strong style='color:#0F172A;font-family:monospace;'>[SCORE {p.overall_score}/100 | GRADE {p.quality_grade} | {p.publication_type_label}]</strong> "
                f"<a href='{p.url}' style='color:#FF5A36;font-weight:700;text-decoration:none;'>{p.title}</a> "
                f"<em style='color:#64748B;'>({p.journal}, {p.publication_year})</em><br/>"
                f"<span style='color:#1E4D6B;font-weight:600;font-size:13px;'>Thème : {p.primary_theme_label} • Cible : {p.athlete_level_label}</span><br/>"
                f"<span style='color:#0F172A;font-size:14px;'>{p.summary_fr}</span><br/>"
                f"<div style='margin-top:6px;padding:8px 10px;background:#ECFDF5;border-left:3px solid #14C38E;color:#047857;font-size:13.5px;'>"
                f"<strong>💡 Takeaway myKairn :</strong> {p.practical_takeaway}</div>"
                f"</li>"
            )

        html_content = (
            f"<div style='font-family:sans-serif;background:#F8FAFC;color:#0F172A;padding:24px;'>"
            f"<div style='background:linear-gradient(135deg,#0F172A 0%,#1E4D6B 100%);color:#FFFFFF;padding:18px 22px;border-radius:12px;margin-bottom:18px;'>"
            f"<div style='font-family:monospace;font-size:11px;letter-spacing:0.14em;color:#FF5A36;font-weight:700;'>MYKAIRN SCIWATCH · ENDURANCE LAB</div>"
            f"<h2 style='margin:6px 0 4px 0;color:#FFFFFF;'>{profile.name}</h2>"
            f"<p style='margin:0;color:#CBD5E1;font-size:13px;'>Mode : <strong>{run_summary.mode.upper()}</strong> | "
            f"Publications classées : <strong>{run_summary.classified_count}</strong> "
            f"(Nouvelles : {run_summary.new_inserted_count})</p></div>"
            f"<h3 style='color:#0F172A;'>Top Publications &amp; Takeaways Coaching :</h3>"
            f"<ol style='padding-left:18px;'>{''.join(items_html)}</ol></div>"
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
        target_url = (self.config.mykairn_webhook_url or "").strip()
        if not target_url:
            return False
        parsed = urllib.parse.urlparse(target_url)
        if parsed.netloc.lower() == "mykairn.fr":
            target_url = urllib.parse.urlunparse(parsed._replace(scheme="https", netloc="www.mykairn.fr"))

        payload_bytes = json.dumps(knowledge_pack).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.mykairn_webhook_secret:
            headers["X-SciWatch-Secret"] = self.config.mykairn_webhook_secret

        for _ in range(3):
            try:
                req = urllib.request.Request(
                    target_url,
                    data=payload_bytes,
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return 200 <= resp.status < 300
            except urllib.error.HTTPError as err:
                if err.code in (301, 302, 307, 308):
                    location = err.headers.get("Location")
                    if location:
                        target_url = urllib.parse.urljoin(target_url, location)
                        continue
                return False
            except Exception:
                return False
        return False
