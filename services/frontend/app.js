const API = window.location.origin.replace(':8080', ':8000');

const app = {
  state: {},
  health: null,
  map: null,
  nations: [],
  cities: [],
  agents: [],
  events: [],
  intel: [],
  timeline: [],
  overlay: 'terrain',
  inspectorTab: 'world',
  dockTab: 'events',
  selectedCity: null,
  selectedNation: null,
  selectedAgent: null,
};

const terrainColor = { ocean:'#1d3049', plains:'#335f48', forest:'#2b4f3f', desert:'#7a5a2a', mountain:'#586473', tundra:'#8398a6' };

async function api(path, method='GET', body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {'Content-Type': 'application/json'},
    body: body ? JSON.stringify(body) : undefined,
  });
  return await res.json();
}

function classifyService(v){ return v === 'ok' ? 'ok' : (v === 'down' ? 'down' : 'degraded'); }

function renderTopbar() {
  const h = app.health || {services: {api: 'down', naming: 'down', gm: 'down'}};
  const s = app.state || {};
  const st = document.getElementById('statusCluster');
  st.innerHTML = `
    <span class="chip">tick ${s.tick ?? '-'}</span>
    <span class="chip">mode ${s.running ? 'live' : 'paused'}</span>
    <span class="chip">speed ${(s.running ? 'active' : 'idle')}</span>
    <span class="chip">replay ${s.replay_mode ? 'on' : 'off'}</span>
    <span class="chip ${classifyService(h.services.api)}">api ${h.services.api}</span>
    <span class="chip ${classifyService(h.services.naming)}">naming ${h.services.naming}</span>
    <span class="chip ${classifyService(h.services.gm)}">gm ${h.services.gm}</span>
    <span class="chip">overlay ${app.overlay}</span>
  `;
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

function buildMapLegend() {
  const legend = document.getElementById('mapLegend');
  legend.innerHTML = `
    <div><b>Overlay</b>: ${app.overlay}</div>
    <div style="margin-top:4px;color:var(--txt-2)">Confirmed data: solid fill · Uncertainty: dashed boundary · Stale intel: amber tags</div>
  `;
}

function renderMap() {
  const host = document.getElementById('mapCanvas');
  if (!app.map || !app.map.cells?.length) {
    host.innerHTML = `<div class="map-empty">Map data unavailable. Verify backend health and replay mode.</div>`;
    return;
  }

  const width = app.map.width;
  const cells = app.map.cells;
  host.innerHTML = '';

  for (let y = 0; y < app.map.height; y++) {
    const row = document.createElement('div');
    row.className = 'map-grid-row';
    for (let x = 0; x < width; x++) {
      const c = cells[y * width + x];
      const el = document.createElement('div');
      el.className = 'map-cell';
      if (app.overlay === 'intel' && c.culture_region === 'frontier') el.classList.add('uncertain');
      el.style.background = metricForCell(c);
      el.title = `${c.biome} | ${c.culture_region} | hab ${c.habitability.toFixed(2)} | resource ${c.resource_richness.toFixed(2)}`;
      row.appendChild(el);
    }
    host.appendChild(row);
  }

  app.cities.slice(0, 60).forEach(city => {
    const marker = document.createElement('div');
    marker.className = 'map-city-marker' + (app.selectedCity?.id === city.id ? ' selected' : '');
    marker.style.left = `${12 + city.x * 13}px`;
    marker.style.top = `${48 + city.y * 13}px`;
    marker.title = `${city.name} (${city.culture})`;
    marker.onclick = () => {
      app.selectedCity = city;
      app.inspectorTab = 'city';
      renderInspector();
      renderMap();
    };
    host.appendChild(marker);
  });

  buildMapLegend();
}

function riskTags() {
  const risks = [];
  const overlays = app.state.overlay_summary || {};
  if ((overlays.migration || 0) > 0) risks.push('<span class="tag warn">migration pressure</span>');
  if ((overlays.conflict || 0) > 0) risks.push('<span class="tag alert">conflict incidents</span>');
  if ((overlays.intel || 0) > 10) risks.push('<span class="tag">intel saturation</span>');
  return risks.join(' ') || '<span class="tag stable">no critical alerts</span>';
}

function inspectorWorld() {
  const pop = app.cities.reduce((a,c)=>a+(c.population||0),0);
  const instability = app.nations.filter(n => (n.coup_risk_estimate || 0) > 0.5).length;
  const uncertain = app.nations.filter(n => (n.intel_confidence || 0) < 0.4).length;
  return `
    <div class="card"><h4>Global Operating Picture</h4>
      <div class="kv">
        <span>Total population</span><span>${pop.toLocaleString()}</span>
        <span>Active nations</span><span>${app.nations.length}</span>
        <span>Total cities</span><span>${app.cities.length}</span>
        <span>Conflict hotspots</span><span>${app.events.filter(e=>e.type==='security_incident').length}</span>
        <span>Top instability regions</span><span>${instability}</span>
        <span>High uncertainty regions</span><span>${uncertain}</span>
      </div>
    </div>
    <div class="card"><h4>Top Global Risks</h4>${riskTags()}</div>
    <div class="card"><h4>Recent Major Events</h4>${app.events.slice(-6).map(e=>`<div class="event-item"><div class="event-head"><span>${e.type}</span><span>t${e.tick}</span></div>${e.message || ''}</div>`).join('') || '<div class="skeleton">No events yet</div>'}</div>
  `;
}

function inspectorNation() {
  const n = app.selectedNation || app.nations[0];
  if (!n) return '<div class="card">No nation selected.</div>';
  return `
    <div class="card"><h4>${n.name}</h4><div class="kv">
      <span>Government</span><span>${n.government_type}</span>
      <span>Legitimacy</span><span>${n.legitimacy}</span>
      <span>Coup risk estimate</span><span>${n.coup_risk_estimate}</span>
      <span>Intel confidence</span><span>${n.intel_confidence}</span>
    </div></div>
    <div class="card"><h4>Migration / Stability</h4>${riskTags()}</div>
    <div class="card"><h4>Recent Incidents</h4>${app.events.filter(e=>e.nation_id===n.id).slice(-5).map(e=>`<div class="event-item">${e.type}: ${e.message||''}</div>`).join('') || '<div class="skeleton">No nation incidents available</div>'}</div>
  `;
}

function inspectorCity() {
  const c = app.selectedCity || app.cities[0];
  if (!c) return '<div class="card">No city selected.</div>';
  return `
    <div class="card"><h4>${c.name}</h4><div class="kv">
      <span>Population</span><span>${c.population}</span>
      <span>Growth trend</span><span>${c.growth_trend}</span>
      <span>Housing pressure</span><span>${c.housing_pressure}</span>
      <span>Crime pressure</span><span>${c.crime_pressure}</span>
      <span>Culture</span><span>${c.culture}</span>
    </div></div>
    <div class="card"><h4>Strategic Signals</h4><span class="tag ${c.crime_pressure > 0.6 ? 'alert' : 'stable'}">crime ${c.crime_pressure}</span><span class="tag ${c.housing_pressure > 0.6 ? 'warn' : ''}">housing ${c.housing_pressure}</span></div>
  `;
}

function inspectorAgent() {
  const a = app.selectedAgent || app.agents[0];
  if (!a) return '<div class="card">No agent selected.</div>';
  return `
    <div class="card"><h4>${a.name}</h4><div class="kv">
      <span>City</span><span>${a.city_id}</span>
      <span>Culture</span><span>${a.culture}</span>
      <span>Tier</span><span>${a.tier}</span>
      <span>Profile scope</span><span>Observed / reported only</span>
    </div></div>
    <div class="card"><h4>Trust / Suspicion (visible indicators)</h4><span class="tag">trust: medium</span><span class="tag warn">suspicion: low</span></div>
  `;
}

function renderInspector() {
  const root = document.getElementById('inspectorBody');
  if (app.inspectorTab === 'world') root.innerHTML = inspectorWorld();
  if (app.inspectorTab === 'nation') root.innerHTML = inspectorNation();
  if (app.inspectorTab === 'city') root.innerHTML = inspectorCity();
  if (app.inspectorTab === 'agent') root.innerHTML = inspectorAgent();
}

function renderEventsColumn(items) {
  if (!items.length) return '<div class="notice info">No events available for current filters.</div>';
  return items.map(e => `
    <div class="event-item">
      <div class="event-head"><span>${e.type || 'event'}</span><span>tick ${e.tick ?? '-'}</span></div>
      <div>${e.message || ''}</div>
    </div>
  `).join('');
}

function renderDock() {
  const root = document.getElementById('dockContent');
  document.querySelectorAll('.dock-tab').forEach(el => el.classList.toggle('active', el.dataset.tab === app.dockTab));

  if (app.dockTab === 'events') {
    root.innerHTML = `
      <div class="panel-scroll">${renderEventsColumn(app.events.slice(-30).reverse())}</div>
      <div class="panel-scroll"><div class="notice">Jump any event to map focus (coming next).</div></div>
      <div class="panel-scroll"><div class="metric-row"><span>Total events</span><span>${app.events.length}</span></div><div class="metric-row"><span>Migration</span><span>${app.events.filter(e=>e.type==='migration').length}</span></div></div>
    `;
    return;
  }
  if (app.dockTab === 'alerts') {
    const alerts = app.events.filter(e => ['coup_risk','security_incident','urban_decline'].includes(e.type)).slice(-30).reverse();
    root.innerHTML = `
      <div class="panel-scroll">${alerts.length ? alerts.map(a=>`<div class="event-item"><div class="event-head"><span>${a.type}</span><span class="tag alert">high</span></div>${a.message || ''}</div>`).join('') : '<div class="notice info">No prioritized alerts currently.</div>'}</div>
      <div class="panel-scroll"><div class="notice warn">Confidence-aware alert sorting enabled.</div></div>
      <div class="panel-scroll"><button class="btn ghost">Dismiss low confidence</button></div>
    `;
    return;
  }
  if (app.dockTab === 'metrics') {
    const m = app.state.metrics || {};
    root.innerHTML = `
      <div class="panel-scroll">${Object.entries(m).map(([k,v])=>`<div class="metric-row"><span>${k}</span><span>${Number(v).toFixed ? Number(v).toFixed(3) : v}</span></div>`).join('')}</div>
      <div class="panel-scroll"><h4>Global Trend Group A</h4><div class="spark"></div><h4>Trend Group B</h4><div class="spark"></div></div>
      <div class="panel-scroll"><h4>Overlay Summary</h4><pre>${JSON.stringify(app.state.overlay_summary || {}, null, 2)}</pre></div>
    `;
    return;
  }
  if (app.dockTab === 'intel') {
    root.innerHTML = `
      <div class="panel-scroll">${app.intel.slice(-25).reverse().map(r=>`<div class="event-item"><div class="event-head"><span>${r.target_scope}</span><span>${r.secrecy_level}</span></div><div class="kv"><span>reliability</span><span>${r.source_reliability}</span><span>confidence</span><span>${r.confidence_score}</span><span>staleness</span><span>${r.staleness}</span></div></div>`).join('') || '<div class="notice info">No intelligence reports yet.</div>'}</div>
      <div class="panel-scroll"><div class="notice">Use filters by nation/topic in next increment.</div></div>
      <div class="panel-scroll"><div class="tag">reported</div><div class="tag warn">suspected</div><div class="tag alert">unconfirmed</div></div>
    `;
    return;
  }
  if (app.dockTab === 'timeline') {
    root.innerHTML = `
      <div class="panel-scroll">${app.timeline.slice(-30).reverse().map(t=>`<div class="event-item"><div class="event-head"><span>${t.type}</span><span>t${t.tick}</span></div>${t.message || ''}</div>`).join('') || '<div class="notice info">Timeline empty</div>'}</div>
      <div class="panel-scroll"><div class="metric-row"><span>Replay mode</span><span>${app.state.replay_mode}</span></div><button class="btn" onclick="toggleReplay(true)">Enable replay</button><button class="btn" onclick="toggleReplay(false)">Disable replay</button></div>
      <div class="panel-scroll"><h4>Compare snapshots</h4><button class="btn ghost" onclick="compareSnapshots()">Compare latest pair</button><pre id="compareOut">Awaiting compare request.</pre></div>
    `;
    return;
  }
  if (app.dockTab === 'conflict') {
    const incidents = app.events.filter(e => e.type === 'security_incident').slice(-30).reverse();
    root.innerHTML = `
      <div class="panel-scroll">${incidents.length ? incidents.map(i=>`<div class="event-item"><div class="event-head"><span>incident</span><span class="tag alert">risk ${Number(i.risk || 0).toFixed(2)}</span></div>${i.message || ''}</div>`).join('') : '<div class="notice info">No incidents currently.</div>'}</div>
      <div class="panel-scroll"><div class="notice warn">Force posture estimation uncertain.</div></div>
      <div class="panel-scroll"><div class="metric-row"><span>Incident count</span><span>${incidents.length}</span></div></div>
    `;
    return;
  }
  if (app.dockTab === 'gm') {
    root.innerHTML = `
      <div class="panel-scroll"><div class="card"><h4>GM Briefings</h4><div class="notice info">Use quick actions for focused intelligence analysis.</div><div style="margin-top:6px"><button class="btn" onclick="quickGM('summarize world')">summarize world</button> <button class="btn" onclick="quickGM('explain selected nation')">selected nation</button> <button class="btn" onclick="quickGM('explain selected city')">selected city</button><br/><button class="btn warn" onclick="quickGM('explain migration surge')">migration surge</button> <button class="btn warn" onclick="quickGM('explain unrest')">unrest</button> <button class="btn" onclick="quickGM('explain intel mismatch')">intel mismatch</button></div></div></div>
      <div class="panel-scroll"><input id="gmInput" class="btn" style="width:100%;text-align:left" placeholder="Ask briefing assistant" /><button class="btn primary" style="margin-top:8px" onclick="askGM()">Generate briefing</button></div>
      <div class="panel-scroll"><pre id="gmOut">No briefing generated yet.</pre></div>
    `;
    return;
  }
}

async function compareSnapshots() {
  const snaps = app.state.snapshots || [];
  if (snaps.length < 2) {
    document.getElementById('compareOut').innerText = 'Need at least 2 snapshots.';
    return;
  }
  const a = snaps[snaps.length - 2].tick;
  const b = snaps[snaps.length - 1].tick;
  const data = await api(`/history/compare?tick_a=${a}&tick_b=${b}`);
  document.getElementById('compareOut').innerText = JSON.stringify(data, null, 2);
}

async function askGM() {
  const input = document.getElementById('gmInput');
  const prompt = input?.value || 'generate briefing';
  const out = await api('/gm/chat', 'POST', {prompt, mode: 'intel'});
  const target = document.getElementById('gmOut');
  if (target) target.innerText = JSON.stringify(out, null, 2);
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
    [app.health, app.state, app.map, app.nations, app.cities, app.agents, app.events, app.intel, app.timeline] = await Promise.all([
      api('/health'),
      api('/simulation/state'),
      api('/world/map'),
      api('/world/nations'),
      api('/world/cities'),
      api('/world/agents'),
      api('/events'),
      api('/intel/reports'),
      api(`/history/timeline?start_tick=0&end_tick=${(app.state?.tick || 0) + 2000}`),
    ]);
    renderTopbar();
    renderMap();
    renderInspector();
    renderDock();
  } catch (err) {
    document.getElementById('mapCanvas').innerHTML = `<div class="notice error">Backend unreachable. Check API status and network route.</div>`;
    document.getElementById('inspectorBody').innerHTML = `<div class="notice error">Inspector unavailable during backend outage.</div>`;
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
