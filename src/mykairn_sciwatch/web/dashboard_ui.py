"""
Interface HTML/CSS/JS autonome du Dashboard Web myKairn SciWatch.
Conçue pour être rapide, moderne, sans dépendance CDN lourde et adaptée à la VM Freebox.
"""

from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>myKairn SciWatch — Audit & Veille Scientifique 6D</title>
  <style>
    :root {
      --bg: #0b1120;
      --bg-card: #111827;
      --bg-card-hover: #1e293b;
      --border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #10b981;
      --accent-dark: #059669;
      --blue: #0ea5e9;
      --amber: #f59e0b;
      --purple: #a855f7;
      --rose: #f43f5e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding-bottom: 60px;
    }
    header {
      background: linear-gradient(135deg, #0f172a 0%, #064e3b 100%);
      border-bottom: 1px solid var(--border);
      padding: 20px 28px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }
    .brand { display: flex; align-items: center; gap: 14px; }
    .brand-badge {
      width: 44px; height: 44px; border-radius: 12px;
      background: rgba(16, 185, 129, 0.2); border: 1px solid var(--accent);
      display: flex; align-items: center; justify-content: center;
      font-size: 22px;
    }
    .brand h1 { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; }
    .brand p { font-size: 0.85rem; color: #a7f3d0; }
    .toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
    select, input, textarea, button {
      font-family: inherit;
      font-size: 0.88rem;
      border-radius: 8px;
      border: 1px solid #374151;
      background: #1f2937;
      color: var(--text);
      padding: 8px 12px;
    }
    button {
      cursor: pointer;
      font-weight: 600;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .btn-primary { background: var(--accent); border-color: var(--accent); color: #052e16; }
    .btn-primary:hover { background: #34d399; }
    .btn-blue { background: var(--blue); border-color: var(--blue); color: #082f49; }
    .btn-blue:hover { background: #38bdf8; }
    .btn-outline { background: transparent; border-color: #4b5563; color: var(--text); }
    .btn-outline:hover { background: #374151; }
    .container { max-width: 1440px; margin: 0 auto; padding: 24px 28px; }

    /* KPIs */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
      gap: 14px;
      margin-bottom: 22px;
    }
    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }
    .kpi-label { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); }
    .kpi-value { font-size: 1.75rem; font-weight: 800; margin-top: 4px; color: var(--accent); }
    .kpi-sub { font-size: 0.78rem; color: var(--text-muted); margin-top: 2px; }

    /* Breakdown panels */
    .analytics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .panel {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
    }
    .panel h3 { font-size: 0.95rem; margin-bottom: 12px; color: #e5e7eb; display: flex; justify-content: space-between; }
    .bar-row { margin-bottom: 9px; font-size: 0.82rem; cursor: pointer; }
    .bar-row:hover .bar-title { color: var(--accent); }
    .bar-header { display: flex; justify-content: space-between; margin-bottom: 3px; }
    .bar-track { height: 7px; background: #1f2937; border-radius: 4px; overflow: hidden; }
    .bar-fill { height: 100%; background: var(--accent); border-radius: 4px; }
    .bar-fill.ebm { background: var(--blue); }
    .bar-fill.scope { background: var(--amber); }

    /* Filters bar */
    .filters-bar {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 20px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      align-items: end;
    }
    .filter-group label { display: block; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px; }
    .filter-group select, .filter-group input { width: 100%; }

    /* Publication Cards */
    .pub-list { display: flex; flex-direction: column; gap: 16px; }
    .pub-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      transition: border-color 0.15s;
    }
    .pub-card:hover { border-color: #374151; }
    .pub-top { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
    .badges { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
    .badge {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 3px 9px;
      border-radius: 999px;
      background: #1f2937;
      border: 1px solid #374151;
    }
    .badge-score { background: rgba(16, 185, 129, 0.15); border-color: var(--accent); color: #6ee7b7; }
    .badge-grade { background: rgba(14, 165, 233, 0.15); border-color: var(--blue); color: #7dd3fc; }
    .badge-ebm { background: rgba(168, 85, 247, 0.15); border-color: var(--purple); color: #d8b4fe; }
    .badge-scope { background: rgba(245, 158, 11, 0.15); border-color: var(--amber); color: #fcd34d; }
    .badge-foundational { background: rgba(244, 63, 94, 0.18); border-color: var(--rose); color: #fda4af; }
    .pub-title { font-size: 1.12rem; font-weight: 700; color: #f9fafb; margin-bottom: 6px; }
    .pub-title a { color: inherit; text-decoration: none; }
    .pub-title a:hover { color: var(--accent); }
    .pub-meta { font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px; }
    .pub-summary {
      font-size: 0.9rem;
      color: #d1d5db;
      background: rgba(255, 255, 255, 0.02);
      border-left: 3px solid var(--blue);
      padding: 10px 14px;
      border-radius: 0 8px 8px 0;
      margin-bottom: 10px;
    }
    .pub-takeaway {
      font-size: 0.9rem;
      color: #ecfdf5;
      background: rgba(16, 185, 129, 0.09);
      border-left: 3px solid var(--accent);
      padding: 10px 14px;
      border-radius: 0 8px 8px 0;
      margin-bottom: 10px;
    }
    .pub-footer {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      font-size: 0.8rem;
      color: var(--text-muted);
      padding-top: 8px;
      border-top: 1px solid #1f2937;
    }
    .pub-links a {
      color: var(--blue);
      text-decoration: none;
      margin-right: 12px;
      font-weight: 600;
    }
    .pub-links a:hover { text-decoration: underline; }

    /* Modal Nouveau Sujet */
    .modal-backdrop {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.72);
      z-index: 50;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .modal-backdrop.active { display: flex; }
    .modal {
      background: var(--bg-card);
      border: 1px solid #374151;
      border-radius: 14px;
      max-width: 580px;
      width: 100%;
      padding: 24px;
    }
    .modal h2 { font-size: 1.2rem; margin-bottom: 8px; }
    .modal p { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px; }
    .form-row { margin-bottom: 14px; }
    .form-row label { display: block; font-size: 0.8rem; color: #d1d5db; margin-bottom: 4px; }
    .form-row input, .form-row textarea, .form-row select { width: 100%; }
    .status-toast {
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #065f46;
      border: 1px solid var(--accent);
      color: #ecfdf5;
      padding: 12px 18px;
      border-radius: 10px;
      font-size: 0.88rem;
      display: none;
      z-index: 100;
      box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-badge">🔬</div>
      <div>
        <h1>myKairn SciWatch — Moteur d'Audit & Veille Scientifique 6D</h1>
        <p id="topicSubtitle">Coaching & Accompagnement d'Athlètes Tous Niveaux en Trail Running</p>
      </div>
    </div>
    <div class="toolbar">
      <select id="profileSelect" onchange="onProfileChange()"></select>
      <button class="btn-outline" onclick="openNewTopicModal()">➕ Nouveau Sujet à Auditer</button>
      <button class="btn-primary" id="btnAudit" onclick="triggerRun('audit')">🚀 Lancer Audit État de l'Art</button>
      <button class="btn-blue" id="btnWatch" onclick="triggerRun('watch')">🔄 Veille Incrémentale (30j)</button>
      <button class="btn-outline" onclick="exportData('markdown')">📄 Rapport MD</button>
      <button class="btn-outline" onclick="exportData('csv')">📊 CSV</button>
      <button class="btn-outline" onclick="exportData('mykairn')">⚡ Pack myKairn JSON</button>
    </div>
  </header>

  <div class="container">
    <!-- KPIs 6D -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Publications Classées</div>
        <div class="kpi-value" id="kpiTotal">0</div>
        <div class="kpi-sub">Dédoublonnées (PubMed, OpenAlex, S2, Crossref)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Score Global Moyen (6D)</div>
        <div class="kpi-value" id="kpiOverall">0</div>
        <div class="kpi-sub">Sur 100 (Qualité + Portée + Fraîcheur)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Qualité Méthodologique</div>
        <div class="kpi-value" id="kpiQuality">0</div>
        <div class="kpi-sub">Pyramide EBM, échantillon n, citations</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Portée & Terrain</div>
        <div class="kpi-value" id="kpiScope">0</div>
        <div class="kpi-sub">Applicabilité coaching & tous niveaux</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Haut Niveau EBM (Tiers 1-2)</div>
        <div class="kpi-value" id="kpiTier12">0</div>
        <div class="kpi-sub">Méta-analyses, Revues syst., RCT, Consensus</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Articles Fondateurs / OA</div>
        <div class="kpi-value" id="kpiFoundational">0</div>
        <div class="kpi-sub" id="kpiOaSub">Classiques très cités & Open Access</div>
      </div>
    </div>

    <!-- Panneaux de répartition 6D -->
    <div class="analytics-grid">
      <div class="panel">
        <h3><span>📌 Répartition par Thème (D2)</span><span style="font-size:0.76rem;color:var(--text-muted)">Cliquer pour filtrer</span></h3>
        <div id="barsTheme"></div>
      </div>
      <div class="panel">
        <h3><span>🏛️ Pyramide EBM — Type de Publi (D1)</span><span style="font-size:0.76rem;color:var(--text-muted)">Niveau de preuve</span></h3>
        <div id="barsType"></div>
      </div>
      <div class="panel">
        <h3><span>🏃 Portée & Niveau d'Athlète Cible (D4)</span><span style="font-size:0.76rem;color:var(--text-muted)">Public étudié</span></h3>
        <div id="barsAthlete"></div>
      </div>
    </div>

    <!-- Barre de filtres multi-critères -->
    <div class="filters-bar">
      <div class="filter-group">
        <label>Recherche plein texte (Titre, Résumé, Takeaway)</label>
        <input type="text" id="filterSearch" placeholder="ex: polarized, downhill, gut training, HRV..." oninput="loadPublications()" />
      </div>
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
          <option value="A+">Grade A+ (>= 82)</option>
          <option value="A">Grade A (>= 72)</option>
          <option value="B">Grade B (>= 60)</option>
          <option value="C">Grade C (>= 48)</option>
        </select>
      </div>
      <div class="filter-group">
        <label>Trier par</label>
        <select id="filterSort" onchange="loadPublications()">
          <option value="overall_score">Score Global 6D (Décroissant)</option>
          <option value="quality_score">Qualité Méthodologique (/100)</option>
          <option value="scope_score">Portée Terrain & Coaching (/100)</option>
          <option value="publication_date">Date de publication (Plus récents)</option>
          <option value="citation_count">Nombre de citations</option>
          <option value="evidence_tier">Pyramide EBM (Niveau 1A d'abord)</option>
        </select>
      </div>
      <div class="filter-group">
        <button class="btn-outline" style="width:100%;justify-content:center;" onclick="resetFilters()">Réinitialiser</button>
      </div>
    </div>

    <!-- Liste des publications -->
    <div id="pubList" class="pub-list"></div>
  </div>

  <!-- Modal Création d'un Nouveau Sujet d'Audit Modulaire -->
  <div class="modal-backdrop" id="newTopicModal">
    <div class="modal">
      <h2>➕ Créer & Auditer un Nouveau Sujet Scientifique</h2>
      <p>Le moteur génère automatiquement un profil déclaratif YAML multi-sources (PubMed, OpenAlex, Semantic Scholar, Crossref) adapté à n'importe quel sujet.</p>
      <div class="form-row">
        <label>Titre du sujet à auditer *</label>
        <input type="text" id="newTopicName" placeholder="ex: Sommeil, VFC et Récupération en Ultra-Endurance" />
      </div>
      <div class="form-row">
        <label>Mots-clés de recherche (en anglais pour interroger les bases internationales, séparés par des virgules) *</label>
        <input type="text" id="newTopicKeywords" placeholder="ex: heart rate variability, sleep deprivation, endurance recovery, overreaching" />
      </div>
      <div class="form-row">
        <label>Domaine scientifique</label>
        <input type="text" id="newTopicDomain" value="sports_science" />
      </div>
      <div class="form-row">
        <label>Année de départ de l'audit historique</label>
        <input type="number" id="newTopicYear" value="2016" min="1990" max="2026" />
      </div>
      <div class="form-row">
        <label>Description / Objectif de l'audit</label>
        <textarea id="newTopicDesc" rows="2" placeholder="Audit de la littérature scientifique et recommandations pratiques..."></textarea>
      </div>
      <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:16px;">
        <button class="btn-outline" onclick="closeNewTopicModal()">Annuler</button>
        <button class="btn-primary" onclick="createNewTopic(true)">Créer & Lancer l'Audit</button>
      </div>
    </div>
  </div>

  <div class="status-toast" id="toast"></div>

  <script>
    let currentTopic = "trail_running_coaching";

    function showToast(msg) {
      const t = document.getElementById("toast");
      t.textContent = msg;
      t.style.display = "block";
      setTimeout(() => { t.style.display = "none"; }, 4500);
    }

    async function initDashboard() {
      const res = await fetch("/api/profiles");
      const data = await res.json();
      const sel = document.getElementById("profileSelect");
      sel.innerHTML = "";
      (data.profiles || []).forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.slug;
        opt.textContent = p.name;
        opt.dataset.desc = p.description || "";
        if (p.slug === currentTopic) opt.selected = true;
        sel.appendChild(opt);
      });
      if (data.profiles && data.profiles.length > 0 && !data.profiles.some(p => p.slug === currentTopic)) {
        currentTopic = data.profiles[0].slug;
      }
      await refreshAll();
    }

    async function onProfileChange() {
      const sel = document.getElementById("profileSelect");
      currentTopic = sel.value;
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
            <div class="bar-header"><span class="bar-title">${th.label}</span><span><strong>${th.count}</strong> (${th.avg_score}/100)</span></div>
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
            <div class="bar-header"><span class="bar-title">${pt.label} <em style="color:var(--text-muted)">(${pt.evidence_level})</em></span><span><strong>${pt.count}</strong></span></div>
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
            <div class="bar-header"><span class="bar-title">${al.label}</span><span><strong>${al.count}</strong> (${pct}%)</span></div>
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

    function resetFilters(reload = true) {
      document.getElementById("filterSearch").value = "";
      document.getElementById("filterTheme").value = "";
      document.getElementById("filterType").value = "";
      document.getElementById("filterAthlete").value = "";
      document.getElementById("filterGrade").value = "";
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
        sort: document.getElementById("filterSort").value,
        limit: "120"
      });
      const res = await fetch(`/api/publications?${params.toString()}`);
      const data = await res.json();
      const box = document.getElementById("pubList");
      const pubs = data.publications || [];

      if (pubs.length === 0) {
        box.innerHTML = `<div class="panel" style="text-align:center;padding:36px;">
          <h3>Aucune publication trouvée pour ces filtres</h3>
          <p style="color:var(--text-muted);margin-top:8px;">Cliquez sur « 🚀 Lancer Audit État de l'Art » en haut à droite pour interroger PubMed, OpenAlex, Semantic Scholar et Crossref.</p>
        </div>`;
        return;
      }

      box.innerHTML = pubs.map((p, idx) => {
        const authors = (p.authors || []).slice(0, 4).join(", ") + ((p.authors || []).length > 4 ? " et al." : "");
        const foundationalBadge = p.is_foundational ? `<span class="badge badge-foundational">🏆 Article Fondateur (${p.citation_count} cit.)</span>` : "";
        const oaBadge = p.is_open_access ? `<span class="badge">🔓 Open Access</span>` : "";
        const sampleBadge = p.sample_size ? `<span class="badge">👥 n = ${p.sample_size}</span>` : "";

        return `
          <div class="pub-card">
            <div class="pub-top">
              <div class="badges">
                <span class="badge badge-score">Score Global : ${p.overall_score}/100</span>
                <span class="badge badge-grade">Qualité : ${p.quality_score}/100 (Grade ${p.quality_grade})</span>
                <span class="badge badge-scope">Portée : ${p.scope_score}/100 • ${p.athlete_level_label}</span>
                <span class="badge badge-ebm">${p.publication_type_label} (${p.evidence_level})</span>
                ${sampleBadge}
                ${foundationalBadge}
                ${oaBadge}
              </div>
              <span class="badge">${p.publication_date}</span>
            </div>
            <div class="pub-title">
              <a href="${p.url || '#'}" target="_blank" rel="noopener">${idx + 1}. ${p.title}</a>
            </div>
            <div class="pub-meta">
              <strong>${p.primary_theme_label}</strong> • ${authors} — <em>${p.journal}</em> (${p.publication_year}) • Cadre : ${p.study_setting} • Citations : ${p.citation_count}
            </div>
            <div class="pub-summary">
              <strong>🔬 Synthèse :</strong> ${p.summary_fr}
            </div>
            <div class="pub-takeaway">
              <strong>💡 Takeaway Coaching :</strong> ${p.practical_takeaway}
            </div>
            <div class="pub-footer">
              <div class="pub-links">
                ${p.url ? `<a href="${p.url}" target="_blank">🔗 Source</a>` : ""}
                ${p.doi ? `<a href="https://doi.org/${p.doi}" target="_blank">DOI: ${p.doi}</a>` : ""}
                ${p.pmid ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${p.pmid}/" target="_blank">PubMed: ${p.pmid}</a>` : ""}
                ${p.pdf_url ? `<a href="${p.pdf_url}" target="_blank">📄 PDF Texte Intégral</a>` : ""}
              </div>
              <div>⚠️ <em>${p.limitations}</em> • Sources : ${(p.sources || []).join(", ")}</div>
            </div>
          </div>
        `;
      }).join("");
    }

    async function triggerRun(mode) {
      const btn = document.getElementById(mode === "audit" ? "btnAudit" : "btnWatch");
      const origText = btn.textContent;
      btn.disabled = true;
      btn.textContent = "⏳ Collecte & Scoring 6D en cours...";
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
      const kwRaw = document.getElementById("newTopicKeywords").value.trim();
      const domain = document.getElementById("newTopicDomain").value.trim() || "general_science";
      const startYear = parseInt(document.getElementById("newTopicYear").value || "2016", 10);
      const desc = document.getElementById("newTopicDesc").value.trim();

      if (!name || !kwRaw) {
        showToast("Veuillez renseigner un titre et des mots-clés.");
        return;
      }
      const keywords = kwRaw.split(",").map(s => s.trim()).filter(Boolean);
      const res = await fetch("/api/profiles", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          name: name,
          keywords: keywords,
          domain: domain,
          audit_start_year: startYear,
          description: desc
        })
      });
      const data = await res.json();
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
