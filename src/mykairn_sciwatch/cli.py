"""
Interface en ligne de commande (CLI) de myKairn SciWatch (`sciwatch`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from mykairn_sciwatch.config import (
    AppConfig,
    list_topic_profiles,
    resolve_profile,
    save_topic_profile,
)
from mykairn_sciwatch.pipeline import SciWatchPipeline
from mykairn_sciwatch.profile_generator import generate_topic_profile
from mykairn_sciwatch.reporting.exporters import (
    export_to_csv,
    export_to_json,
    export_to_mykairn_knowledge_pack,
)
from mykairn_sciwatch.web.server import run_web_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sciwatch",
        description=(
            "myKairn SciWatch — Moteur modulaire d'audit et de veille scientifique automatisée "
            "(PubMed, OpenAlex, Semantic Scholar, Crossref/RSS) avec classification 6D."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # 1. audit
    p_audit = sub.add_parser("audit", help="Lancer un Audit État de l'Art complet sur un sujet")
    p_audit.add_argument(
        "--profile",
        "-p",
        default="trail_running_coaching",
        help="Slug ou chemin du profil de veille (défaut: trail_running_coaching)",
    )
    p_audit.add_argument(
        "--max-per-source",
        "-m",
        type=int,
        default=None,
        help="Nombre maximum de publications à collecter par source",
    )
    p_audit.add_argument(
        "--sources",
        "-s",
        default=None,
        help="Sources séparées par des virgules (pubmed,openalex,semantic_scholar,crossref,pedro,rss)",
    )
    p_audit.add_argument("--notify", action="store_true", help="Envoyer le digest email / webhook")

    # 2. watch
    p_watch = sub.add_parser("watch", help="Lancer une veille incrémentale sur les nouvelles parutions")
    p_watch.add_argument(
        "--profile",
        "-p",
        default="trail_running_coaching",
        help="Slug ou chemin du profil de veille (défaut: trail_running_coaching)",
    )
    p_watch.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Fenêtre temporelle en jours (défaut: 30)",
    )
    p_watch.add_argument(
        "--max-per-source",
        "-m",
        type=int,
        default=None,
        help="Nombre maximum de publications à collecter par source",
    )
    p_watch.add_argument("--notify", action="store_true", help="Envoyer le digest email / webhook")

    # 3. profile
    p_prof = sub.add_parser("profile", help="Gérer ou générer des profils de sujets à auditer")
    prof_sub = p_prof.add_subparsers(dest="profile_action", required=True)
    prof_sub.add_parser("list", help="Lister les profils de sujets disponibles")

    p_create = prof_sub.add_parser("create", help="Générer un nouveau profil de sujet à auditer")
    p_create.add_argument("--name", "-n", required=True, help="Titre du sujet à auditer")
    p_create.add_argument(
        "--keywords",
        "-k",
        required=True,
        help="Mots-clés scientifiques (en anglais, séparés par des virgules)",
    )
    p_create.add_argument("--domain", default="general_science", help="Domaine scientifique")
    p_create.add_argument("--description", default="", help="Description de l'audit")
    p_create.add_argument("--start-year", type=int, default=2016, help="Année de début d'audit")

    # 4. export
    p_exp = sub.add_parser("export", help="Exporter les publications classées (markdown, csv, json, mykairn)")
    p_exp.add_argument("--profile", "-p", default="trail_running_coaching", help="Slug du profil")
    p_exp.add_argument(
        "--format",
        "-f",
        choices=["markdown", "csv", "json", "mykairn"],
        default="markdown",
        help="Format d'export",
    )
    p_exp.add_argument("--output", "-o", default=None, help="Fichier de sortie")

    # 5. stats
    p_stats = sub.add_parser("stats", help="Afficher les statistiques 6D d'un sujet audité")
    p_stats.add_argument("--profile", "-p", default="trail_running_coaching", help="Slug du profil")

    # 6. serve
    p_serve = sub.add_parser("serve", help="Démarrer le Dashboard Web & l'API REST")
    p_serve.add_argument("--host", default=None, help="Hôte d'écoute (défaut: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=None, help="Port d'écoute (défaut: 8095)")

    # 7. push (synchronisation vers mykairn.fr /api/science/packs)
    p_push = sub.add_parser(
        "push",
        help="Pousser le Knowledge Pack 6D d'un sujet vers mykairn.fr (/api/science/packs)",
    )
    p_push.add_argument("--profile", "-p", default="trail_running_coaching", help="Slug du profil")
    p_push.add_argument(
        "--url",
        default=None,
        help="URL de destination (défaut: MYKAIRN_WEBHOOK_URL ou https://www.mykairn.fr/api/science/packs)",
    )
    p_push.add_argument(
        "--secret",
        default=None,
        help="Secret Webhook (défaut: MYKAIRN_WEBHOOK_SECRET)",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AppConfig()
    config.ensure_dirs()

    if args.command in ("audit", "watch"):
        pipeline = SciWatchPipeline(config)
        sources = (
            [s.strip() for s in args.sources.split(",") if s.strip()]
            if getattr(args, "sources", None)
            else None
        )
        days = getattr(args, "days", None)
        print(f"🔬 Exécution de [{args.command.upper()}] sur le profil '{args.profile}'...")
        summary = pipeline.run_for_profile(
            profile_or_slug=args.profile,
            mode=args.command,
            lookback_days=days,
            max_per_source=args.max_per_source,
            enabled_sources=sources,
            send_notifications=args.notify,
        )
        print(f"✅ Statut : {summary.status}")
        print(f"   • Publications brutes collectées : {summary.raw_fetched_count}")
        print(f"   • Après dédoublonnage multi-sources : {summary.deduplicated_count}")
        print(f"   • Retenues & classées en 6D : {summary.classified_count}")
        print(f"   • Nouvelles en base : {summary.new_inserted_count} | Mises à jour : {summary.updated_count}")
        if summary.report_path:
            print(f"   • Rapport Markdown généré : {summary.report_path}")
        return 0

    if args.command == "profile":
        if args.profile_action == "list":
            profiles = list_topic_profiles(config.profiles_dir)
            for p in profiles:
                print(f"• {p.slug:30s} | {p.name} ({len(p.themes)} thèmes, {len(p.queries)} requêtes)")
            return 0

        if args.profile_action == "create":
            kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
            prof = generate_topic_profile(
                name=args.name,
                description=args.description,
                domain=args.domain,
                seed_keywords=kws,
                audit_start_year=args.start_year,
            )
            saved = save_topic_profile(prof, config.profiles_dir)
            print(f"✅ Profil '{prof.slug}' généré et sauvegardé dans : {saved}")
            return 0

    if args.command == "export":
        pipeline = SciWatchPipeline(config)
        profile = resolve_profile(args.profile, config.profiles_dir)
        pubs = pipeline.store.query_publications(topic_slug=profile.slug, limit=1000)
        analytics = pipeline.store.get_analytics(topic_slug=profile.slug)
        out_path = Path(args.output) if args.output else None

        if args.format == "csv":
            target = out_path or (config.reports_dir / f"{profile.slug}_export.csv")
            export_to_csv(pubs, output_path=target)
            print(f"✅ Export CSV généré : {target}")
        elif args.format == "json":
            target = out_path or (config.reports_dir / f"{profile.slug}_export.json")
            export_to_json(pubs, analytics=analytics, output_path=target)
            print(f"✅ Export JSON généré : {target}")
        elif args.format == "mykairn":
            target = out_path or (config.reports_dir / f"{profile.slug}_mykairn_pack.json")
            export_to_mykairn_knowledge_pack(profile, pubs, output_path=target)
            print(f"✅ Knowledge Pack myKairn Platform généré : {target}")
        else:
            target = config.reports_dir / f"{profile.slug}_latest.md"
            print(f"✅ Rapport Markdown disponible : {target}")
        return 0

    if args.command == "stats":
        pipeline = SciWatchPipeline(config)
        analytics = pipeline.store.get_analytics(topic_slug=args.profile)
        print(json.dumps(analytics, ensure_ascii=False, indent=2))
        return 0

    if args.command == "serve":
        host = args.host or config.host
        port = args.port or config.port
        run_web_server(host=host, port=port, config=config)
        return 0

    if args.command == "push":
        pipeline = SciWatchPipeline(config)
        profile = resolve_profile(args.profile, config.profiles_dir)
        pubs = pipeline.store.query_publications(topic_slug=profile.slug, limit=500)
        pack = export_to_mykairn_knowledge_pack(profile, pubs)
        if args.url:
            config.mykairn_webhook_url = args.url
        elif not config.mykairn_webhook_url:
            config.mykairn_webhook_url = "https://www.mykairn.fr/api/science/packs"
        if args.secret:
            config.mykairn_webhook_secret = args.secret
        ok = pipeline.notifier.push_webhook(pack)
        if ok:
            print(
                f"✅ Knowledge Pack '{profile.slug}' ({len(pubs)} études) synchronisé vers {config.mykairn_webhook_url}"
            )
            return 0
        print(
            f"❌ Échec de la synchronisation vers {config.mykairn_webhook_url} (vérifiez MYKAIRN_WEBHOOK_SECRET)."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
