// Do zero aos 5 km — painel estático (GitHub Pages)
const $app = document.getElementById("app");
const state = { plan: null, acts: { sessions: {}, recent: [] }, pushed: {} };

const STATUS_LABEL = { feito: "Feito", adaptado: "Adaptado", pulado: "Pulado", pendente: "" };
const WD_FIXED = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

async function getJSON(path, fallback) {
  try {
    const r = await fetch(path + "?v=" + Date.now());
    return r.ok ? await r.json() : fallback;
  } catch { return fallback; }
}

const todayISO = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};
const fmtDate = (iso) => {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}`;
};
const mmss = (sec) => {
  const m = Math.floor(sec / 60), s = Math.round(sec % 60);
  return s ? `${m}:${String(s).padStart(2, "0")}` : `${m} min`;
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const result = (id) => state.acts.sessions?.[id] || { status: id >= todayISO() ? "pendente" : "pulado" };

function flatten(steps) {
  const out = [];
  for (const s of steps) {
    if (s.type === "repeat") for (let i = 0; i < s.n; i++) out.push(...s.steps);
    else out.push(s);
  }
  return out;
}

function nextSession() {
  const t = todayISO();
  return state.plan.sessions.find((s) => s.date >= t && !["feito", "adaptado"].includes(result(s.id).status))
    || state.plan.sessions.at(-1);
}

// ---------- Visão geral ----------
function weeklyChart() {
  const weeks = {};
  for (const s of state.plan.sessions) {
    const w = (weeks[s.week] ||= { plan: 0, done: 0 });
    w.plan += s.run_minutes;
    const r = result(s.id);
    if (r.status === "feito" || r.status === "adaptado") w.done += Math.min(r.minutes ?? 0, s.total_minutes) * (s.run_minutes / Math.max(s.total_minutes, 1));
  }
  const keys = Object.keys(weeks).map(Number).sort((a, b) => a - b);
  const max = Math.max(...keys.map((k) => weeks[k].plan)) * 1.1;
  const W = 700, H = 180, pad = 26, bw = (W - pad) / keys.length;
  let bars = "";
  keys.forEach((k, i) => {
    const x = pad + i * bw + bw * 0.15, w = bw * 0.7;
    const hp = (weeks[k].plan / max) * (H - 30), hd = (weeks[k].done / max) * (H - 30);
    bars += `<rect x="${x}" y="${H - 20 - hp}" width="${w}" height="${hp}" rx="3" fill="var(--ease)"/>`;
    if (hd > 0) bars += `<rect x="${x}" y="${H - 20 - hd}" width="${w}" height="${hd}" rx="3" fill="var(--run)"/>`;
    bars += `<text x="${x + w / 2}" y="${H - 5}" text-anchor="middle">${k}</text>`;
    bars += `<text x="${x + w / 2}" y="${H - 24 - hp}" text-anchor="middle">${Math.round(weeks[k].plan)}</text>`;
  });
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Minutos de corrida por semana">${bars}
    <text x="0" y="12">min</text></svg>
    <div class="legend"><span><i style="background:var(--ease)"></i>Planejado</span><span><i style="background:var(--run)"></i>Feito (estimado)</span></div>`;
}

function renderHome() {
  const P = state.plan, t = todayISO();
  const runs = P.sessions.filter((s) => s.kind === "run");
  const done = P.sessions.filter((s) => ["feito", "adaptado"].includes(result(s.id).status));
  const km = done.reduce((a, s) => a + (result(s.id).km || 0), 0);
  const nx = nextSession();
  const nr = result(nx.id);

  const byWeek = {};
  P.sessions.forEach((s) => (byWeek[s.week] ||= []).push(s));
  const fixed = Object.entries(P.weekly || {}).map(([d, a]) => `${d}: ${a}`).join(" · ");

  const weeksHTML = Object.entries(byWeek).map(([w, list]) => {
    const first = list[0].date, last = list.at(-1).date;
    const cells = list.map((s) => {
      const r = result(s.id);
      return `<a class="sess ${s.date === t ? "today" : ""}" href="#/s/${s.id}">
        <div class="d">${s.weekday} ${fmtDate(s.date)}</div>
        <div class="n">${esc(s.title)}</div>
        ${STATUS_LABEL[r.status] ? `<span class="badge ${r.status}">${STATUS_LABEL[r.status]}</span>` : ""}
      </a>`;
    }).join("");
    return `<div class="week"><div class="wk">S${w}<small>${fmtDate(first)}–${fmtDate(last)}</small></div><div class="days">${cells}</div></div>`;
  }).join("");

  $app.innerHTML = `
    <h1>${esc(P.name)}</h1>
    <div class="muted">${done.length} de ${P.sessions.length} sessões feitas · meta: 5 km em ${fmtDate(P.sessions.at(-1).date)}</div>
    <div class="progress"><i style="width:${(done.length / P.sessions.length) * 100}%"></i></div>

    <h2>Próxima sessão</h2>
    <a class="card hero" href="#/s/${nx.id}">
      <div class="kicker">${nx.date === t ? "Hoje" : `${nx.weekday} ${fmtDate(nx.date)}`} · semana ${nx.week}</div>
      <div class="t">${esc(nx.title)}</div>
      <div class="muted">${nx.total_minutes} min no total${nx.pace ? ` · pace ${nx.pace.fast}–${nx.pace.slow}/km` : ""}${P.hr_cap ? ` · FC até ${P.hr_cap}` : ""}</div>
      ${state.pushed[nx.id] ? `<div class="pill-row"><span class="pill garmin">No relógio</span></div>` : ""}
    </a>

    <div class="stats">
      <div class="stat"><div class="num">${done.length}</div><div class="lbl">sessões feitas</div></div>
      <div class="stat"><div class="num">${km.toFixed(1)}</div><div class="lbl">km registrados</div></div>
      <div class="stat"><div class="num">${runs.length}</div><div class="lbl">corridas no plano</div></div>
      <div class="stat"><div class="num">${P.hr_cap ?? "—"}</div><div class="lbl">teto de FC (bpm)</div></div>
    </div>

    <h2>Minutos de corrida por semana</h2>
    <div class="card">${weeklyChart()}</div>

    <h2>Semanas</h2>
    <div class="fixed">${esc(fixed)}</div>
    <div class="card">${weeksHTML}</div>`;
  window.scrollTo(0, 0);
}

// ---------- Sessão ----------
function stepRow(s, pace, hr) {
  const isRun = s.type === "run";
  const dur = s.meters ? `${(s.meters / 1000).toLocaleString("pt-BR")} km` : mmss(s.sec);
  const sub = isRun
    ? [pace && `pace ${pace.fast}–${pace.slow}/km`, hr && `FC até ${hr}`].filter(Boolean).join(" · ")
    : "caminhada rápida, respiração tranquila";
  return `<li><span class="sw ${s.type}"></span><div><div>${esc(s.label)}</div><div class="sub">${sub}</div></div><div class="dur">${dur}</div></li>`;
}

function renderSession(id) {
  const P = state.plan;
  const i = P.sessions.findIndex((s) => s.id === id);
  if (i < 0) { $app.innerHTML = `<p class="pad">Sessão não encontrada. <a href="#/">Voltar</a></p>`; return; }
  const s = P.sessions[i], r = result(s.id), hr = P.hr_cap;
  const flat = flatten(s.steps);
  const total = flat.reduce((a, x) => a + x.sec, 0);

  const bar = flat.map((x) => `<i class="${x.type}" style="flex:${x.sec}" title="${esc(x.label)} ${mmss(x.sec)}"></i>`).join("");
  const steps = s.steps.map((st) => st.type === "repeat"
    ? `<div class="repeat"><div class="repeat-h">Repita ${st.n}x</div><ul class="steps">${st.steps.map((c) => stepRow(c, s.pace, hr)).join("")}</ul></div>`
    : `<ul class="steps">${stepRow(st, s.pace, hr)}</ul>`).join("");

  const actual = r.activityId ? `
    <h2>Realizado</h2>
    <div class="card">
      <span class="badge ${r.status}">${STATUS_LABEL[r.status]}</span>
      <div class="stats">
        <div class="stat"><div class="num">${r.minutes}</div><div class="lbl">min (${r.pct_planned}% do plano)</div></div>
        <div class="stat"><div class="num">${r.km}</div><div class="lbl">km</div></div>
        <div class="stat"><div class="num">${r.pace ?? "—"}</div><div class="lbl">pace médio /km</div></div>
        <div class="stat"><div class="num">${r.avgHR ?? "—"}</div><div class="lbl">FC média${r.maxHR ? ` · máx ${r.maxHR}` : ""}</div></div>
      </div>
      ${hr && r.maxHR > hr ? `<p class="muted">A FC máxima passou do teto (${hr}). Na próxima, comece os blocos mais devagar.</p>` : ""}
    </div>` : (r.status === "pulado" ? `<h2>Realizado</h2><div class="card muted">Nenhuma atividade registrada nesse dia. Siga o plano, sem compensar.</div>` : "");

  const prev = P.sessions[i - 1], next = P.sessions[i + 1];
  $app.innerHTML = `
    <a href="#/" class="muted" style="text-decoration:none">← Plano</a>
    <div class="muted" style="margin-top:12px">${s.weekday} ${fmtDate(s.date)} · semana ${s.week}</div>
    <h1>${esc(s.title)}</h1>
    <div class="pill-row">
      <span class="pill">${mmss(total)} no total</span>
      ${s.run_minutes ? `<span class="pill">${s.run_minutes} min correndo</span>` : ""}
      ${s.pace ? `<span class="pill">pace ${s.pace.fast}–${s.pace.slow}/km</span>` : ""}
      ${hr && s.kind === "run" ? `<span class="pill">FC até ${hr} bpm</span>` : ""}
      ${state.pushed[s.id] ? `<span class="pill garmin">Enviado ao Garmin</span>` : (s.kind === "run" ? `<span class="pill">Vai para o Garmin até 7 dias antes</span>` : `<span class="pill">Caminhada: não vai para o relógio</span>`)}
    </div>

    <div class="bar">${bar}</div>
    <div class="axis"><span>0</span><span>${mmss(total)}</span></div>

    <h2>Passo a passo</h2>
    <div class="card">${steps}</div>

    ${s.note ? `<h2>Nota</h2><div class="card">${esc(s.note)}</div>` : ""}
    ${actual}

    <h2>Lembretes</h2>
    <div class="card"><ul class="rules">
      <li>Corra no ritmo de conversa. O pace é estimativa; a FC manda.</li>
      <li>Se a FC passar do teto, caminhe até baixar uns 10 batimentos e volte.</li>
      <li>Dor que piora ou muda a passada: pare e troque por caminhada.</li>
      <li>Calor: antes das 7h ou depois das 18h, com água.</li>
    </ul></div>

    <div class="pager">
      ${prev ? `<a href="#/s/${prev.id}">← ${prev.weekday} ${fmtDate(prev.date)}</a>` : "<span></span>"}
      ${next ? `<a href="#/s/${next.id}">${next.weekday} ${fmtDate(next.date)} →</a>` : "<span></span>"}
    </div>`;
  window.scrollTo(0, 0);
}

function route() {
  const h = location.hash;
  if (h.startsWith("#/s/")) return renderSession(h.slice(4));
  if (h === "#/hoje") return renderSession(nextSession().id);
  renderHome();
}

// ---------- Login (dados criptografados com a senha do site) ----------
const KEY_STORE = "c5k_key";
const b64d = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const b64e = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)));
const store = {
  get() { try { return JSON.parse(localStorage.getItem(KEY_STORE) || sessionStorage.getItem(KEY_STORE)); } catch { return null; } },
  set(v, remember) { try { (remember ? localStorage : sessionStorage).setItem(KEY_STORE, JSON.stringify(v)); } catch {} },
  clear() { try { localStorage.removeItem(KEY_STORE); sessionStorage.removeItem(KEY_STORE); } catch {} },
};

async function deriveKey(password, vault) {
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt: b64d(vault.salt), iterations: vault.iterations },
    base, { name: "AES-GCM", length: 256 }, true, ["decrypt"]);
}

async function openVault(vault, key) {
  const out = {};
  for (const [name, f] of Object.entries(vault.files)) {
    const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: b64d(f.iv) }, key, b64d(f.ct));
    out[name] = JSON.parse(new TextDecoder().decode(pt));
  }
  return out;
}

async function tryStoredKey(vault) {
  const saved = store.get();
  if (!saved || saved.salt !== vault.salt) return null;
  try {
    const key = await crypto.subtle.importKey("raw", b64d(saved.key), "AES-GCM", false, ["decrypt"]);
    return await openVault(vault, key);
  } catch { store.clear(); return null; }
}

function loginForm(vault) {
  return new Promise((resolve) => {
    document.getElementById("foot").textContent = "";
    $app.innerHTML = `
      <form class="card login" id="login">
        <h1>Entrar</h1>
        <p class="muted">Seus treinos e sua frequência cardíaca ficam criptografados. Digite a senha do painel.</p>
        <input type="password" id="pw" autocomplete="current-password" placeholder="Senha" required>
        <label class="remember"><input type="checkbox" id="remember" checked> Lembrar neste aparelho</label>
        <button type="submit">Entrar</button>
        <p class="err" id="err"></p>
      </form>`;
    const $f = document.getElementById("login"), $err = document.getElementById("err");
    document.getElementById("pw").focus();
    $f.addEventListener("submit", async (e) => {
      e.preventDefault();
      $err.textContent = "Abrindo…";
      try {
        const key = await deriveKey(document.getElementById("pw").value, vault);
        const files = await openVault(vault, key);
        store.set({ salt: vault.salt, key: b64e(await crypto.subtle.exportKey("raw", key)) },
          document.getElementById("remember").checked);
        resolve(files);
      } catch { $err.textContent = "Senha incorreta."; }
    });
  });
}

async function loadData() {
  const vault = await getJSON("data/vault.json", null);
  if (!vault) {  // site publicado sem senha
    return {
      "plan.json": await getJSON("data/plan.json", null),
      "activities.json": await getJSON("data/activities.json", state.acts),
      "pushed.json": await getJSON("data/pushed.json", {}),
    };
  }
  document.getElementById("logout").hidden = false;
  return (await tryStoredKey(vault)) || (await loginForm(vault));
}

document.getElementById("logout").addEventListener("click", (e) => {
  e.preventDefault(); store.clear(); location.hash = "#/"; location.reload();
});

(async function init() {
  const files = await loadData();
  state.plan = files["plan.json"];
  if (!state.plan) { $app.innerHTML = `<p class="pad">Não encontrei os dados do plano.</p>`; return; }
  state.acts = files["activities.json"] && files["activities.json"].sessions ? files["activities.json"] : state.acts;
  state.pushed = files["pushed.json"] || {};
  document.getElementById("foot").textContent = state.acts.updated
    ? `Dados do Garmin atualizados em ${state.acts.updated.replace("T", " às ")}`
    : "Ainda sem dados do Garmin.";
  window.addEventListener("hashchange", route);
  route();
})();
