"""
Gestion de la configuration environnementale et chargement des profils de veille YAML/JSON.
Inclut un support PyYAML avec repli JSON/YAML léger afin de fonctionner sur tout système.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from mykairn_sciwatch.models import ThemeConfig, TopicProfile

try:
    import yaml  # type: ignore

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_dotenv_file(env_path: Optional[Path] = None) -> None:
    """Charge un fichier .env simple sans dépendance externe."""
    candidates = [env_path] if env_path else [Path(".env"), Path(".env.local")]
    for candidate in candidates:
        if candidate and candidate.is_file():
            for raw_line in candidate.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val


class AppConfig:
    """Configuration globale de myKairn SciWatch."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        load_dotenv_file()
        self.base_dir = base_dir or Path.cwd()
        self.db_path = Path(os.environ.get("SCIWATCH_DB_PATH", str(self.base_dir / "data" / "sciwatch.db")))
        self.profiles_dir = Path(os.environ.get("SCIWATCH_PROFILES_DIR", str(self.base_dir / "profiles")))
        self.reports_dir = Path(os.environ.get("SCIWATCH_REPORTS_DIR", str(self.base_dir / "reports")))
        self.host = os.environ.get("SCIWATCH_HOST", "0.0.0.0")
        self.port = int(os.environ.get("SCIWATCH_PORT", "8095"))

        # Sécurité API & Tunnel Freebox <-> mykairn.fr
        self.api_secret = os.environ.get("SCIWATCH_API_SECRET", "").strip()
        self.allow_lan_direct = os.environ.get("SCIWATCH_ALLOW_LAN_DIRECT", "true").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        self.trusted_lan_prefixes = tuple(
            p.strip()
            for p in os.environ.get("SCIWATCH_TRUSTED_LAN_PREFIXES", "192.168.,10.").split(",")
            if p.strip()
        )
        self.cors_allowed_origin = os.environ.get("SCIWATCH_CORS_ORIGIN", "https://mykairn.fr").strip()

        # APIs scientifiques
        self.ncbi_api_key = os.environ.get("NCBI_API_KEY", "").strip()
        self.ncbi_email = os.environ.get("NCBI_EMAIL", "contact@mykairn.fr").strip()
        self.openalex_email = os.environ.get("OPENALEX_EMAIL", "contact@mykairn.fr").strip()
        self.s2_api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()

        # Enrichissement LLM optionnel
        self.llm_provider = os.environ.get("SCIWATCH_LLM_PROVIDER", "gemini").strip().lower()
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self.anthropic_model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip()

        # Notifications Email / Webhook
        self.brevo_api_key = os.environ.get("BREVO_API_KEY", "").strip()
        self.brevo_from_email = os.environ.get("BREVO_FROM_EMAIL", "contact@mykairn.fr").strip()
        self.brevo_from_name = os.environ.get("BREVO_FROM_NAME", "myKairn SciWatch").strip()
        self.digest_to = os.environ.get("SCIWATCH_DIGEST_TO", "reubrechtj@free.fr").strip()
        self.mykairn_webhook_url = os.environ.get("MYKAIRN_WEBHOOK_URL", "").strip()
        self.mykairn_webhook_secret = os.environ.get("MYKAIRN_WEBHOOK_SECRET", "").strip()

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


def parse_profile_dict(data: Dict[str, Any]) -> TopicProfile:
    """Convertit un dictionnaire YAML/JSON en TopicProfile validé."""
    themes: List[ThemeConfig] = []
    for raw_t in data.get("themes", []):
        themes.append(
            ThemeConfig(
                slug=str(raw_t["slug"]),
                name=str(raw_t["name"]),
                description=str(raw_t.get("description", "")),
                keywords=[str(k).lower() for k in raw_t.get("keywords", [])],
                weight=float(raw_t.get("weight", 1.0)),
            )
        )

    raw_end_year = data.get("audit_end_year")
    audit_end_year = int(raw_end_year) if raw_end_year not in (None, "", 0) else None
    raw_sources = data.get("enabled_sources")
    enabled_sources = (
        [str(s).strip() for s in raw_sources if str(s).strip()]
        if isinstance(raw_sources, list) and raw_sources
        else ["pubmed", "openalex", "semantic_scholar", "crossref"]
    )
    raw_blocks = data.get("query_blocks")
    query_blocks = [dict(b) for b in raw_blocks if isinstance(b, dict)] if isinstance(raw_blocks, list) else []

    return TopicProfile(
        slug=str(data["slug"]),
        name=str(data["name"]),
        description=str(data.get("description", "")),
        domain=str(data.get("domain", "sports_science")),
        language=str(data.get("language", "fr")),
        queries=[str(q) for q in data.get("queries", [])],
        boolean_query=str(data.get("boolean_query", "") or ""),
        query_blocks=query_blocks,
        inclusion_keywords=[str(k).lower() for k in data.get("inclusion_keywords", [])],
        exclusion_keywords=[str(k).lower() for k in data.get("exclusion_keywords", [])],
        high_impact_journals=[str(j) for j in data.get("high_impact_journals", [])],
        rss_feeds=list(data.get("rss_feeds", [])),
        themes=themes,
        target_scopes={
            str(k): [str(v).lower() for v in vals]
            for k, vals in data.get("target_scopes", {}).items()
        },
        audit_start_year=int(data.get("audit_start_year", 2015)),
        audit_end_year=audit_end_year,
        watch_lookback_days=int(data.get("watch_lookback_days", 30)),
        max_results_per_source=int(data.get("max_results_per_source", 40)),
        min_relevance_score=float(data.get("min_relevance_score", 15.0)),
        enabled_sources=enabled_sources,
        allowed_publication_types=[
            str(pt).strip()
            for pt in (data.get("allowed_publication_types") or [])
            if str(pt).strip()
        ],
        humans_only=bool(data.get("humans_only", False)),
        open_access_only=bool(data.get("open_access_only", False)),
        exclude_preprints=bool(data.get("exclude_preprints", False)),
        strict_boolean=bool(data.get("strict_boolean", True)),
        search_languages=[
            str(l).strip().lower()
            for l in (data.get("search_languages") or [])
            if str(l).strip()
        ],
        min_citations=int(data.get("min_citations", 0) or 0),
        min_sample_size=int(data.get("min_sample_size", 0) or 0),
        min_quality_score=float(data.get("min_quality_score", 0.0) or 0.0),
        llm_system_prompt=str(data.get("llm_system_prompt", "")),
    )


def load_topic_profile(path: Path) -> TopicProfile:
    """Charge un profil de sujet depuis un fichier YAML ou JSON."""
    if not path.is_file():
        raise FileNotFoundError(f"Profil introuvable : {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    elif HAS_YAML:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Format de profil invalide dans {path}")
    return parse_profile_dict(data)


def save_topic_profile(profile: TopicProfile, profiles_dir: Path) -> Path:
    """Sauvegarde un TopicProfile au format YAML (ou JSON si PyYAML absent)."""
    profiles_dir.mkdir(parents=True, exist_ok=True)
    data = profile.to_dict()
    if HAS_YAML:
        out_path = profiles_dir / f"{profile.slug}.yaml"
        out_path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
    else:
        out_path = profiles_dir / f"{profile.slug}.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def list_topic_profiles(profiles_dir: Path) -> List[TopicProfile]:
    """Liste tous les profils de veille disponibles dans le dossier profiles/."""
    if not profiles_dir.is_dir():
        return []
    profiles: List[TopicProfile] = []
    seen_slugs = set()
    for ext in ("*.yaml", "*.yml", "*.json"):
        for file_path in sorted(profiles_dir.glob(ext)):
            try:
                prof = load_topic_profile(file_path)
                if prof.slug not in seen_slugs:
                    profiles.append(prof)
                    seen_slugs.add(prof.slug)
            except Exception:
                continue
    return profiles


def resolve_profile(slug_or_path: str, profiles_dir: Path) -> TopicProfile:
    """Résout un profil par son slug (ex: 'trail_running_coaching') ou son chemin fichier."""
    direct = Path(slug_or_path)
    if direct.is_file():
        return load_topic_profile(direct)
    for ext in (".yaml", ".yml", ".json"):
        candidate = profiles_dir / f"{slug_or_path}{ext}"
        if candidate.is_file():
            return load_topic_profile(candidate)
    raise FileNotFoundError(
        f"Impossible de trouver le profil '{slug_or_path}' dans {profiles_dir}"
    )
