"""
Exporteurs multi-formats : CSV, JSON complet et Knowledge Pack JSON pour myKairn Platform.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mykairn_sciwatch.models import ClassifiedPublication, TopicProfile


def export_to_csv(
    publications: List[ClassifiedPublication],
    output_path: Optional[Path] = None,
) -> str:
    """Exporte une liste de publications classées en CSV (UTF-8). Retourne la chaîne CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "uid",
            "topic_slug",
            "overall_score",
            "quality_score",
            "quality_grade",
            "scope_score",
            "scope_level",
            "freshness_score",
            "is_foundational",
            "publication_type",
            "publication_type_label",
            "evidence_level",
            "evidence_tier",
            "primary_theme",
            "primary_theme_label",
            "athlete_level",
            "athlete_level_label",
            "sample_size",
            "study_setting",
            "publication_date",
            "publication_year",
            "title",
            "journal",
            "authors",
            "citation_count",
            "is_open_access",
            "doi",
            "pmid",
            "url",
            "sources",
            "summary_fr",
            "practical_takeaway",
            "limitations",
        ]
    )

    for p in publications:
        writer.writerow(
            [
                p.uid,
                p.topic_slug,
                p.overall_score,
                p.quality_score,
                p.quality_grade,
                p.scope_score,
                p.scope_level,
                p.freshness_score,
                "oui" if p.is_foundational else "non",
                p.publication_type,
                p.publication_type_label,
                p.evidence_level,
                p.evidence_tier,
                p.primary_theme,
                p.primary_theme_label,
                p.athlete_level,
                p.athlete_level_label,
                p.sample_size or "",
                p.study_setting,
                p.publication_date,
                p.publication_year,
                p.title,
                p.journal,
                "; ".join(p.authors),
                p.citation_count,
                "oui" if p.is_open_access else "non",
                p.doi or "",
                p.pmid or "",
                p.url,
                ", ".join(p.sources),
                p.summary_fr,
                p.practical_takeaway,
                p.limitations,
            ]
        )

    csv_text = buffer.getvalue()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(csv_text, encoding="utf-8")
    return csv_text


def export_to_json(
    publications: List[ClassifiedPublication],
    analytics: Optional[Dict[str, Any]] = None,
    output_path: Optional[Path] = None,
) -> str:
    """Exporte les publications classées et les métriques analytiques au format JSON."""
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(publications),
        "analytics": analytics or {},
        "publications": [p.to_dict() for p in publications],
    }
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_text, encoding="utf-8")
    return json_text


def export_to_mykairn_knowledge_pack(
    profile: TopicProfile,
    publications: List[ClassifiedPublication],
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Génère un Knowledge Pack JSON structuré prêt à alimenter l'assistant scientifique
    et les modules de coaching de myKairn Platform.
    """
    pack: Dict[str, Any] = {
        "schema_version": "mykairn-sciwatch-pack/v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "topic": {
            "slug": profile.slug,
            "name": profile.name,
            "domain": profile.domain,
        },
        "evidence_cards": [
            {
                "id": p.uid,
                "title": p.title,
                "year": p.publication_year,
                "journal": p.journal,
                "doi": p.doi,
                "pmid": p.pmid,
                "url": p.url,
                "theme": p.primary_theme,
                "themeLabel": p.primary_theme_label,
                "studyType": p.publication_type_label,
                "evidenceLevel": p.evidence_level,
                "evidenceTier": p.evidence_tier,
                "qualityScore": p.quality_score,
                "qualityGrade": p.quality_grade,
                "scopeScore": p.scope_score,
                "athleteLevel": p.athlete_level,
                "athleteLevelLabel": p.athlete_level_label,
                "overallScore": p.overall_score,
                "isFoundational": p.is_foundational,
                "summaryFr": p.summary_fr,
                "coachingTakeaway": p.practical_takeaway,
                "keyFindings": p.key_findings,
                "limitations": p.limitations,
                "tags": p.tags,
            }
            for p in publications
        ],
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return pack
