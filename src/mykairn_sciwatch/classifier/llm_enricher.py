"""
Enrichisseur LLM optionnel (Gemini Flash, OpenAI GPT-4o-mini, Anthropic Claude Haiku).
Fonctionne uniquement via la bibliothèque standard (urllib.request) sans SDK lourd,
et bascule automatiquement sur le moteur déterministe EBM si aucune clé API n'est configurée.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, Optional

from mykairn_sciwatch.config import AppConfig
from mykairn_sciwatch.models import ClassifiedPublication, TopicProfile


class LLMEnricher:
    """Enrichit les synthèses en français (summary_fr, practical_takeaway, key_findings, limitations) via API LLM."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    @property
    def is_enabled(self) -> bool:
        provider = self.config.llm_provider
        if provider == "gemini" and self.config.gemini_api_key:
            return True
        if provider == "openai" and self.config.openai_api_key:
            return True
        if provider == "anthropic" and self.config.anthropic_api_key:
            return True
        return False

    def enrich_publication(
        self, pub: ClassifiedPublication, profile: TopicProfile
    ) -> ClassifiedPublication:
        """Enrichit une publication classée via l'API LLM configurée (avec repli silencieux en cas d'erreur)."""
        if not self.is_enabled or not pub.abstract:
            return pub

        prompt = self._build_prompt(pub, profile)
        try:
            response_json = self._call_provider(prompt, profile.llm_system_prompt)
            if response_json:
                if response_json.get("summary_fr"):
                    pub.summary_fr = str(response_json["summary_fr"]).strip()
                if response_json.get("practical_takeaway"):
                    pub.practical_takeaway = str(response_json["practical_takeaway"]).strip()
                if isinstance(response_json.get("key_findings"), list) and response_json["key_findings"]:
                    pub.key_findings = [str(x).strip() for x in response_json["key_findings"][:4]]
                if response_json.get("limitations"):
                    pub.limitations = str(response_json["limitations"]).strip()
                pub.classification_method = f"hybrid_llm ({self.config.llm_provider})"
        except Exception:
            # Conserver la synthèse déterministe EBM en cas de quota ou d'erreur réseau
            pass
        return pub

    @staticmethod
    def _build_prompt(pub: ClassifiedPublication, profile: TopicProfile) -> str:
        return (
            f"Sujet d'audit : {profile.name}\n"
            f"Titre : {pub.title}\n"
            f"Journal ({pub.publication_year}) : {pub.journal}\n"
            f"Type d'étude : {pub.publication_type_label} ({pub.evidence_level})\n"
            f"Thème : {pub.primary_theme_label}\n"
            f"Public cible détecté : {pub.athlete_level_label}\n"
            f"Résumé original :\n{pub.abstract}\n\n"
            "Réponds UNIQUEMENT avec un objet JSON valide contenant les clés :\n"
            '- "summary_fr": résumé scientifique synthétique en français (2-3 phrases)\n'
            '- "practical_takeaway": recommandation concrète et actionnable sur le terrain/coaching (1-2 phrases)\n'
            '- "key_findings": liste de 2 ou 3 résultats clés chiffrés en français\n'
            '- "limitations": principale limite méthodologique ou précaution d\'interprétation en français (1 phrase)'
        )

    def _call_provider(self, user_prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        provider = self.config.llm_provider
        if provider == "gemini" and self.config.gemini_api_key:
            return self._call_gemini(user_prompt, system_prompt)
        if provider == "openai" and self.config.openai_api_key:
            return self._call_openai(user_prompt, system_prompt)
        if provider == "anthropic" and self.config.anthropic_api_key:
            return self._call_anthropic(user_prompt, system_prompt)
        return None

    def _call_gemini(self, user_prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.config.gemini_model}:generateContent?key={self.config.gemini_api_key}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt or "Tu es un analyste scientifique."}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return self._extract_json(text)

    def _call_openai(self, user_prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.config.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt or "Tu es un analyste scientifique."},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.openai_api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return self._extract_json(text)

    def _call_anthropic(self, user_prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self.config.anthropic_model,
            "max_tokens": 700,
            "system": system_prompt or "Tu es un analyste scientifique.",
            "messages": [{"role": "user", "content": user_prompt}],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.config.anthropic_api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data.get("content", [])
        text = content[0].get("text", "") if content else ""
        return self._extract_json(text)

    @staticmethod
    def _extract_json(raw_text: str) -> Optional[Dict[str, Any]]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        return None
