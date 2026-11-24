"""
Gestionnaire de base de données SQLite (WAL) pour les publications classées en 6D et l'historique des exécutions.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mykairn_sciwatch.models import ClassifiedPublication, WatchRunSummary


class SciWatchStore:
    """Stockage relationnel SQLite léger et indexé pour la VM Freebox."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS publications (
                    uid TEXT NOT NULL,
                    topic_slug TEXT NOT NULL,
                    title TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    authors_json TEXT NOT NULL,
                    journal TEXT NOT NULL,
                    publication_date TEXT NOT NULL,
                    publication_year INTEGER NOT NULL,
                    doi TEXT,
                    pmid TEXT,
                    url TEXT NOT NULL,
                    pdf_url TEXT,
                    sources_json TEXT NOT NULL,
                    citation_count INTEGER NOT NULL DEFAULT 0,
                    influential_citation_count INTEGER NOT NULL DEFAULT 0,
                    is_open_access INTEGER NOT NULL DEFAULT 0,
                    mesh_terms_json TEXT NOT NULL,
                    concepts_json TEXT NOT NULL,
                    publication_type TEXT NOT NULL,
                    publication_type_label TEXT NOT NULL,
                    evidence_level TEXT NOT NULL,
                    evidence_tier INTEGER NOT NULL,
                    primary_theme TEXT NOT NULL,
                    primary_theme_label TEXT NOT NULL,
                    secondary_themes_json TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    quality_score REAL NOT NULL,
                    quality_grade TEXT NOT NULL,
                    quality_breakdown_json TEXT NOT NULL,
                    scope_score REAL NOT NULL,
                    scope_level TEXT NOT NULL,
                    athlete_level TEXT NOT NULL,
                    athlete_level_label TEXT NOT NULL,
                    sample_size INTEGER,
                    study_setting TEXT NOT NULL,
                    freshness_score REAL NOT NULL,
                    is_foundational INTEGER NOT NULL DEFAULT 0,
                    overall_score REAL NOT NULL,
                    relevance_score REAL NOT NULL,
                    summary_fr TEXT NOT NULL,
                    practical_takeaway TEXT NOT NULL,
                    key_findings_json TEXT NOT NULL,
                    limitations TEXT NOT NULL,
                    classification_method TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (uid, topic_slug)
                );

                CREATE INDEX IF NOT EXISTS idx_pub_topic_overall
                    ON publications (topic_slug, overall_score DESC);
                CREATE INDEX IF NOT EXISTS idx_pub_topic_theme
                    ON publications (topic_slug, primary_theme);
                CREATE INDEX IF NOT EXISTS idx_pub_topic_type
                    ON publications (topic_slug, publication_type);
                CREATE INDEX IF NOT EXISTS idx_pub_topic_athlete
                    ON publications (topic_slug, athlete_level);
                CREATE INDEX IF NOT EXISTS idx_pub_topic_year
                    ON publications (topic_slug, publication_year DESC);

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    topic_slug TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    raw_fetched_count INTEGER NOT NULL,
                    deduplicated_count INTEGER NOT NULL,
                    classified_count INTEGER NOT NULL,
                    new_inserted_count INTEGER NOT NULL,
                    updated_count INTEGER NOT NULL,
                    sources_breakdown_json TEXT NOT NULL,
                    themes_breakdown_json TEXT NOT NULL,
                    types_breakdown_json TEXT NOT NULL,
                    report_path TEXT,
                    error_message TEXT
                );
                """
            )

    def upsert_publications(self, pubs: List[ClassifiedPublication]) -> Tuple[int, int]:
        """Insère ou met à jour une liste de ClassifiedPublication. Retourne (inserted, updated)."""
        inserted = 0
        updated = 0
        with self._connect() as conn:
            for p in pubs:
                cur = conn.execute(
                    "SELECT uid FROM publications WHERE uid = ? AND topic_slug = ?",
                    (p.uid, p.topic_slug),
                )
                exists = cur.fetchone() is not None

                params = (
                    p.uid,
                    p.topic_slug,
                    p.title,
                    p.abstract,
                    json.dumps(p.authors, ensure_ascii=False),
                    p.journal,
                    p.publication_date,
                    p.publication_year,
                    p.doi,
                    p.pmid,
                    p.url,
                    p.pdf_url,
                    json.dumps(p.sources, ensure_ascii=False),
                    p.citation_count,
                    p.influential_citation_count,
                    1 if p.is_open_access else 0,
                    json.dumps(p.mesh_terms, ensure_ascii=False),
                    json.dumps(p.concepts, ensure_ascii=False),
                    p.publication_type,
                    p.publication_type_label,
                    p.evidence_level,
                    p.evidence_tier,
                    p.primary_theme,
                    p.primary_theme_label,
                    json.dumps(p.secondary_themes, ensure_ascii=False),
                    json.dumps(p.tags, ensure_ascii=False),
                    p.quality_score,
                    p.quality_grade,
                    json.dumps(p.quality_breakdown, ensure_ascii=False),
                    p.scope_score,
                    p.scope_level,
                    p.athlete_level,
                    p.athlete_level_label,
                    p.sample_size,
                    p.study_setting,
                    p.freshness_score,
                    1 if p.is_foundational else 0,
                    p.overall_score,
                    p.relevance_score,
                    p.summary_fr,
                    p.practical_takeaway,
                    json.dumps(p.key_findings, ensure_ascii=False),
                    p.limitations,
                    p.classification_method,
                    p.created_at,
                )

                conn.execute(
                    """
                    INSERT INTO publications (
                        uid, topic_slug, title, abstract, authors_json, journal,
                        publication_date, publication_year, doi, pmid, url, pdf_url,
                        sources_json, citation_count, influential_citation_count, is_open_access,
                        mesh_terms_json, concepts_json, publication_type, publication_type_label,
                        evidence_level, evidence_tier, primary_theme, primary_theme_label,
                        secondary_themes_json, tags_json, quality_score, quality_grade,
                        quality_breakdown_json, scope_score, scope_level, athlete_level,
                        athlete_level_label, sample_size, study_setting, freshness_score,
                        is_foundational, overall_score, relevance_score, summary_fr,
                        practical_takeaway, key_findings_json, limitations,
                        classification_method, created_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?
                    )
                    ON CONFLICT(uid, topic_slug) DO UPDATE SET
                        abstract = excluded.abstract,
                        sources_json = excluded.sources_json,
                        citation_count = MAX(publications.citation_count, excluded.citation_count),
                        influential_citation_count = MAX(publications.influential_citation_count, excluded.influential_citation_count),
                        is_open_access = MAX(publications.is_open_access, excluded.is_open_access),
                        pdf_url = COALESCE(excluded.pdf_url, publications.pdf_url),
                        quality_score = excluded.quality_score,
                        quality_grade = excluded.quality_grade,
                        quality_breakdown_json = excluded.quality_breakdown_json,
                        scope_score = excluded.scope_score,
                        scope_level = excluded.scope_level,
                        athlete_level = excluded.athlete_level,
                        athlete_level_label = excluded.athlete_level_label,
                        freshness_score = excluded.freshness_score,
                        is_foundational = excluded.is_foundational,
                        overall_score = excluded.overall_score,
                        summary_fr = excluded.summary_fr,
                        practical_takeaway = excluded.practical_takeaway,
                        key_findings_json = excluded.key_findings_json,
                        limitations = excluded.limitations,
                        classification_method = excluded.classification_method
                    """,
                    params,
                )
                if exists:
                    updated += 1
                else:
                    inserted += 1
        return inserted, updated

    @staticmethod
    def _row_to_publication(row: sqlite3.Row) -> ClassifiedPublication:
        return ClassifiedPublication(
            uid=row["uid"],
            topic_slug=row["topic_slug"],
            title=row["title"],
            abstract=row["abstract"],
            authors=json.loads(row["authors_json"]),
            journal=row["journal"],
            publication_date=row["publication_date"],
            publication_year=int(row["publication_year"]),
            doi=row["doi"],
            pmid=row["pmid"],
            url=row["url"],
            pdf_url=row["pdf_url"],
            sources=json.loads(row["sources_json"]),
            citation_count=int(row["citation_count"]),
            influential_citation_count=int(row["influential_citation_count"]),
            is_open_access=bool(row["is_open_access"]),
            mesh_terms=json.loads(row["mesh_terms_json"]),
            concepts=json.loads(row["concepts_json"]),
            publication_type=row["publication_type"],
            publication_type_label=row["publication_type_label"],
            evidence_level=row["evidence_level"],
            evidence_tier=int(row["evidence_tier"]),
            primary_theme=row["primary_theme"],
            primary_theme_label=row["primary_theme_label"],
            secondary_themes=json.loads(row["secondary_themes_json"]),
            tags=json.loads(row["tags_json"]),
            quality_score=float(row["quality_score"]),
            quality_grade=row["quality_grade"],
            quality_breakdown=json.loads(row["quality_breakdown_json"]),
            scope_score=float(row["scope_score"]),
            scope_level=row["scope_level"],
            athlete_level=row["athlete_level"],
            athlete_level_label=row["athlete_level_label"],
            sample_size=row["sample_size"],
            study_setting=row["study_setting"],
            freshness_score=float(row["freshness_score"]),
            is_foundational=bool(row["is_foundational"]),
            overall_score=float(row["overall_score"]),
            relevance_score=float(row["relevance_score"]),
            summary_fr=row["summary_fr"],
            practical_takeaway=row["practical_takeaway"],
            key_findings=json.loads(row["key_findings_json"]),
            limitations=row["limitations"],
            classification_method=row["classification_method"],
            created_at=row["created_at"],
        )

    def query_publications(
        self,
        topic_slug: Optional[str] = None,
        theme: Optional[str] = None,
        publication_type: Optional[str] = None,
        athlete_level: Optional[str] = None,
        quality_grade: Optional[str] = None,
        min_quality: float = 0.0,
        min_scope: float = 0.0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        search_query: Optional[str] = None,
        only_foundational: bool = False,
        only_open_access: bool = False,
        sort_by: str = "overall_score",
        limit: int = 200,
        offset: int = 0,
    ) -> List[ClassifiedPublication]:
        """Requête multi-critères filtrée et triée sur la base de publications."""
        clauses: List[str] = ["1=1"]
        params: List[Any] = []

        if topic_slug:
            clauses.append("topic_slug = ?")
            params.append(topic_slug)
        if theme:
            clauses.append("(primary_theme = ? OR secondary_themes_json LIKE ?)")
            params.extend([theme, f'%"{theme}"%'])
        if publication_type:
            clauses.append("publication_type = ?")
            params.append(publication_type)
        if athlete_level:
            clauses.append("athlete_level = ?")
            params.append(athlete_level)
        if quality_grade:
            clauses.append("quality_grade = ?")
            params.append(quality_grade)
        if min_quality > 0:
            clauses.append("quality_score >= ?")
            params.append(min_quality)
        if min_scope > 0:
            clauses.append("scope_score >= ?")
            params.append(min_scope)
        if year_from:
            clauses.append("publication_year >= ?")
            params.append(year_from)
        if year_to:
            clauses.append("publication_year <= ?")
            params.append(year_to)
        if only_foundational:
            clauses.append("is_foundational = 1")
        if only_open_access:
            clauses.append("is_open_access = 1")
        if search_query and search_query.strip():
            like_q = f"%{search_query.strip()}%"
            clauses.append(
                "(title LIKE ? OR abstract LIKE ? OR summary_fr LIKE ? OR practical_takeaway LIKE ? OR journal LIKE ?)"
            )
            params.extend([like_q, like_q, like_q, like_q, like_q])

        allowed_sorts = {
            "overall_score": "overall_score DESC, quality_score DESC",
            "quality_score": "quality_score DESC, overall_score DESC",
            "scope_score": "scope_score DESC, overall_score DESC",
            "publication_date": "publication_date DESC, overall_score DESC",
            "citation_count": "citation_count DESC, overall_score DESC",
            "evidence_tier": "evidence_tier ASC, overall_score DESC",
        }
        order_clause = allowed_sorts.get(sort_by, allowed_sorts["overall_score"])

        sql = (
            f"SELECT * FROM publications WHERE {' AND '.join(clauses)} "
            f"ORDER BY {order_clause} LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_publication(r) for r in rows]

    def get_analytics(self, topic_slug: Optional[str] = None) -> Dict[str, Any]:
        """Retourne les statistiques agrégées 6D pour le Dashboard Web et les rapports d'audit."""
        pubs = self.query_publications(topic_slug=topic_slug, limit=2000)
        total = len(pubs)
        if total == 0:
            return {
                "total_publications": 0,
                "avg_overall_score": 0.0,
                "avg_quality_score": 0.0,
                "avg_scope_score": 0.0,
                "open_access_count": 0,
                "foundational_count": 0,
                "tier_1_2_count": 0,
                "by_theme": [],
                "by_publication_type": [],
                "by_athlete_level": [],
                "by_quality_grade": {},
                "by_year": [],
                "by_source": {},
                "top_journals": [],
            }

        avg_overall = round(sum(p.overall_score for p in pubs) / total, 1)
        avg_quality = round(sum(p.quality_score for p in pubs) / total, 1)
        avg_scope = round(sum(p.scope_score for p in pubs) / total, 1)
        oa_count = sum(1 for p in pubs if p.is_open_access)
        foundational_count = sum(1 for p in pubs if p.is_foundational)
        tier_1_2 = sum(1 for p in pubs if p.evidence_tier <= 2)

        themes_map: Dict[str, Dict[str, Any]] = {}
        types_map: Dict[str, Dict[str, Any]] = {}
        athlete_map: Dict[str, Dict[str, Any]] = {}
        grade_map: Dict[str, int] = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        year_map: Dict[int, int] = {}
        source_map: Dict[str, int] = {}
        journal_map: Dict[str, int] = {}

        for p in pubs:
            # Thèmes
            if p.primary_theme not in themes_map:
                themes_map[p.primary_theme] = {
                    "slug": p.primary_theme,
                    "label": p.primary_theme_label,
                    "count": 0,
                    "avg_score_sum": 0.0,
                }
            themes_map[p.primary_theme]["count"] += 1
            themes_map[p.primary_theme]["avg_score_sum"] += p.overall_score

            # Types EBM
            if p.publication_type not in types_map:
                types_map[p.publication_type] = {
                    "key": p.publication_type,
                    "label": p.publication_type_label,
                    "evidence_level": p.evidence_level,
                    "tier": p.evidence_tier,
                    "count": 0,
                }
            types_map[p.publication_type]["count"] += 1

            # Niveau d'athlète / Portée
            if p.athlete_level not in athlete_map:
                athlete_map[p.athlete_level] = {
                    "key": p.athlete_level,
                    "label": p.athlete_level_label,
                    "count": 0,
                }
            athlete_map[p.athlete_level]["count"] += 1

            # Grades qualité
            grade_map[p.quality_grade] = grade_map.get(p.quality_grade, 0) + 1

            # Années
            if p.publication_year:
                year_map[p.publication_year] = year_map.get(p.publication_year, 0) + 1

            # Sources
            for s in p.sources:
                source_map[s] = source_map.get(s, 0) + 1

            # Journaux
            if p.journal:
                journal_map[p.journal] = journal_map.get(p.journal, 0) + 1

        by_theme = [
            {
                "slug": v["slug"],
                "label": v["label"],
                "count": v["count"],
                "avg_score": round(v["avg_score_sum"] / v["count"], 1),
            }
            for v in sorted(themes_map.values(), key=lambda x: x["count"], reverse=True)
        ]

        by_type = sorted(types_map.values(), key=lambda x: (x["tier"], -x["count"]))
        by_athlete = sorted(athlete_map.values(), key=lambda x: x["count"], reverse=True)
        by_year = [
            {"year": y, "count": c}
            for y, c in sorted(year_map.items(), key=lambda x: x[0])
        ]
        top_journals = [
            {"journal": j, "count": c}
            for j, c in sorted(journal_map.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return {
            "total_publications": total,
            "avg_overall_score": avg_overall,
            "avg_quality_score": avg_quality,
            "avg_scope_score": avg_scope,
            "open_access_count": oa_count,
            "foundational_count": foundational_count,
            "tier_1_2_count": tier_1_2,
            "by_theme": by_theme,
            "by_publication_type": by_type,
            "by_athlete_level": by_athlete,
            "by_quality_grade": grade_map,
            "by_year": by_year,
            "by_source": source_map,
            "top_journals": top_journals,
        }

    def record_run(self, summary: WatchRunSummary) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, topic_slug, mode, started_at, finished_at, status,
                    raw_fetched_count, deduplicated_count, classified_count,
                    new_inserted_count, updated_count, sources_breakdown_json,
                    themes_breakdown_json, types_breakdown_json, report_path, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.run_id,
                    summary.topic_slug,
                    summary.mode,
                    summary.started_at,
                    summary.finished_at,
                    summary.status,
                    summary.raw_fetched_count,
                    summary.deduplicated_count,
                    summary.classified_count,
                    summary.new_inserted_count,
                    summary.updated_count,
                    json.dumps(summary.sources_breakdown, ensure_ascii=False),
                    json.dumps(summary.themes_breakdown, ensure_ascii=False),
                    json.dumps(summary.types_breakdown, ensure_ascii=False),
                    summary.report_path,
                    summary.error_message,
                ),
            )

    def list_runs(self, topic_slug: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if topic_slug:
                rows = conn.execute(
                    "SELECT * FROM runs WHERE topic_slug = ? ORDER BY started_at DESC LIMIT ?",
                    (topic_slug, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()

        results: List[Dict[str, Any]] = []
        for r in rows:
            results.append(
                {
                    "run_id": r["run_id"],
                    "topic_slug": r["topic_slug"],
                    "mode": r["mode"],
                    "started_at": r["started_at"],
                    "finished_at": r["finished_at"],
                    "status": r["status"],
                    "raw_fetched_count": r["raw_fetched_count"],
                    "deduplicated_count": r["deduplicated_count"],
                    "classified_count": r["classified_count"],
                    "new_inserted_count": r["new_inserted_count"],
                    "updated_count": r["updated_count"],
                    "sources_breakdown": json.loads(r["sources_breakdown_json"]),
                    "themes_breakdown": json.loads(r["themes_breakdown_json"]),
                    "types_breakdown": json.loads(r["types_breakdown_json"]),
                    "report_path": r["report_path"],
                    "error_message": r["error_message"],
                }
            )
        return results
