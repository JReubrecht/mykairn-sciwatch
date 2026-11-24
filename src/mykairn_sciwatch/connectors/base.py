"""
Utilitaires HTTP, normalisation DOI/titres et classe de base des connecteurs scientifiques.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


USER_AGENT = "myKairn-SciWatch/1.0 (https://mykairn.fr; mailto:contact@mykairn.fr)"


def normalize_doi(raw_doi: Optional[str]) -> Optional[str]:
    """Normalise un DOI sous la forme '10.xxxx/...' en minuscules."""
    if not raw_doi:
        return None
    cleaned = raw_doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    if cleaned.startswith("10.") and "/" in cleaned:
        return cleaned
    return None


def normalize_title_key(title: str) -> str:
    """Génère une empreinte alphanumérique normalisée d'un titre pour le dédoublonnage."""
    cleaned = html.unescape(title or "").lower()
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "", cleaned)
    return cleaned[:160]


def clean_html_text(text: str) -> str:
    """Nettoie les balises XML/HTML et les espaces multiples d'un titre ou résumé."""
    if not text:
        return ""
    unescaped = html.unescape(text)
    no_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", no_tags).strip()


def http_get_text(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 20,
    retries: int = 2,
) -> str:
    """Exécute une requête HTTP GET robuste avec User-Agent académique et gestion du rate-limit."""
    req_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        req_headers.update(headers)

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=req_headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except Exception as err:
            last_err = err
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
    if last_err:
        raise last_err
    return ""


def http_get_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 20,
    retries: int = 2,
) -> Dict[str, Any]:
    """Exécute une requête HTTP GET et parse le JSON retourné."""
    json_headers = {"Accept": "application/json"}
    if headers:
        json_headers.update(headers)
    raw = http_get_text(url, headers=json_headers, timeout=timeout, retries=retries)
    return json.loads(raw) if raw else {}
