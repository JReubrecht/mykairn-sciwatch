"""
Générateur de rapports d'Audit État de l'Art et de Digest de Veille Scientifique au format Markdown.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from mykairn_sciwatch.models import ClassifiedPublication, TopicProfile, WatchRunSummary


def generate_markdown_report(
    profile: TopicProfile,
    publications: List[ClassifiedPublication],
    analytics: Dict[str, Any],
    run_summary: WatchRunSummary,
    reports_dir: Path,
) -> Path:
    """Génère un rapport Markdown complet structuré par pyramide EBM, thèmes, niveaux d'athlète et takeaways."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mode_label = "AUDIT ÉTAT DE L'ART" if run_summary.mode == "audit" else "DIGEST DE VEILLE CONTINUE"

    lines: List[str] = [
        f"# 🔬 {mode_label} — {profile.name}",
        "",
        f"> **Sujet audité** : `{profile.slug}` | **Mode** : `{run_summary.mode.upper()}` | "
        f"**Généré le** : `{date_tag}` | **Publications retenues & scorées** : **{len(publications)}**",
        "",
        f"_{profile.description.strip()}_",
        "",
        "---",
        "",
        "## 1. Synthèse Exécutive & Indicateurs Clés (Grille 6D)",
        "",
        "| Indicateur | Valeur | Interprétation |",
        "| :--- | :---: | :--- |",
        f"| **Corpus Analysé (Dédoublonné)** | **{analytics.get('total_publications', len(publications))}** | PubMed, OpenAlex, Semantic Scholar, Crossref/RSS |",
        f"| **Score Global Moyen (/100)** | **{analytics.get('avg_overall_score', 0.0)} / 100** | Pondération Qualité (42%), Portée (35%), Fraîcheur/Impact (23%) |",
        f"| **Score Qualité Méthodologique Moyen** | **{analytics.get('avg_quality_score', 0.0)} / 100** | Design EBM, taille d'échantillon, journal, citations, rigueur |",
        f"| **Score Portée & Applicabilité Terrain** | **{analytics.get('avg_scope_score', 0.0)} / 100** | Validité écologique, métriques coaching & couverture tous niveaux |",
        f"| **Haut Niveau de Preuve (Niveaux 1 & 2 EBM)** | **{analytics.get('tier_1_2_count', 0)}** | Méta-analyses, Revues systématiques, RCT & Consensus |",
        f"| **Articles Fondateurs de Référence** | **{analytics.get('foundational_count', 0)}** | Publications à fort impact bibliométrique |",
        f"| **Accès Libre (Open Access / PDF)** | **{analytics.get('open_access_count', 0)}** | Textes intégraux librement accessibles |",
        "",
        "### Pyramide des Niveaux de Preuve (Dimension 1 — Type de Publication)",
        "",
        "| Niveau EBM | Type de Publication | Nombre d'études |",
        "| :--- | :--- | :---: |",
    ]

    for pt in analytics.get("by_publication_type", []):
        lines.append(f"| **{pt['evidence_level']}** | {pt['label']} | **{pt['count']}** |")

    lines.extend(
        [
            "",
            "### Répartition par Thème Scientifique (Dimension 2)",
            "",
            "| Thème | Publications | Score Global Moyen |",
            "| :--- | :---: | :---: |",
        ]
    )
    for th in analytics.get("by_theme", []):
        lines.append(f"| **{th['label']}** | {th['count']} | **{th['avg_score']} / 100** |")

    lines.extend(
        [
            "",
            "### Couverture par Niveau d'Athlète & Portée (Dimension 4)",
            "",
            "| Public / Niveau d'Athlète Cible | Publications |",
            "| :--- | :---: |",
        ]
    )
    for al in analytics.get("by_athlete_level", []):
        lines.append(f"| **{al['label']}** | **{al['count']}** |")

    # Section 2 : Top 10 Publications Majeures (Toutes thématiques confondues)
    lines.extend(
        [
            "",
            "---",
            "",
            "## 2. Top 10 des Publications Incontournables (Classement Global 6D)",
            "",
        ]
    )

    top_pubs = sorted(publications, key=lambda p: p.overall_score, reverse=True)[:10]
    for idx, pub in enumerate(top_pubs, start=1):
        lines.extend(_format_publication_block(idx, pub))

    # Section 3 : Analyse Détaillée par Thème
    lines.extend(
        [
            "---",
            "",
            "## 3. Classement Détaillé & Recommandations Terrain par Thème",
            "",
        ]
    )

    by_theme_pubs: Dict[str, List[ClassifiedPublication]] = {}
    for pub in publications:
        by_theme_pubs.setdefault(pub.primary_theme, []).append(pub)

    for theme_cfg in profile.themes:
        t_pubs = by_theme_pubs.get(theme_cfg.slug, [])
        if not t_pubs:
            continue
        t_pubs.sort(key=lambda p: p.overall_score, reverse=True)
        lines.extend(
            [
                f"### 📌 {theme_cfg.name} ({len(t_pubs)} publications)",
                f"_{theme_cfg.description}_",
                "",
            ]
        )
        for idx, pub in enumerate(t_pubs[:6], start=1):
            lines.extend(_format_publication_block(idx, pub, compact=True))

    report_filename = f"{profile.slug}_{run_summary.mode}_{date_tag}.md"
    report_path = reports_dir / report_filename
    latest_path = reports_dir / f"{profile.slug}_latest.md"

    content = "\n".join(lines) + "\n"
    report_path.write_text(content, encoding="utf-8")
    latest_path.write_text(content, encoding="utf-8")
    return report_path


def _format_publication_block(
    rank: int, pub: ClassifiedPublication, compact: bool = False
) -> List[str]:
    badge_foundational = " 🏆 **[Article Fondateur]**" if pub.is_foundational else ""
    badge_oa = " 🔓 *[Open Access]*" if pub.is_open_access else ""
    sample_info = f" | **n = {pub.sample_size}**" if pub.sample_size else ""
    authors_short = ", ".join(pub.authors[:4]) + (" et al." if len(pub.authors) > 4 else "")

    links: List[str] = []
    if pub.url:
        links.append(f"[Lien Source]({pub.url})")
    if pub.doi:
        links.append(f"[DOI:{pub.doi}](https://doi.org/{pub.doi})")
    if pub.pmid:
        links.append(f"[PMID:{pub.pmid}](https://pubmed.ncbi.nlm.nih.gov/{pub.pmid}/)")
    if pub.pdf_url:
        links.append(f"[PDF]({pub.pdf_url})")
    links_str = " • ".join(links)

    block = [
        f"#### {rank}. {pub.title}{badge_foundational}{badge_oa}",
        f"- **Score Global** : **`{pub.overall_score}/100`** | "
        f"**Qualité** : **`{pub.quality_score}/100` (Grade {pub.quality_grade})** | "
        f"**Portée Terrain** : **`{pub.scope_score}/100` ({pub.scope_level})**",
        f"- **Type & Preuve** : `{pub.publication_type_label}` — *{pub.evidence_level}*{sample_info}",
        f"- **Thème** : `{pub.primary_theme_label}` | **Cible** : `{pub.athlete_level_label}` | **Cadre** : `{pub.study_setting}`",
        f"- **Référence** : {authors_short} — *{pub.journal}* ({pub.publication_date}) • Citations : `{pub.citation_count}` • Sources : `{', '.join(pub.sources)}`",
        f"- **Synthèse** : {pub.summary_fr}",
        f"- 💡 **Takeaway Coaching** : {pub.practical_takeaway}",
    ]
    if not compact:
        if pub.key_findings:
            block.append(f"- 📊 **Résultats clés** : {' ; '.join(pub.key_findings[:2])}")
        block.append(f"- ⚠️ **Limites & Vigilance** : {pub.limitations}")
    if links_str:
        block.append(f"- 🔗 {links_str}")
    block.append("")
    return block
