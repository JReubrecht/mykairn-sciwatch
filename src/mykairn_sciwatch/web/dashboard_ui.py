"""
Interface HTML/CSS/JS du Dashboard Web myKairn SciWatch.
Implémente intégralement la Charte Graphique Unifiée V2 de mykairn.fr ("Albères Performance") :
- Nuancier officiel : Marine Principal (#0F172A), Cairn Pétrole (#1E4D6B), Cairn Profond (#0F2D42),
  Corail Accent (#FF5A36 / hover #E34A28), Trail Mint (#14C38E / Émeraude WCAG #047857),
  Fond Clair Alpin (#F8FAFC) avec lignes topographiques IGN (.bg-topo-lines), Cartes Blanc Pur (#FFFFFF)
  et bordures (#E2E8F0).
- Typographie : Instrument Sans (UI & titres) + JetBrains Mono (métriques tabular-nums, badges & codes).
- Logo vectoriel officiel myKairn Coach à 3 galets organiques (courbes de Bézier) sans cadre.
"""

from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>myKairn SciWatch — Endurance Lab · Audit & Veille Scientifique 6D</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg width='512' height='512' viewBox='0 0 512 512' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='512' height='512' rx='108' fill='%230F172A'/%3E%3Cg transform='translate(68, 82) scale(3.6)'%3E%3Cpath fill='%23FF5A36' d='M 38.49,21.84 C 35.15,17.64 37.76,8.40 48.65,4.78 C 58.87,1.36 67.85,5.24 68.20,12.35 C 68.44,18.20 59.81,22.21 49.46,24.38 C 43.60,25.54 40.63,24.32 38.49,21.84 Z'/%3E%3Cpath fill='%23FFFFFF' d='M 22.97,50.53 C 18.76,45.02 25.09,35.05 50.03,29.77 C 73.92,24.69 87.58,28.75 86.59,38.43 C 85.69,45.50 71.35,49.76 52.94,52.36 C 34.02,55.06 26.07,54.31 22.97,50.53 Z'/%3E%3Cpath fill='%23FFFFFF' d='M 15.45,84.52 C 10.86,76.98 15.86,64.08 31.83,59.91 C 47.11,55.87 68.27,52.86 85.56,53.76 C 96.62,54.44 100.77,65.07 97.36,73.18 C 94.58,79.43 79.42,82.70 57.60,86.07 C 34.39,89.67 19.28,90.42 15.45,84.52 Z'/%3E%3C/g%3E%3C/svg%3E" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {
      /* Albères Performance · Charte Unifiée V2 (mykairn.fr) */
      --mk-slate-deep: #0F172A;
      --mk-cairn-petrol: #1E4D6B;
      --mk-cairn-deep: #0F2D42;
      --mk-slate-muted: #64748B;
      --mk-alpine-bg: #F8FAFC;
      --mk-border-light: #E2E8F0;
      --mk-surface-card: #FFFFFF;
      --mk-kairn-orange: #FF5A36;
      --mk-kairn-orange-hover: #E34A28;
      --mk-kairn-orange-light: #FF7A59;
      --mk-trail-mint: #14C38E;
      --mk-trail-mint-light: #34D399;
      --mk-emerald-dark: #047857;
      --mk-amber-alert: #F59E0B;
      --mk-danger-red: #E11D48;

      --font-sans: "Instrument Sans", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: var(--font-sans);
      background-color: var(--mk-alpine-bg);
      color: var(--mk-slate-deep);
      -webkit-font-smoothing: antialiased;
      font-feature-settings: "cv02", "cv03", "cv04", "cv11";
      line-height: 1.55;
      padding-bottom: 64px;
      /* Motif topographique IGN discret (lignes de niveau à 4.5 % d'opacité) */
      background-image: url("data:image/svg+xml,%3Csvg width='320' height='320' viewBox='0 0 320 320' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%230F172A' stroke-opacity='0.045' stroke-width='1'%3E%3Cpath d='M-20 40 C 60 10, 120 90, 210 55 C 275 30, 310 75, 340 60'/%3E%3Cpath d='M-20 95 C 55 55, 130 140, 215 100 C 280 70, 310 120, 340 105'/%3E%3Cpath d='M-20 155 C 65 110, 135 195, 225 150 C 285 120, 315 170, 340 155'/%3E%3Cpath d='M-20 220 C 70 175, 145 255, 235 210 C 295 180, 318 225, 340 210'/%3E%3Cpath d='M-20 280 C 75 245, 155 310, 245 270 C 300 245, 320 285, 340 275'/%3E%3C/g%3E%3C/svg%3E");
      background-size: 320px 320px;
    }

    .tabular-nums { font-variant-numeric: tabular-nums; }
    .font-mono { font-family: var(--font-mono); }

    /* Top Promo / System Bar (style PublicNavbar mykairn.fr) */
    .top-banner {
      background: var(--mk-slate-deep);
      color: #E2E8F0;
      padding: 8px 24px;
      font-size: 0.76rem;
      border-bottom: 1px solid #1E293B;
    }
    .top-banner-inner {
      max-width: 1380px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .top-banner-tag {
      font-family: var(--font-mono);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--mk-kairn-orange);
      font-weight: 700;
      margin-right: 8px;
    }
    .top-banner-status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-family: var(--font-mono);
      font-size: 10.5px;
      color: #94A3B8;
    }
    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--mk-trail-mint);
      box-shadow: 0 0 8px var(--mk-trail-mint);
    }

    /* Sticky Navbar myKairn (fond blanc / blur) */
    .navbar {
      position: sticky;
      top: 0;
      z-index: 40;
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--mk-border-light);
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }
    .navbar-inner {
      max-width: 1380px;
      margin: 0 auto;
      padding: 12px 24px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    /* BrandLogo officiel myKairn V2 */
    .brand-logo {
      display: inline-flex;
      align-items: center;
      gap: 11px;
      text-decoration: none;
      user-select: none;
    }
    .brand-wordmark-wrap {
      display: flex;
      flex-direction: column;
      line-height: 1;
    }
    .brand-wordmark-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .brand-wordmark {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.03em;
      color: var(--mk-slate-deep);
    }
    .brand-wordmark span {
      color: var(--mk-kairn-orange);
    }
    .brand-pill {
      font-family: var(--font-mono);
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      padding: 3px 9px;
      border-radius: 999px;
      background: var(--mk-slate-deep);
      color: #FFFFFF;
    }
    .brand-sub {
      font-family: var(--font-mono);
      font-size: 9px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.24em;
      color: var(--mk-slate-muted);
      margin-top: 4px;
    }

    /* Controls & Buttons */
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }
    select, input, textarea, button {
      font-family: var(--font-sans);
      font-size: 0.84rem;
      border-radius: 8px;
      border: 1px solid var(--mk-border-light);
      background: var(--mk-surface-card);
      color: var(--mk-slate-deep);
      padding: 8px 13px;
      transition: all 0.15s ease;
    }
    select:focus, input:focus, textarea:focus {
      outline: none;
      border-color: var(--mk-cairn-petrol);
      box-shadow: 0 0 0 3px rgba(30, 77, 107, 0.12);
    }
    button {
      cursor: pointer;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .btn-coral {
      background: var(--mk-kairn-orange);
      border-color: var(--mk-kairn-orange);
      color: #FFFFFF;
      box-shadow: 0 2px 6px rgba(255, 90, 54, 0.25);
    }
    .btn-coral:hover {
      background: var(--mk-kairn-orange-hover);
      border-color: var(--mk-kairn-orange-hover);
    }
    .btn-marine {
      background: var(--mk-slate-deep);
      border-color: var(--mk-slate-deep);
      color: #FFFFFF;
    }
    .btn-marine:hover {
      background: var(--mk-cairn-petrol);
      border-color: var(--mk-cairn-petrol);
    }
    .btn-mint {
      background: #ECFDF5;
      border-color: #A7F3D0;
      color: var(--mk-emerald-dark);
    }
    .btn-mint:hover {
      background: #D1FAE5;
    }
    .btn-outline {
      background: var(--mk-surface-card);
      border-color: var(--mk-border-light);
      color: #334155;
    }
    .btn-outline:hover {
      border-color: #CBD5E1;
      background: #F1F5F9;
      color: var(--mk-slate-deep);
    }

    .container {
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px;
    }

    /* Hero Card Cairn Pétrole -> Cairn Profond */
    .hero-banner {
      background: linear-gradient(135deg, var(--mk-slate-deep) 0%, var(--mk-cairn-deep) 52%, var(--mk-cairn-petrol) 100%);
      border-radius: 16px;
      padding: 24px 28px;
      color: #FFFFFF;
      margin-bottom: 22px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.18);
      position: relative;
      overflow: hidden;
    }
    .hero-eyebrow {
      font-family: var(--font-mono);
      font-size: 10.5px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: var(--mk-trail-mint-light);
      font-weight: 700;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .hero-title {
      font-size: 1.45rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #FFFFFF;
      margin-bottom: 6px;
    }
    .hero-desc {
      font-size: 0.88rem;
      color: #CBD5E1;
      max-width: 780px;
    }
    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    /* KPIs 6D */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
      gap: 14px;
      margin-bottom: 22px;
    }
    .kpi-card {
      background: var(--mk-surface-card);
      border: 1px solid var(--mk-border-light);
      border-radius: 12px;
      padding: 16px 18px;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
      position: relative;
      overflow: hidden;
    }
    .kpi-card::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
      background: var(--mk-cairn-petrol);
    }
    .kpi-card.accent-coral::before { background: var(--mk-kairn-orange); }
    .kpi-card.accent-mint::before { background: var(--mk-trail-mint); }
    .kpi-card.accent-amber::before { background: var(--mk-amber-alert); }
    .kpi-label {
      font-family: var(--font-mono);
      font-size: 10.5px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--mk-slate-muted);
      font-weight: 700;
    }
    .kpi-value {
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
      font-size: 1.75rem;
      font-weight: 700;
      margin-top: 6px;
      color: var(--mk-slate-deep);
    }
    .kpi-sub {
      font-size: 0.76rem;
      color: var(--mk-slate-muted);
      margin-top: 3px;
    }

    /* Panneaux Analytiques Data-Viz (Échelle Z1-Z5 myKairn) */
    .analytics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 16px;
      margin-bottom: 22px;
    }
    .panel {
      background: var(--mk-surface-card);
      border: 1px solid var(--mk-border-light);
      border-radius: 12px;
      padding: 18px 20px;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid #F1F5F9;
    }
    .panel-tag {
      font-family: var(--font-mono);
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--mk-cairn-petrol);
    }
    .panel-hint {
      font-family: var(--font-mono);
      font-size: 10px;
      color: var(--mk-slate-muted);
    }
    .bar-row {
      margin-bottom: 10px;
      font-size: 0.82rem;
      cursor: pointer;
      padding: 4px 6px;
      border-radius: 6px;
      transition: background 0.12s;
    }
    .bar-row:hover {
      background: #F8FAFC;
    }
    .bar-row:hover .bar-title {
      color: var(--mk-kairn-orange);
    }
    .bar-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
      font-weight: 500;
      color: var(--mk-slate-deep);
    }
    .bar-count {
      font-family: var(--font-mono);
      font-size: 0.76rem;
      color: var(--mk-slate-muted);
    }
    .bar-track {
      height: 7px;
      background: #F1F5F9;
      border-radius: 999px;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      background: var(--mk-trail-mint); /* Z2 Endurance */
      border-radius: 999px;
    }
    .bar-fill.ebm {
      background: var(--mk-cairn-petrol); /* Cairn Pétrole */
    }
    .bar-fill.scope {
      background: var(--mk-kairn-orange); /* Z4 Corail Accent */
    }

    /* Barre de filtres multi-critères */
    .filters-bar {
      background: var(--mk-surface-card);
      border: 1px solid var(--mk-border-light);
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 20px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
      gap: 12px;
      align-items: end;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
    }
    .filter-group label {
      display: block;
      font-family: var(--font-mono);
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--mk-slate-muted);
      margin-bottom: 5px;
    }
    .filter-group select, .filter-group input {
      width: 100%;
      background: #F8FAFC;
    }

    /* Cartes de Publications 6D */
    .pub-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .pub-card {
      background: var(--mk-surface-card);
      border: 1px solid var(--mk-border-light);
      border-radius: 14px;
      padding: 22px 24px;
      box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
      transition: all 0.15s ease;
    }
    .pub-card:hover {
      border-color: #CBD5E1;
      box-shadow: 0 8px 20px -4px rgba(15, 23, 42, 0.07);
    }
    .pub-top {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
    }
    .badges {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      align-items: center;
    }
    .badge {
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 999px;
      background: #F1F5F9;
      border: 1px solid var(--mk-border-light);
      color: #334155;
      font-variant-numeric: tabular-nums;
    }
    .badge-score {
      background: var(--mk-slate-deep);
      border-color: var(--mk-slate-deep);
      color: #FFFFFF;
    }
    .badge-grade {
      background: #EFF6FF;
      border-color: #BFDBFE;
      color: var(--mk-cairn-petrol);
    }
    .badge-ebm {
      background: #FFF7ED;
      border-color: #FED7AA;
      color: #C2410C;
    }
    .badge-scope {
      background: #ECFDF5;
      border-color: #A7F3D0;
      color: var(--mk-emerald-dark);
    }
    .badge-foundational {
      background: #FFF1F2;
      border-color: #FECDD3;
      color: var(--mk-danger-red);
    }
    .pub-title {
      font-size: 1.14rem;
      font-weight: 700;
      letter-spacing: -0.015em;
      color: var(--mk-slate-deep);
      margin-bottom: 6px;
    }
    .pub-title a {
      color: inherit;
      text-decoration: none;
    }
    .pub-title a:hover {
      color: var(--mk-kairn-orange);
    }
    .pub-meta {
      font-size: 0.83rem;
      color: var(--mk-slate-muted);
      margin-bottom: 14px;
    }
    .pub-meta strong {
      color: var(--mk-cairn-petrol);
    }
    .pub-summary {
      font-size: 0.9rem;
      color: #1E293B;
      background: #F8FAFC;
      border: 1px solid var(--mk-border-light);
      border-left: 4px solid var(--mk-cairn-petrol);
      padding: 12px 16px;
      border-radius: 0 10px 10px 0;
      margin-bottom: 10px;
    }
    .pub-takeaway {
      font-size: 0.9rem;
      color: #064E3B;
      background: #ECFDF5;
      border: 1px solid #A7F3D0;
      border-left: 4px solid var(--mk-trail-mint);
      padding: 12px 16px;
      border-radius: 0 10px 10px 0;
      margin-bottom: 12px;
    }
    .pub-footer {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      font-size: 0.79rem;
      color: var(--mk-slate-muted);
      padding-top: 10px;
      border-top: 1px solid #F1F5F9;
    }
    .pub-links a {
      font-family: var(--font-mono);
      font-size: 0.77rem;
      color: var(--mk-cairn-petrol);
      text-decoration: none;
      margin-right: 14px;
      font-weight: 700;
    }
    .pub-links a:hover {
      color: var(--mk-kairn-orange);
      text-decoration: underline;
    }

    /* Modal Nouveau Sujet */
    .modal-backdrop {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.65);
      backdrop-filter: blur(4px);
      z-index: 50;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .modal-backdrop.active { display: flex; }
    .modal {
      background: var(--mk-surface-card);
      border: 1px solid var(--mk-border-light);
      border-radius: 16px;
      max-width: 600px;
      width: 100%;
      padding: 26px;
      box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
    }
    .modal h2 {
      font-size: 1.22rem;
      color: var(--mk-slate-deep);
      margin-bottom: 6px;
    }
    .modal p {
      font-size: 0.85rem;
      color: var(--mk-slate-muted);
      margin-bottom: 18px;
    }
    .form-row { margin-bottom: 14px; }
    .form-row label {
      display: block;
      font-family: var(--font-mono);
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--mk-slate-deep);
      margin-bottom: 5px;
    }
    .form-row input, .form-row textarea, .form-row select {
      width: 100%;
      background: #F8FAFC;
    }
    .status-toast {
      position: fixed;
      bottom: 22px;
      right: 22px;
      background: var(--mk-slate-deep);
      border-left: 4px solid var(--mk-kairn-orange);
      color: #FFFFFF;
      padding: 13px 18px;
      border-radius: 10px;
      font-size: 0.86rem;
      font-weight: 500;
      display: none;
      z-index: 100;
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.28);
    }

    .mobile-only-btn {
      display: none;
    }

    .filters-collapsible {
      display: contents;
    }

    @media (max-width: 1024px) {
      .analytics-grid {
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      }
      .navbar-inner {
        padding: 12px 16px;
      }
      .container {
        padding: 16px;
      }
    }

    @media (max-width: 768px) {
      html, body {
        overflow-x: hidden;
      }
      body {
        padding-bottom: 48px;
      }
      .top-banner {
        padding: 6px 12px;
        font-size: 0.68rem;
      }
      .top-banner-desc {
        display: none;
      }
      .navbar-inner {
        padding: 10px 12px;
        gap: 8px;
      }
      .brand-wordmark {
        font-size: 18px;
      }
      .brand-sub {
        display: none;
      }
      .mobile-only-btn {
        display: inline-flex;
        padding: 7px 11px;
        font-size: 0.78rem;
      }
      .toolbar {
        display: none;
        width: 100%;
        flex-direction: column;
        align-items: stretch;
        padding-top: 8px;
        border-top: 1px solid var(--mk-border-light);
      }
      .toolbar.mobile-open {
        display: flex;
      }
      .toolbar select,
      .toolbar button {
        width: 100%;
        justify-content: center;
      }
      .container {
        padding: 12px;
      }
      .hero-banner {
        padding: 16px;
        border-radius: 12px;
        gap: 12px;
        margin-bottom: 14px;
      }
      .hero-title {
        font-size: 1.12rem;
      }
      .hero-desc {
        font-size: 0.78rem;
      }
      .hero-actions {
        width: 100%;
      }
      .hero-actions button {
        flex: 1 1 auto;
        justify-content: center;
        font-size: 0.75rem;
        padding: 7px 10px;
      }
      .kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        margin-bottom: 14px;
      }
      .kpi-card {
        padding: 12px;
      }
      .kpi-value {
        font-size: 1.28rem;
      }
      .kpi-label {
        font-size: 9.5px;
      }
      .analytics-grid {
        grid-template-columns: 1fr;
        gap: 12px;
        margin-bottom: 14px;
      }
      .panel {
        padding: 14px;
      }
      .filters-bar {
        grid-template-columns: 1fr;
        padding: 12px 14px;
        gap: 10px;
        margin-bottom: 14px;
      }
      .filters-collapsible {
        display: none;
        grid-template-columns: 1fr;
        gap: 10px;
      }
      .filters-collapsible.mobile-open {
        display: grid;
      }
      .pub-card {
        padding: 14px;
        border-radius: 12px;
      }
      .pub-title {
        font-size: 0.98rem;
        line-height: 1.35;
      }
      .pub-meta {
        font-size: 0.76rem;
      }
      .pub-summary,
      .pub-takeaway {
        font-size: 0.8rem;
        padding: 10px 12px;
      }
      .badge {
        font-size: 10px;
        padding: 2px 8px;
      }
      .pub-links {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      .pub-links a {
        margin-right: 0;
        word-break: break-all;
      }
      .pub-footer {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }
      .modal-backdrop {
        padding: 10px;
        align-items: flex-end;
      }
      .modal {
        padding: 18px;
        max-height: 90dvh;
        overflow-y: auto;
        border-radius: 14px;
      }
      .status-toast {
        left: 12px;
        right: 12px;
        bottom: 12px;
        font-size: 0.8rem;
      }
    }
  </style>
</head>
<body>
  <!-- Bandeau Supérieur Marine Principal (#0F172A) — Charte mykairn.fr -->
  <div class="top-banner">
    <div class="top-banner-inner">
      <div>
        <span class="top-banner-tag">[ALBÈRES PERFORMANCE · SCIWATCH 6D]</span>
        <span class="top-banner-desc">Veille & Audit Scientifique Multi-Sources (PubMed · OpenAlex · Semantic Scholar · Crossref)</span>
      </div>
      <div class="top-banner-status">
        <span class="status-dot"></span>
        <span>ENDURANCE LAB · MOTEUR 6D ACTIF</span>
      </div>
    </div>
  </div>

  <!-- Barre de Navigation Officielle myKairn Coach -->
  <header class="navbar">
    <div class="navbar-inner">
      <a href="/" class="brand-logo">
        <!-- Logo Vectoriel Officiel myKairn Coach (Galets organiques Bézier sans cadre) -->
        <svg width="38" height="38" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <defs>
            <linearGradient id="mkCairnGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#1E4D6B" />
              <stop offset="100%" stop-color="#0F2D42" />
            </linearGradient>
          </defs>
          <!-- Pierre sommitale Corail Accent (#FF5A36) -->
          <path d="M 38.49,21.84 C 35.15,17.64 37.76,8.40 48.65,4.78 C 58.87,1.36 67.85,5.24 68.20,12.35 C 68.44,18.20 59.81,22.21 49.46,24.38 C 43.60,25.54 40.63,24.32 38.49,21.84 Z" fill="#FF5A36" />
          <!-- Pierre médiane Cairn Pétrole -> Profond -->
          <path d="M 22.97,50.53 C 18.76,45.02 25.09,35.05 50.03,29.77 C 73.92,24.69 87.58,28.75 86.59,38.43 C 85.69,45.50 71.35,49.76 52.94,52.36 C 34.02,55.06 26.07,54.31 22.97,50.53 Z" fill="url(#mkCairnGrad)" />
          <!-- Pierre de base Cairn Pétrole -> Profond -->
          <path d="M 15.45,84.52 C 10.86,76.98 15.86,64.08 31.83,59.91 C 47.11,55.87 68.27,52.86 85.56,53.76 C 96.62,54.44 100.77,65.07 97.36,73.18 C 94.58,79.43 79.42,82.70 57.60,86.07 C 34.39,89.67 19.28,90.42 15.45,84.52 Z" fill="url(#mkCairnGrad)" />
        </svg>
        <div class="brand-wordmark-wrap">
          <div class="brand-wordmark-row">
            <span class="brand-wordmark">my<span>Kairn</span></span>
            <span class="brand-pill">SCIWATCH</span>
          </div>
          <span class="brand-sub">ENDURANCE LAB · DATA &amp; PHYSIOLOGIE</span>
        </div>
      </a>

      <button type="button" class="btn-outline mobile-only-btn" id="btnToggleToolbar" onclick="toggleMobileToolbar()">⚙️ Actions</button>

      <div class="toolbar" id="mainToolbar">
        <select id="profileSelect" onchange="onProfileChange()" aria-label="Sélectionner le sujet d'audit"></select>
        <button class="btn-outline" onclick="openNewTopicModal()">➕ Nouveau Sujet à Auditer</button>
        <button class="btn-coral" id="btnAudit" onclick="triggerRun('audit')">🚀 Lancer Audit État de l'Art</button>
        <button class="btn-marine" id="btnWatch" onclick="triggerRun('watch')">🔄 Veille 30j</button>
      </div>
    </div>
  </header>

  <div class="container">
    <!-- Bandeau Cockpit Cairn Pétrole -> Cairn Profond -->
    <section class="hero-banner">
      <div>
        <div class="hero-eyebrow">
          <span>● SUJET D'AUDIT ACTIF</span>
          <span>·</span>
          <span id="heroSlugBadge">TRAIL_RUNNING_COACHING</span>
        </div>
        <h1 class="hero-title" id="topicTitle">Coaching &amp; Accompagnement d'Athlètes Tous Niveaux en Trail Running</h1>
        <p class="hero-desc" id="topicSubtitle">
          Classement automatisé 6D par type d'étude EBM, thème, qualité méthodologique, portée terrain, fraîcheur et takeaways coaching.
        </p>
      </div>
      <div class="hero-actions">
        <button class="btn-outline" onclick="exportData('markdown')">📄 Rapport Markdown</button>
        <button class="btn-outline" onclick="exportData('csv')">📊 Export CSV</button>
        <button class="btn-mint" onclick="exportData('mykairn')">⚡ Knowledge Pack myKairn.fr</button>
      </div>
    </section>

    <!-- KPIs 6D -->
    <div class="kpi-grid">
      <div class="kpi-card accent-coral">
        <div class="kpi-label">Corpus Analysé</div>
        <div class="kpi-value" id="kpiTotal">0</div>
        <div class="kpi-sub">Publications dédoublonnées</div>
      </div>
      <div class="kpi-card accent-mint">
        <div class="kpi-label">Score Global Moyen (6D)</div>
        <div class="kpi-value" id="kpiOverall">0</div>
        <div class="kpi-sub">Pondération Qualité · Portée · Impact</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Qualité Méthodologique</div>
        <div class="kpi-value" id="kpiQuality">0</div>
        <div class="kpi-sub">Design EBM, échantillon n, citations</div>
      </div>
      <div class="kpi-card accent-mint">
        <div class="kpi-label">Portée &amp; Terrain</div>
        <div class="kpi-value" id="kpiScope">0</div>
        <div class="kpi-sub">Validité écologique &amp; tous niveaux</div>
      </div>
      <div class="kpi-card accent-amber">
        <div class="kpi-label">Preuve Élevée (Tiers 1-2)</div>
        <div class="kpi-value" id="kpiTier12">0</div>
        <div class="kpi-sub">Méta-analyses, Revues syst., RCT</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Fondateurs / Open Access</div>
        <div class="kpi-value" id="kpiFoundational">0</div>
        <div class="kpi-sub">Classiques très cités &amp; PDF libres</div>
      </div>
    </div>

    <!-- Panneaux de répartition 6D -->
    <div class="analytics-grid">
      <div class="panel">
        <div class="panel-header">
          <span class="panel-tag">[D2 · THÈMES SCIENTIFIQUES]</span>
          <span class="panel-hint">Cliquer pour filtrer</span>
        </div>
        <div id="barsTheme"></div>
      </div>
      <div class="panel">
        <div class="panel-header">
          <span class="panel-tag">[D1 · PYRAMIDE DES PREUVES EBM]</span>
          <span class="panel-hint">Type de publication</span>
        </div>
        <div id="barsType"></div>
      </div>
      <div class="panel">
        <div class="panel-header">
          <span class="panel-tag">[D4 · PORTÉE &amp; NIVEAU D'ATHLÈTE]</span>
          <span class="panel-hint">Public cible étudié</span>
        </div>
        <div id="barsAthlete"></div>
      </div>
    </div>

    <!-- Barre de filtres multi-critères & booléenne -->
    <div class="filters-bar">
      <div class="filter-group" style="grid-column: 1 / -1;">
        <div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;margin-bottom:5px;">
          <label style="margin-bottom:0;">Requête Booléenne Scientifique (AND · OR · NOT · "..." · (...) · * · ti: au: jo: mesh:)</label>
          <div style="display:flex;flex-wrap:wrap;gap:4px;">
            <button type="button" class="btn-outline" style="padding:2px 7px;font-size:10px;font-family:var(--font-mono);" onclick="insertCorpusToken(' AND ')">AND</button>
            <button type="button" class="btn-outline" style="padding:2px 7px;font-size:10px;font-family:var(--font-mono);" onclick="insertCorpusToken(' OR ')">OR</button>
            <button type="button" class="btn-outline" style="padding:2px 7px;font-size:10px;font-family:var(--font-mono);" onclick="insertCorpusToken(' NOT ')">NOT</button>
            <button type="button" class="btn-outline" style="padding:2px 7px;font-size:10px;font-family:var(--font-mono);" onclick="insertCorpusToken('\"\"')">"phrase"</button>
            <button type="button" class="btn-outline" style="padding:2px 7px;font-size:10px;font-family:var(--font-mono);" onclick="insertCorpusToken('()')">( )</button>
            <button type="button" class="btn-outline" style="padding:2px 7px;font-size:10px;font-family:var(--font-mono);" onclick="insertCorpusToken('*')">*</button>
            <button type="button" class="btn-outline" style="padding:2px 7px;font-size:10px;font-family:var(--font-mono);" onclick="insertCorpusToken('ti:')">ti:</button>
            <button type="button" class="btn-outline" style="padding:2px 7px;font-size:10px;font-family:var(--font-mono);" onclick="insertCorpusToken('au:')">au:</button>
            <button type="button" class="btn-outline" style="padding:2px 7px;font-size:10px;font-family:var(--font-mono);" onclick="insertCorpusToken('mesh:')">mesh:</button>
          </div>
        </div>
        <input type="text" id="filterSearch" placeholder='ex: ("trail running" OR ultramarathon) AND (sleep OR HRV) NOT mice' oninput="loadPublications()" />
      </div>
      <button type="button" class="btn-outline mobile-only-btn" id="btnToggleFilters" onclick="toggleMobileFilters()" style="width:100%;justify-content:center;">🔎 Filtres &amp; Tri (D1–D4)</button>
      <div class="filters-collapsible" id="filtersCollapsible">
      <div class="filter-group">
        <label>Thème Scientifique (D2)</label>
        <select id="filterTheme" onchange="loadPublications()"><option value="">Tous les thèmes</option></select>
      </div>
      <div class="filter-group">
        <label>Type de Publication EBM (D1)</label>
        <select id="filterType" onchange="loadPublications()"><option value="">Tous les types</option></select>
      </div>
      <div class="filter-group">
        <label>Niveau d'Athlète / Portée (D4)</label>
        <select id="filterAthlete" onchange="loadPublications()"><option value="">Tous les niveaux</option></select>
      </div>
      <div class="filter-group">
        <label>Grade Qualité (D3)</label>
        <select id="filterGrade" onchange="loadPublications()">
          <option value="">Tous (A+ à D)</option>
          <option value="A+">Grade A+ (&ge; 82)</option>
          <option value="A">Grade A (&ge; 72)</option>
          <option value="B">Grade B (&ge; 60)</option>
          <option value="C">Grade C (&ge; 48)</option>
        </select>
      </div>
      <div class="filter-group">
        <label>Année Min</label>
        <input type="number" id="filterYearFrom" placeholder="2015" min="1950" max="2030" onchange="loadPublications()" />
      </div>
      <div class="filter-group">
        <label>Année Max</label>
        <input type="number" id="filterYearTo" placeholder="2026" min="1950" max="2030" onchange="loadPublications()" />
      </div>
      <div class="filter-group">
        <label>Tri Principal</label>
        <select id="filterSort" onchange="loadPublications()">
          <option value="overall_score">Score Global 6D (Décroissant)</option>
          <option value="quality_score">Qualité Méthodologique (/100)</option>
          <option value="scope_score">Portée Terrain &amp; Coaching (/100)</option>
          <option value="publication_date">Date de parution (Plus récents)</option>
          <option value="citation_count">Impact &amp; Citations</option>
          <option value="evidence_tier">Pyramide EBM (Niveau 1A d'abord)</option>
        </select>
      </div>
      <div class="filter-group" style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;">
        <label style="display:inline-flex;align-items:center;gap:5px;margin-bottom:0;cursor:pointer;"><input type="checkbox" id="filterOA" onchange="loadPublications()" style="width:auto;" /> Open Access</label>
        <label style="display:inline-flex;align-items:center;gap:5px;margin-bottom:0;cursor:pointer;"><input type="checkbox" id="filterNoPreprint" onchange="loadPublications()" style="width:auto;" /> Sans preprints</label>
      </div>
      <div class="filter-group">
        <button class="btn-outline" style="width:100%;justify-content:center;" onclick="resetFilters()">Réinitialiser</button>
      </div>
      </div>
    </div>

    <!-- Liste des publications -->
    <div id="pubList" class="pub-list"></div>
  </div>

  <!-- Modal Création d'un Nouveau Sujet d'Audit Modulaire -->
  <div class="modal-backdrop" id="newTopicModal">
    <div class="modal" style="max-width:720px;">
      <h2>➕ Configurer une Recherche Scientifique Paramétrable</h2>
      <p>Constructeur compatible PubMed Entrez, OpenAlex, Semantic Scholar Bulk et Crossref (AND, OR, NOT, parenthèses, troncature *, champs [Title/Abstract]).</p>
      <div class="form-row">
        <label>Titre du sujet à auditer *</label>
        <input type="text" id="newTopicName" placeholder="ex: Sommeil, VFC et Récupération en Ultra-Endurance" />
      </div>
      <div class="form-row">
        <label>Équation Booléenne Experte (AND / OR / NOT)</label>
        <textarea id="newTopicBoolean" rows="2" class="font-mono" placeholder='ex: ("trail running" OR ultramarathon*) AND ("heart rate variability" OR sleep) NOT mice'></textarea>
      </div>
      <div class="form-row">
        <label>Ou mots-clés simples (séparés par des virgules)</label>
        <input type="text" id="newTopicKeywords" placeholder="ex: heart rate variability, sleep deprivation, endurance recovery" />
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;" class="form-row">
        <div>
          <label>Année début</label>
          <input type="number" id="newTopicYear" value="2016" min="1950" max="2030" />
        </div>
        <div>
          <label>Année fin (opt.)</label>
          <input type="number" id="newTopicEndYear" placeholder="2026" min="1950" max="2030" />
        </div>
        <div>
          <label>Max / source</label>
          <input type="number" id="newTopicMaxPerSource" value="30" min="5" max="100" />
        </div>
        <div>
          <label>Domaine</label>
          <input type="text" id="newTopicDomain" value="sports_science" />
        </div>
      </div>
      <div class="form-row" style="display:flex;flex-wrap:wrap;gap:12px;">
        <label style="display:inline-flex;align-items:center;gap:5px;cursor:pointer;"><input type="checkbox" class="srcCheck" value="pubmed" checked style="width:auto;" /> PubMed</label>
        <label style="display:inline-flex;align-items:center;gap:5px;cursor:pointer;"><input type="checkbox" class="srcCheck" value="openalex" checked style="width:auto;" /> OpenAlex</label>
        <label style="display:inline-flex;align-items:center;gap:5px;cursor:pointer;"><input type="checkbox" class="srcCheck" value="semantic_scholar" checked style="width:auto;" /> Semantic Scholar</label>
        <label style="display:inline-flex;align-items:center;gap:5px;cursor:pointer;"><input type="checkbox" class="srcCheck" value="crossref" checked style="width:auto;" /> Crossref</label>
      </div>
      <div class="form-row" style="display:flex;flex-wrap:wrap;gap:12px;">
        <label style="display:inline-flex;align-items:center;gap:5px;cursor:pointer;"><input type="checkbox" id="newTopicHumans" style="width:auto;" /> Humains uniquement</label>
        <label style="display:inline-flex;align-items:center;gap:5px;cursor:pointer;"><input type="checkbox" id="newTopicOA" style="width:auto;" /> Open Access uniquement</label>
        <label style="display:inline-flex;align-items:center;gap:5px;cursor:pointer;"><input type="checkbox" id="newTopicNoPreprint" style="width:auto;" /> Exclure preprints</label>
      </div>
      <div class="form-row">
        <label>Objectif / Description de l'audit</label>
        <textarea id="newTopicDesc" rows="2" placeholder="Audit de la littérature scientifique et recommandations pratiques..."></textarea>
      </div>
      <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:18px;">
        <button class="btn-outline" onclick="closeNewTopicModal()">Annuler</button>
        <button class="btn-coral" onclick="createNewTopic(true)">Créer &amp; Lancer l'Audit</button>
      </div>
    </div>
  </div>

  <div class="status-toast" id="toast"></div>

  <script>
    let currentTopic = "trail_running_coaching";
    let profilesMap = {};

    function showToast(msg) {
      const t = document.getElementById("toast");
      t.textContent = msg;
      t.style.display = "block";
      setTimeout(() => { t.style.display = "none"; }, 4500);
    }

    function toggleMobileToolbar() {
      const tb = document.getElementById("mainToolbar");
      if (tb) tb.classList.toggle("mobile-open");
    }

    function toggleMobileFilters() {
      const box = document.getElementById("filtersCollapsible");
      if (box) box.classList.toggle("mobile-open");
    }

    function updateHeroHeader() {
      const p = profilesMap[currentTopic];
      document.getElementById("heroSlugBadge").textContent = currentTopic.toUpperCase();
      if (p) {
        document.getElementById("topicTitle").textContent = p.name;
        document.getElementById("topicSubtitle").textContent = p.description || "";
      }
    }

    async function initDashboard() {
      const res = await fetch("/api/profiles");
      const data = await res.json();
      const sel = document.getElementById("profileSelect");
      sel.innerHTML = "";
      profilesMap = {};
      (data.profiles || []).forEach(p => {
        profilesMap[p.slug] = p;
        const opt = document.createElement("option");
        opt.value = p.slug;
        opt.textContent = p.name;
        if (p.slug === currentTopic) opt.selected = true;
        sel.appendChild(opt);
      });
      if (data.profiles && data.profiles.length > 0 && !profilesMap[currentTopic]) {
        currentTopic = data.profiles[0].slug;
      }
      updateHeroHeader();
      await refreshAll();
    }

    async function onProfileChange() {
      const sel = document.getElementById("profileSelect");
      currentTopic = sel.value;
      updateHeroHeader();
      resetFilters(false);
      await refreshAll();
    }

    async function refreshAll() {
      await loadAnalytics();
      await loadPublications();
    }

    async function loadAnalytics() {
      const res = await fetch(`/api/analytics?topic=${encodeURIComponent(currentTopic)}`);
      const a = await res.json();
      document.getElementById("kpiTotal").textContent = a.total_publications || 0;
      document.getElementById("kpiOverall").textContent = `${a.avg_overall_score || 0}/100`;
      document.getElementById("kpiQuality").textContent = `${a.avg_quality_score || 0}/100`;
      document.getElementById("kpiScope").textContent = `${a.avg_scope_score || 0}/100`;
      document.getElementById("kpiTier12").textContent = a.tier_1_2_count || 0;
      document.getElementById("kpiFoundational").textContent = `${a.foundational_count || 0} / ${a.open_access_count || 0}`;

      const total = Math.max(1, a.total_publications || 1);

      // Barres Thèmes + Populate Select
      const themeBox = document.getElementById("barsTheme");
      const themeSelect = document.getElementById("filterTheme");
      const prevTheme = themeSelect.value;
      themeBox.innerHTML = "";
      themeSelect.innerHTML = '<option value="">Tous les thèmes</option>';
      (a.by_theme || []).forEach(th => {
        const pct = Math.round((th.count / total) * 100);
        themeBox.innerHTML += `
          <div class="bar-row" onclick="setSelectAndLoad('filterTheme', '${th.slug}')">
            <div class="bar-header"><span class="bar-title">${th.label}</span><span class="bar-count"><strong>${th.count}</strong> · ${th.avg_score}/100</span></div>
            <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
          </div>`;
        themeSelect.innerHTML += `<option value="${th.slug}">${th.label} (${th.count})</option>`;
      });
      themeSelect.value = prevTheme;

      // Barres Types EBM
      const typeBox = document.getElementById("barsType");
      const typeSelect = document.getElementById("filterType");
      const prevType = typeSelect.value;
      typeBox.innerHTML = "";
      typeSelect.innerHTML = '<option value="">Tous les types EBM</option>';
      (a.by_publication_type || []).forEach(pt => {
        const pct = Math.round((pt.count / total) * 100);
        typeBox.innerHTML += `
          <div class="bar-row" onclick="setSelectAndLoad('filterType', '${pt.key}')">
            <div class="bar-header"><span class="bar-title">${pt.label} <em style="color:var(--mk-slate-muted);font-weight:400;">(${pt.evidence_level})</em></span><span class="bar-count"><strong>${pt.count}</strong></span></div>
            <div class="bar-track"><div class="bar-fill ebm" style="width:${pct}%"></div></div>
          </div>`;
        typeSelect.innerHTML += `<option value="${pt.key}">${pt.label} (${pt.count})</option>`;
      });
      typeSelect.value = prevType;

      // Barres Niveau d'athlète
      const athBox = document.getElementById("barsAthlete");
      const athSelect = document.getElementById("filterAthlete");
      const prevAth = athSelect.value;
      athBox.innerHTML = "";
      athSelect.innerHTML = '<option value="">Tous les niveaux</option>';
      (a.by_athlete_level || []).forEach(al => {
        const pct = Math.round((al.count / total) * 100);
        athBox.innerHTML += `
          <div class="bar-row" onclick="setSelectAndLoad('filterAthlete', '${al.key}')">
            <div class="bar-header"><span class="bar-title">${al.label}</span><span class="bar-count"><strong>${al.count}</strong> (${pct}%)</span></div>
            <div class="bar-track"><div class="bar-fill scope" style="width:${pct}%"></div></div>
          </div>`;
        athSelect.innerHTML += `<option value="${al.key}">${al.label} (${al.count})</option>`;
      });
      athSelect.value = prevAth;
    }

    function setSelectAndLoad(selectId, val) {
      const el = document.getElementById(selectId);
      el.value = (el.value === val) ? "" : val;
      loadPublications();
    }

    function insertCorpusToken(token) {
      const inp = document.getElementById("filterSearch");
      const start = inp.selectionStart ?? inp.value.length;
      const end = inp.selectionEnd ?? inp.value.length;
      inp.value = inp.value.slice(0, start) + token + inp.value.slice(end);
      inp.focus();
      loadPublications();
    }

    function resetFilters(reload = true) {
      document.getElementById("filterSearch").value = "";
      document.getElementById("filterTheme").value = "";
      document.getElementById("filterType").value = "";
      document.getElementById("filterAthlete").value = "";
      document.getElementById("filterGrade").value = "";
      document.getElementById("filterYearFrom").value = "";
      document.getElementById("filterYearTo").value = "";
      document.getElementById("filterOA").checked = false;
      document.getElementById("filterNoPreprint").checked = false;
      document.getElementById("filterSort").value = "overall_score";
      if (reload) loadPublications();
    }

    async function loadPublications() {
      const params = new URLSearchParams({
        topic: currentTopic,
        q: document.getElementById("filterSearch").value,
        theme: document.getElementById("filterTheme").value,
        type: document.getElementById("filterType").value,
        athlete_level: document.getElementById("filterAthlete").value,
        grade: document.getElementById("filterGrade").value,
        year_from: document.getElementById("filterYearFrom").value,
        year_to: document.getElementById("filterYearTo").value,
        only_open_access: document.getElementById("filterOA").checked ? "1" : "",
        exclude_preprints: document.getElementById("filterNoPreprint").checked ? "1" : "",
        sort: document.getElementById("filterSort").value,
        limit: "120"
      });
      const res = await fetch(`/api/publications?${params.toString()}`);
      const data = await res.json();
      const box = document.getElementById("pubList");
      const pubs = data.publications || [];

      if (pubs.length === 0) {
        box.innerHTML = `<div class="panel" style="text-align:center;padding:42px;">
          <h3 style="margin-bottom:8px;">Aucune publication trouvée pour ces critères</h3>
          <p style="color:var(--mk-slate-muted);font-size:0.88rem;">Cliquez sur « 🚀 Lancer Audit État de l'Art » dans la barre supérieure pour collecter et scorer la littérature scientifique.</p>
        </div>`;
        return;
      }

      box.innerHTML = pubs.map((p, idx) => {
        const authors = (p.authors || []).slice(0, 4).join(", ") + ((p.authors || []).length > 4 ? " et al." : "");
        const foundationalBadge = p.is_foundational ? `<span class="badge badge-foundational">🏆 Fondateur (${p.citation_count} cit.)</span>` : "";
        const oaBadge = p.is_open_access ? `<span class="badge">🔓 Open Access</span>` : "";
        const sampleBadge = p.sample_size ? `<span class="badge">n = ${p.sample_size}</span>` : "";

        return `
          <article class="pub-card">
            <div class="pub-top">
              <div class="badges">
                <span class="badge badge-score">SCORE ${p.overall_score}/100</span>
                <span class="badge badge-grade">QUALITÉ ${p.quality_score}/100 · GRADE ${p.quality_grade}</span>
                <span class="badge badge-scope">PORTÉE ${p.scope_score}/100 · ${p.athlete_level_label}</span>
                <span class="badge badge-ebm">${p.publication_type_label} (${p.evidence_level})</span>
                ${sampleBadge}
                ${foundationalBadge}
                ${oaBadge}
              </div>
              <span class="badge">${p.publication_date}</span>
            </div>
            <h2 class="pub-title">
              <a href="${p.url || '#'}" target="_blank" rel="noopener">${idx + 1}. ${p.title}</a>
            </h2>
            <div class="pub-meta">
              <strong>${p.primary_theme_label}</strong> • ${authors} — <em>${p.journal}</em> (${p.publication_year}) • Cadre : ${p.study_setting} • Citations : <span class="font-mono">${p.citation_count}</span>
            </div>
            <div class="pub-summary">
              <strong>🔬 Synthèse Scientifique :</strong> ${p.summary_fr}
            </div>
            <div class="pub-takeaway">
              <strong>💡 Takeaway Coaching (myKairn) :</strong> ${p.practical_takeaway}
            </div>
            <div class="pub-footer">
              <div class="pub-links">
                ${p.url ? `<a href="${p.url}" target="_blank" rel="noopener">🔗 SOURCE</a>` : ""}
                ${p.doi ? `<a href="https://doi.org/${p.doi}" target="_blank" rel="noopener">DOI:${p.doi}</a>` : ""}
                ${p.pmid ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/" target="_blank" rel="noopener">PMID:${p.pmid}</a>` : ""}
                ${p.pdf_url ? `<a href="${p.pdf_url}" target="_blank" rel="noopener">📄 PDF INTÉGRAL</a>` : ""}
              </div>
              <div>⚠️ <em>${p.limitations}</em> • Sources : <span class="font-mono">${(p.sources || []).join(", ")}</span></div>
            </div>
          </article>
        `;
      }).join("");
    }

    async function triggerRun(mode) {
      const btn = document.getElementById(mode === "audit" ? "btnAudit" : "btnWatch");
      const origText = btn.textContent;
      btn.disabled = true;
      btn.textContent = "⏳ Collecte & Scoring 6D...";
      showToast(`Lancement du mode ${mode.toUpperCase()} sur '${currentTopic}'...`);
      try {
        const res = await fetch("/api/run", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({ topic: currentTopic, mode: mode })
        });
        const data = await res.json();
        if (data.status === "completed") {
          showToast(`✅ Terminé : ${data.classified_count} publications scorées (${data.new_inserted_count} nouvelles)`);
          await refreshAll();
        } else {
          showToast(`❌ Erreur : ${data.error || "Échec de l'exécution"}`);
        }
      } catch (e) {
        showToast(`❌ Erreur réseau : ${e}`);
      } finally {
        btn.disabled = false;
        btn.textContent = origText;
      }
    }

    function exportData(fmt) {
      window.open(`/api/export?topic=${encodeURIComponent(currentTopic)}&format=${encodeURIComponent(fmt)}`, "_blank");
    }

    function openNewTopicModal() {
      document.getElementById("newTopicModal").classList.add("active");
    }
    function closeNewTopicModal() {
      document.getElementById("newTopicModal").classList.remove("active");
    }

    async function createNewTopic(runAuditAfter) {
      const name = document.getElementById("newTopicName").value.trim();
      const booleanQuery = document.getElementById("newTopicBoolean").value.trim();
      const kwRaw = document.getElementById("newTopicKeywords").value.trim();
      const domain = document.getElementById("newTopicDomain").value.trim() || "general_science";
      const startYear = parseInt(document.getElementById("newTopicYear").value || "2016", 10);
      const endYearRaw = document.getElementById("newTopicEndYear").value.trim();
      const maxPerSource = parseInt(document.getElementById("newTopicMaxPerSource").value || "30", 10);
      const desc = document.getElementById("newTopicDesc").value.trim();
      const enabledSources = Array.from(document.querySelectorAll(".srcCheck:checked")).map(el => el.value);

      if (!name || (!kwRaw && !booleanQuery)) {
        showToast("Veuillez renseigner un titre et une équation booléenne ou des mots-clés.");
        return;
      }
      const keywords = kwRaw.split(",").map(s => s.trim()).filter(Boolean);
      const res = await fetch("/api/profiles", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          name: name,
          boolean_query: booleanQuery,
          keywords: keywords,
          domain: domain,
          audit_start_year: startYear,
          audit_end_year: endYearRaw ? parseInt(endYearRaw, 10) : null,
          max_results_per_source: maxPerSource,
          enabled_sources: enabledSources,
          humans_only: document.getElementById("newTopicHumans").checked,
          open_access_only: document.getElementById("newTopicOA").checked,
          exclude_preprints: document.getElementById("newTopicNoPreprint").checked,
          description: desc
        })
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(`❌ ${data.error || "Erreur lors de la création"}`);
        return;
      }
      if (data.profile && data.profile.slug) {
        closeNewTopicModal();
        currentTopic = data.profile.slug;
        await initDashboard();
        showToast(`Profil '${data.profile.name}' créé avec succès !`);
        if (runAuditAfter) {
          await triggerRun("audit");
        }
      }
    }

    initDashboard();
  </script>
</body>
</html>
"""
