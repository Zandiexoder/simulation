const API = window.location.origin.replace(':8080', ':8000');

const app = {
  state: {}, health: null, map: null,
  nations: [], cities: [], agents: [], events: [], intel: [], timeline: [],
  orgs: [], outlets: [], issues: [], cultures: [], descriptions: {},
  overlay: 'terrain', inspectorTab: 'world', dockTab: 'events',
  selectedCity: null, selectedNation: null, selectedAgent: null, selectedOrg: null, selectedIssue: null, selectedEvent: null,
  narrativeCoverage: [], milestones: [], diagnostics: null, runDiag: null, replayStatus: null, scenarios: [], lastKnown: null,
};

const terrainColor = { ocean:'#1d3049', plains:'#335f48', forest:'#2b4f3f', desert:'#7a5a2a', mountain:'#586473', tundra:'#8398a6' };

async function api(path, method='GET', body) {
  const res = await fetch(`${API}${path}`, { method, headers: {'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined });
  return await res.json();
}

function classifyService(v){ return v === 'ok' ? 'ok' : (v === 'down' ? 'down' : 'degraded'); }
function value(v){ return `<span class="v">${v}</span>`; }

function renderTopbar() {
  const h = app.health || {services: {api: 'down', naming: 'down', gm: 'down'}};
  const s = app.state || {};
  const st = document.getElementById('statusCluster');
  st.innerHTML = `
    <span class="chip">tick ${value(s.tick ?? '-')}</span>
    <span class="chip">mode ${value(s.running ? 'live' : 'paused')}</span>
    <span class="chip">replay ${value(s.replay_mode ? 'on' : 'off')}</span>
    <span class="chip ${classifyService(h.services.api)}">api ${value(h.services.api)}</span>
    <span class="chip ${classifyService(h.services.naming)}">naming ${value(h.services.naming)}</span>
    <span class="chip ${classifyService(h.services.gm)}">gm ${value(h.services.gm)}</span>
    <span class="chip">overlay ${value(app.overlay)}</span>
    <span class="chip">orgs ${value(app.orgs.length)}</span>
    <span class="chip">news ${value(app.issues.length)}</span>
  `;
  const op = document.getElementById('overlayPill');
  if (op) op.textContent = app.overlay;
}

function metricForCell(c) {
  if (app.overlay === 'terrain') return terrainColor[c.biome] || '#2a3948';
  if (app.overlay === 'population') return c.population_capacity > 120 ? '#3ecb88' : (c.population_capacity > 80 ? '#e0a33a' : '#2d4257');
  if (app.overlay === 'migration') return c.habitability > 0.75 ? '#41a9ff' : (c.habitability > 0.5 ? '#355c7b' : '#1f2d3a');
  if (app.overlay === 'trade') return c.resource_richness > 0.7 ? '#62b9ff' : '#24384a';
  if (app.overlay === 'legitimacy') return c.culture_region === 'industrial' ? '#3ecb88' : '#9c8c57';
  if (app.overlay === 'intel') return c.culture_region === 'frontier' ? '#a482ff' : '#38495e';
  if (app.overlay === 'conflict') return c.biome === 'mountain' ? '#d95858' : '#394a5b';
  if (app.overlay === 'climate') return c.biome === 'desert' ? '#e0a33a' : '#34506a';
  if (app.overlay === 'resources') return c.resource_richness > 0.6 ? '#4fbeff' : '#294155';
  if (app.overlay === 'urban') return c.population_capacity > 150 ? '#f0b24a' : '#30495d';
  return '#2a3948';
}

function buildMapLegend(degraded = false) {
  const legend = document.getElementById('mapLegend');
  legend.innerHTML = `
    <div><b>Overlay</b>: ${app.overlay}</div>
    <div style="margin-top:4px;color:var(--txt-2)">Confirmed: solid fill · Uncertainty: dashed boundary · Stale intel: amber tags</div>
    <div style="margin-top:4px;color:var(--txt-2)">Organizations: ${app.orgs.length} · News issues: ${app.issues.length}</div>
    ${degraded ? '<div class="tag warn" style="margin-top:6px">degraded data mode</div>' : ''}
  `;
}

function paintMap(mapData, {ghost = false} = {}) {
  const host = document.getElementById('mapCanvas');
  host.innerHTML = '';
  const width = mapData.width;
  for (let y = 0; y < mapData.height; y++) {
    const row = document.createElement('div'); row.className = 'map-grid-row';
    for (let x = 0; x < width; x++) {
      const c = mapData.cells[y * width + x];
      const el = document.createElement('div');
      el.className = 'map-cell';
      if (app.overlay === 'intel' && c.culture_region === 'frontier') el.classList.add('uncertain');
      el.style.background = metricForCell(c);
      if (ghost) el.style.opacity = '0.55';
      el.title = `${c.biome} | ${c.culture_region} | hab ${c.habitability.toFixed(2)} | resource ${c.resource_richness.toFixed(2)}`;
      row.appendChild(el);
    }
    host.appendChild(row);
  }

  (app.cities || []).slice(0, 80).forEach(city => {
    const marker = document.createElement('div');
    marker.className = 'map-city-marker' + (ghost ? ' ghost' : '') + (app.selectedCity?.id === city.id ? ' selected' : '');
    marker.style.left = `${12 + city.x * 13}px`;
    marker.style.top = `${58 + city.y * 13}px`;
    marker.title = `${city.name || 'city'} (${city.culture || 'unknown'})`;
    marker.onclick = () => { app.selectedCity = city; app.inspectorTab = 'city'; renderInspector(); renderMap(); };
    host.appendChild(marker);
  });
}

function renderMapDegraded() {
  const host = document.getElementById('mapCanvas');
  if (app.lastKnown?.map) {
    paintMap(app.lastKnown.map, {ghost: true});
    const card = document.createElement('div');
    card.className = 'map-degraded-card';
    card.innerHTML = `
      <div class="notice error"><b>Backend link degraded</b></div>
      <div style="margin-top:8px;color:var(--txt-1)">Rendering cached last-known-state. Data may be stale; continue triage via timeline/intel/news tabs.</div>
      <div style="margin-top:6px" class="tag warn">cached tick ${app.lastKnown.state?.tick ?? '-'}</div>
    `;
    host.appendChild(card);
  } else {
    host.innerHTML = '<div class="map-empty">No live or cached map available. Continue with service diagnostics and replay checks.</div>';
  }
  buildMapLegend(true);
}

function renderMap() {
  if (!app.map || !app.map.cells?.length) return renderMapDegraded();
  paintMap(app.map);
  buildMapLegend(false);
}

function riskTags() {
  const risks = [];
  const overlays = app.state.overlay_summary || {};
  if ((overlays.migration || 0) > 0) risks.push('<span class="tag warn">migration pressure</span>');
  if ((overlays.conflict || 0) > 0) risks.push('<span class="tag alert">conflict incidents</span>');
  if ((overlays.intel || 0) > 10) risks.push('<span class="tag">intel saturation</span>');
  if ((overlays.organizations || 0) > 0) risks.push('<span class="tag stable">institutional coordination</span>');
  return risks.join(' ') || '<span class="tag stable">no critical alerts</span>';
}

function inspectorFallback() {
  const h = app.health?.services || {api: 'down', naming: 'down', gm: 'down'};
  const cache = app.lastKnown;
  return `
    <div class="card"><h4>Degraded Operations Mode</h4><div class="notice warn">Live feed interrupted. Inspector switched to structured fallback.</div></div>
    <div class="card"><h4>Service Health</h4><span class="chip ${classifyService(h.api)}">api ${h.api}</span> <span class="chip ${classifyService(h.naming)}">naming ${h.naming}</span> <span class="chip ${classifyService(h.gm)}">gm ${h.gm}</span></div>
    <div class="card"><h4>Cached Summary</h4><div class="kv"><span>cached tick</span><span class="val">${cache?.state?.tick ?? '-'}</span><span>cached nations</span><span class="val">${cache?.nations?.length ?? 0}</span><span>cached cities</span><span class="val">${cache?.cities?.length ?? 0}</span><span>cached issues</span><span class="val">${cache?.issues?.length ?? 0}</span></div></div>
    <div class="card"><h4>Operator Guidance</h4><div class="tag warn">use timeline</div><div class="tag">review intel staleness</div><div class="tag">check diplomacy/org tab</div></div>
  `;
}

function inspectorWorld() {
  const cultureCount = app.cultures?.length || 0;
  return `<div class="card"><h4>World Brief</h4><div class="metric-row"><span>nations</span><span>${app.nations.length}</span></div><div class="metric-row"><span>cities</span><span>${app.cities.length}</span></div><div class="metric-row"><span>cultures</span><span>${cultureCount}</span></div></div><div class="card"><h4>Culture Definitions</h4><pre>${JSON.stringify((app.cultures||[]).slice(0,4), null, 2)}</pre></div>`;
}

function inspectorNation() {
  const n = app.selectedNation || app.nations[0];
  if (!n) return '<div class="card">No nation selected.</div>';
  const d = app.descriptions[`nation:${n.id}`]?.description || 'Description loading...';
  return `<div class="card"><h4>${n.name}</h4><div class="metric-row"><span>culture</span><span>${n.culture}</span></div><pre>${JSON.stringify(n, null, 2)}</pre></div><div class="card"><h4>AI Description</h4><div>${d}</div></div>`;
}

function inspectorCity() {
  const c = app.selectedCity || app.cities[0];
  if (!c) return '<div class="card">No city selected.</div>';
  const d = app.descriptions[`city:${c.id}`]?.description || 'Description loading...';
  return `<div class="card"><h4>${c.name}</h4><div class="metric-row"><span>culture</span><span>${c.culture}</span></div><pre>${JSON.stringify(c, null, 2)}</pre></div><div class="card"><h4>AI Description</h4><div>${d}</div></div>`;
}

function inspectorAgent() {
  const a = app.selectedAgent || app.agents[0];
  if (!a) return '<div class="card">No agent selected.</div>';
  const d = app.descriptions[`agent:${a.id}`]?.description || 'Description loading...';
  return `<div class="card"><h4>${a.name}</h4><div class="metric-row"><span>culture</span><span>${a.culture}</span></div><pre>${JSON.stringify(a, null, 2)}</pre></div><div class="card"><h4>AI Description</h4><div>${d}</div></div>`;
}

function inspectorOrg() {
  const o = app.selectedOrg || app.orgs[0];
  if (!o) return '<div class="card">No international organization formed yet.</div>';
  return `<div class="card"><h4>${o.name}</h4><div class="kv"><span>Type</span><span class="val">${o.org_type}</span><span>Members</span><span class="val">${o.members.length}</span><span>Legitimacy</span><span class="val">${o.legitimacy.toFixed(2)}</span><span>Enforcement</span><span class="val">${o.enforcement_capacity.toFixed(2)}</span><span>Effectiveness</span><span class="val">${o.institutional_effectiveness.toFixed(2)}</span><span>Status</span><span class="val">${o.status || 'active'}</span></div></div><div class="card"><h4>Influence</h4><pre>${JSON.stringify(o.influence || {}, null, 2)}</pre><h4>Factions</h4><pre>${JSON.stringify(o.internal_factions || o.voting_blocs || [], null, 2)}</pre></div><div class="card"><h4>Charter</h4>${o.charter}</div>`;
}

function inspectorNews() {
  const i = app.selectedIssue || app.issues[0];
  if (!i) return '<div class="card">No newspaper issues in archive yet.</div>';
  return `<div class="card"><h4>${i.outlet_id} · issue ${i.issue_id}</h4><div class="kv"><span>Tick</span><span class="val">${i.publication_tick}</span><span>Scope</span><span class="val">${i.region_scope}</span><span>event</span><span class="val">${i.event_id || '-'}</span></div></div><div class="card"><h4>Headlines</h4>${i.headlines.map(h=>`<div class="event-item">${h}</div>`).join('')}</div><div class="card"><h4>Narrative Variants</h4>${(i.narrative_variants||[]).slice(0,8).map(v=>`<div class="event-item"><div class="event-head"><span>${v.outlet}</span><span class="tag">${v.bias}</span></div><div>${v.headline}</div><div class="tag">conf ${v.confidence}</div></div>`).join('')}</div><div class="card"><h4>Framing</h4>${(i.ideological_framing_tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}</div>`;
}

function renderInspector(degraded = false) {
  const root = document.getElementById('inspectorBody');
  if (degraded) { root.innerHTML = inspectorFallback(); return; }
  if (app.inspectorTab === 'world') root.innerHTML = inspectorWorld();
  if (app.inspectorTab === 'nation') root.innerHTML = inspectorNation();
  if (app.inspectorTab === 'city') root.innerHTML = inspectorCity();
  if (app.inspectorTab === 'agent') root.innerHTML = inspectorAgent();
  if (app.inspectorTab === 'org') root.innerHTML = inspectorOrg();
  if (app.inspectorTab === 'news') root.innerHTML = inspectorNews();
}

function renderEventsColumn(items) {
  if (!items.length) return '<div class="notice info">No events available for current filters.</div>';
  return items.map(e => `<div class="event-item" onclick="app.selectedEvent=app.events.find(x=>x.id==='${e.id}')||null; renderDock();"><div class="event-head"><span>${e.type || 'event'}</span><span>tick ${e.tick ?? '-'}</span></div>${e.milestone ? '<span class="tag alert">milestone</span>' : ''}<div>${e.message || ''}</div>${(e.causal_chain||[]).length ? `<div class="notice">causality: ${(e.causal_chain||[]).map(c=>c.type).join(' → ')}</div>` : ''}</div>`).join('');
}

function renderDock() {
  const root = document.getElementById('dockContent');
  document.querySelectorAll('.dock-tab').forEach(el => el.classList.toggle('active', el.dataset.tab === app.dockTab));

  if (app.dockTab === 'events') {
    const se = app.selectedEvent;
    root.innerHTML = `<div class="panel-scroll">${renderEventsColumn(app.events.slice(-36).reverse())}</div><div class="panel-scroll"><div class="metric-row"><span>Total events</span><span>${app.events.length}</span></div><div class="metric-row"><span>Migration</span><span>${app.events.filter(e=>e.type==='migration').length}</span></div><div class="metric-row"><span>Conflict</span><span>${app.events.filter(e=>e.type==='security_incident').length}</span></div><div class="metric-row"><span>Milestones</span><span>${app.events.filter(e=>e.milestone).length}</span></div></div><div class="panel-scroll"><div class="notice info">Click an event to inspect causality and cross-links.</div>${se ? `<pre>${JSON.stringify({id: se.id, type: se.type, causal_chain: se.causal_chain || [], causal_confidence: se.causal_confidence || 0}, null, 2)}</pre>` : ''}</div>`;
    return;
  }
  if (app.dockTab === 'alerts') {
    const alerts = app.events.filter(e => ['coup_risk','security_incident','urban_decline','org_dissolved'].includes(e.type)).slice(-30).reverse();
    root.innerHTML = `<div class="panel-scroll">${alerts.length ? alerts.map(a=>`<div class="event-item"><div class="event-head"><span>${a.type}</span><span class="tag alert">priority</span></div>${a.message || ''}</div>`).join('') : '<div class="notice info">No prioritized alerts currently.</div>'}</div><div class="panel-scroll"><div class="notice warn">Confidence-aware sort active.</div></div><div class="panel-scroll"><div class="metric-row"><span>alert count</span><span>${alerts.length}</span></div></div>`;
    return;
  }
  if (app.dockTab === 'metrics') {
    const m = app.state.metrics || {};
    root.innerHTML = `<div class="panel-scroll">${Object.entries(m).map(([k,v])=>`<div class="metric-row"><span>${k}</span><span>${Number(v).toFixed ? Number(v).toFixed(3) : v}</span></div>`).join('')}</div><div class="panel-scroll"><h4>Diagnostics</h4><pre>${JSON.stringify(app.diagnostics || {}, null, 2)}</pre><h4>Run</h4><pre>${JSON.stringify(app.runDiag || {}, null, 2)}</pre><h4>Replay</h4><pre>${JSON.stringify(app.replayStatus || {}, null, 2)}</pre></div><div class="panel-scroll"><h4>Scenario</h4>${(app.scenarios||[]).slice(0,8).map(s=>`<button class="btn btn-sm" style="margin:2px" onclick="loadScenario('${s.scenario_id}')">${s.scenario_id}</button>`).join('')}<h4>Overlay summary</h4><pre>${JSON.stringify(app.state.overlay_summary || {}, null, 2)}</pre></div>`;
    return;
  }
  if (app.dockTab === 'intel' || app.dockTab === 'press') {
    root.innerHTML = `<div class="panel-scroll">${app.intel.slice(-25).reverse().map(r=>`<div class="event-item"><div class="event-head"><span>${r.target_scope}</span><span>${r.secrecy_level}</span></div><div class="kv"><span>reliability</span><span class="val">${r.source_reliability}</span><span>confidence</span><span class="val">${r.confidence_score}</span><span>staleness</span><span class="val">${r.staleness}</span></div></div>`).join('') || '<div class="notice info">No intelligence reports yet.</div>'}</div><div class="panel-scroll"><h4>Outlets</h4>${app.outlets.slice(0,18).map(o=>`<div class="event-item"><div class="event-head"><span>${o.name}</span><span>${o.nation_alignment}</span></div><span class="tag">cred ${o.credibility}</span><span class="tag warn">sens ${o.sensationalism}</span></div>`).join('')}</div><div class="panel-scroll"><div class="tag">reported</div><div class="tag warn">suspected</div><div class="tag alert">unconfirmed</div></div>`;
    return;
  }
  if (app.dockTab === 'timeline') {
    root.innerHTML = `<div class="panel-scroll">${app.timeline.slice(-30).reverse().map(t=>`<div class="event-item"><div class="event-head"><span>${t.type}</span><span>t${t.tick}</span></div>${t.message || ''}</div>`).join('') || '<div class="notice info">Timeline empty</div>'}</div><div class="panel-scroll"><div class="metric-row"><span>Replay mode</span><span>${app.state.replay_mode}</span></div><button class="btn btn-sm" onclick="toggleReplay(true)">Enable replay</button><button class="btn btn-sm" onclick="toggleReplay(false)">Disable replay</button></div><div class="panel-scroll"><h4>Compare snapshots</h4><button class="btn btn-sm ghost" onclick="compareSnapshots()">Compare latest pair</button><pre id="compareOut">Awaiting compare request.</pre></div>`;
    return;
  }
  if (app.dockTab === 'conflict') {
    const incidents = app.events.filter(e => e.type === 'security_incident').slice(-30).reverse();
    root.innerHTML = `<div class="panel-scroll">${incidents.length ? incidents.map(i=>`<div class="event-item"><div class="event-head"><span>incident</span><span class="tag alert">risk ${Number(i.risk || 0).toFixed(2)}</span></div>${i.message || ''}</div>`).join('') : '<div class="notice info">No incidents currently.</div>'}</div><div class="panel-scroll"><div class="notice warn">Force posture estimate uncertain.</div></div><div class="panel-scroll"><div class="metric-row"><span>Incident count</span><span>${incidents.length}</span></div></div>`;
    return;
  }
  if (app.dockTab === 'diplomacy' || app.dockTab === 'organizations') {
    root.innerHTML = `<div class="panel-scroll">${app.orgs.map(o=>`<div class="event-item" onclick="app.selectedOrg=app.orgs.find(x=>x.org_id==='${o.org_id}'); app.inspectorTab='org'; renderInspector();"><div class="event-head"><span>${o.name}</span><span>${o.org_type}</span></div><div class="kv"><span>members</span><span class="val">${o.members.length}</span><span>effectiveness</span><span class="val">${Number(o.institutional_effectiveness).toFixed(2)}</span></div></div>`).join('') || '<div class="notice info">No organizations emerged yet.</div>'}</div><div class="panel-scroll"><div class="notice info">Emergence driven by crises, diplomacy, and coordination needs.</div></div><div class="panel-scroll"><div class="metric-row"><span>Org count</span><span>${app.orgs.length}</span></div></div>`;
    return;
  }
  if (app.dockTab === 'news') {
    root.innerHTML = `<div class="panel-scroll">${app.issues.slice(-30).reverse().map(i=>`<div class="event-item" onclick="app.selectedIssue=app.issues.find(x=>x.issue_id==='${i.issue_id}'); app.inspectorTab='news'; loadNarratives(i.event_id); renderInspector();"><div class="event-head"><span>${i.outlet_id}</span><span>t${i.publication_tick}</span></div>${(i.headlines||[]).slice(0,2).map(h=>`<div>${h}</div>`).join('')}</div>`).join('') || '<div class="notice info">No issues yet.</div>'}</div><div class="panel-scroll"><button class="btn btn-sm" onclick="generateNews()">Generate on demand</button><div class="notice">Compare outlet framing by selecting issues.</div></div><div class="panel-scroll"><h4>Narrative comparison</h4>${(app.narrativeCoverage||[]).slice(0,10).map(v=>`<div class="event-item"><div class="event-head"><span>${v.outlet}</span><span class="tag">${v.bias}</span></div><div>${v.headline}</div><div class="tag">conf ${v.confidence}</div></div>`).join('') || '<div class="notice info">Select an issue to compare narratives.</div>'}</div>`;
    return;
  }
  if (app.dockTab === 'gm') {
    root.innerHTML = `<div class="panel-scroll"><div class="card"><h4>Briefing Types</h4><span class="tag">strategic</span><span class="tag warn">unrest</span><span class="tag">intel mismatch</span><span class="tag stable">status</span></div><div class="card"><h4>Quick Actions</h4><button class="btn btn-sm" onclick="quickGM('summarize world')">world</button> <button class="btn btn-sm" onclick="quickGM('explain selected nation')">nation</button> <button class="btn btn-sm" onclick="quickGM('explain selected city')">city</button> <button class="btn btn-sm warn" onclick="quickGM('explain migration surge')">migration</button> <button class="btn btn-sm warn" onclick="quickGM('explain unrest')">unrest</button> <button class="btn btn-sm" onclick="quickGM('compare press framing')">press framing</button></div></div><div class="panel-scroll"><div class="card"><h4>Analyst Query</h4><input id="gmInput" class="overlay-select" style="width:100%" placeholder="Ask briefing assistant" /><button class="btn primary" style="margin-top:8px" onclick="askGM()">Generate briefing</button></div></div><div class="panel-scroll"><div class="card"><h4>Briefing Output</h4><div class="tag">confidence: medium</div><div class="tag warn">uncertainty-aware</div><pre id="gmOut">No briefing generated yet.</pre></div></div>`;
    return;
  }
}

async function compareSnapshots() {
  const snaps = app.state.snapshots || [];
  const out = document.getElementById('compareOut');
  if (!out) return;
  if (snaps.length < 2) { out.innerText = 'Need at least 2 snapshots.'; return; }
  const a = snaps[snaps.length - 2].tick;
  const b = snaps[snaps.length - 1].tick;
  const data = await api(`/history/compare?tick_a=${a}&tick_b=${b}`);
  out.innerText = JSON.stringify(data, null, 2);
}

async function askGM() {
  const input = document.getElementById('gmInput');
  const prompt = input?.value || 'generate briefing';
  const out = await api('/gm/chat', 'POST', {prompt, mode: 'intel'});
  const target = document.getElementById('gmOut');
  if (target) target.innerText = JSON.stringify(out, null, 2);
}

async function loadScenario(id) {
  await api('/scenarios/load', 'POST', {scenario_id: id});
  await refresh();
}

async function loadNarratives(eventId) {
  if (!eventId) { app.narrativeCoverage = []; return; }
  const out = await api(`/media/narratives/${eventId}`);
  app.narrativeCoverage = out.coverage || [];
}

async function generateNews() {
  await api('/media/generate', 'POST', {scope: 'world', trigger: 'on_demand'});
  await refresh();
}

function quickGM(prompt){ const input = document.getElementById('gmInput'); if (input) input.value = prompt; askGM(); }
async function toggleReplay(enabled){ await api('/simulation/replay-mode', 'POST', {enabled}); await refresh(); }

function bindUI() {
  document.getElementById('overlaySelect').addEventListener('change', (e) => {
    app.overlay = e.target.value;
    renderMap();
    renderTopbar();
  });
  document.querySelectorAll('[data-inspector]').forEach(btn => btn.addEventListener('click', () => { app.inspectorTab = btn.dataset.inspector; renderInspector(); }));
  document.querySelectorAll('.dock-tab').forEach(btn => btn.addEventListener('click', () => { app.dockTab = btn.dataset.tab; renderDock(); }));
}

async function refresh() {
  try {
    const health = await api('/health');
    const state = await api('/simulation/state');
    const [map, nations, cities, agents, events, intel, timeline, orgs, issues, outlets, cultures, milestones, diagnostics, runDiag, replayStatus, scenarios] = await Promise.all([
      api('/world/map'),
      api('/world/nations'),
      api('/world/cities'),
      api('/world/agents'),
      api('/events'),
      api('/intel/reports'),
      api(`/history/timeline?start_tick=0&end_tick=${(state?.tick || 0) + 2000}`),
      api('/diplomacy/organizations'),
      api('/media/issues?limit=120'),
      api('/media/outlets'),
      api('/world/cultures'),
      api('/history/milestones'),
      api('/diagnostics/performance'),
      api('/diagnostics/run'),
      api('/replay/status'),
      api('/scenarios'),
    ]);

    app.health = health; app.state = state; app.map = map; app.nations = nations; app.cities = cities; app.agents = agents;
    app.events = events; app.intel = intel; app.timeline = timeline; app.orgs = orgs; app.issues = issues; app.outlets = outlets; app.cultures = cultures.items || []; app.milestones = milestones || []; app.diagnostics = diagnostics; app.runDiag = runDiag; app.replayStatus = replayStatus; app.scenarios = scenarios || [];

    const sampleNation = nations[0]; const sampleCity = cities[0]; const sampleAgent = agents[0];
    const descReq = [];
    if (sampleNation) descReq.push(api(`/descriptions/nation/${sampleNation.id}`));
    if (sampleCity) descReq.push(api(`/descriptions/city/${sampleCity.id}`));
    if (sampleAgent) descReq.push(api(`/descriptions/agent/${sampleAgent.id}`));
    const descs = await Promise.all(descReq);
    descs.forEach((d)=>{ if (d?.role && d?.entity_id) app.descriptions[`${d.role === 'person' ? 'agent' : d.role}:${d.entity_id}`]=d; });

    app.lastKnown = { map, state, nations, cities, agents, events, intel, timeline, orgs, issues, outlets, cultures, ts: Date.now() };

    renderTopbar(); renderMap(); renderInspector(false); renderDock();
  } catch (err) {
    app.health = app.health || {services: {api: 'down', naming: 'down', gm: 'down'}};
    if (app.health?.services) app.health.services.api = 'down';
    renderTopbar(); renderMapDegraded(); renderInspector(true); renderDock();
  }
}

window.uiAction = async function(action) {
  if (action === 'start') await api('/simulation/start', 'POST');
  if (action === 'pause') await api('/simulation/pause', 'POST');
  if (action === 'step') await api('/simulation/step', 'POST', {ticks: 1});
  if (action === 'speed') await api('/simulation/speed', 'POST', {speed: 4});
  if (action === 'replayOn') await api('/simulation/replay-mode', 'POST', {enabled: true});
  if (action === 'replayOff') await api('/simulation/replay-mode', 'POST', {enabled: false});
  if (action === 'dock') document.querySelector('.app-shell').classList.toggle('dock-collapsed');
  await refresh();
};

bindUI();
refresh();
setInterval(refresh, 8000);
