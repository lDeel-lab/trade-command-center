/* Trade journal + real-time signal alerts.
 *
 * Runs the SAME engine code that ships in dashboard.html (extracted and
 * executed in a sandbox), so server-side picks always match what the
 * dashboard shows. Each 15-min cycle it:
 *   1. loads crypto live from Bybit + every universe JSON from site/data/
 *   2. collects all picks with conviction >= 70
 *   3. opens journal entries for new picks (and Telegram-alerts them)
 *   4. walks fresh candles to close open entries on SL/TP with a
 *      thirds scale-out model (1/3 off at TP1/2/3, stop to BE after TP1)
 *   5. writes state/journal.json (committed) + site/data/journal.json (site)
 *
 * Usage: node journal.js [--mock]   (mock = synthetic candles, no Telegram)
 */

const fs = require("fs");
const vm = require("vm");

const MOCK = process.argv.includes("--mock");
const MIN_CONV = 70;
const MAX_ALERTS = 6;
const MAX_REVIEWS = 8;      // AI reviews per cycle (cost control)
const EXPIRE_DAYS = 14;
const JOURNAL = "state/journal.json";

/* ---------------- AI reviewer (optional — needs ANTHROPIC_API_KEY) -------- */
async function aiReview(pick, ctx) {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key || MOCK) return null;
  const model = process.env.AI_MODEL || "claude-haiku-4-5";
  const useSearch = process.env.AI_WEB_SEARCH === "1";
  const prompt =
`You are the independent risk reviewer for a systematic trading signal service.
A technical system produced this signal. Your job is to find reasons it might be WRONG, then verdict it.

SIGNAL: ${pick.dir === 1 ? "LONG" : "SHORT"} ${pick.name} (${pick.cls}) — conviction ${pick.conv}/100
Type: ${pick.type} · Strategy: ${pick.strat} · Signal timeframe: ${pick.tfKey}
Plan: entry ${pick.entry} · stop ${pick.sl} · TP1 ${pick.tp1} · TP2 ${pick.tp2} · TP3 ${pick.tp3}
Technical context: ${ctx.tech}
Fundamentals: ${ctx.fund}
Recent tagged headlines: ${ctx.news || "none captured"}
${useSearch ? `You MAY use web search (max 2 searches) to check for fresh news, earnings dates, or events about ${pick.name}.` : ""}
Consider: imminent binary events (earnings, CPI/FOMC, court rulings), news contradicting the direction, signs the technical setup is an artifact (weekend/stale data, illiquid gap), over-extension, and anything idiosyncratic you know about this asset.

Reply with ONLY a JSON object, no other text:
{"verdict":"CONFIRM"|"CAUTION"|"VETO","adjusted_conviction":<0-100>,"summary":"<one sentence>","risks":["<risk1>","<risk2>"]}
VETO only for a clear disqualifier. CAUTION when real risks exist but the trade is defensible. CONFIRM when nothing material contradicts it.`;
  try {
    const body = {model, max_tokens: 800,
      messages: [{role: "user", content: prompt}]};
    if (useSearch) body.tools = [{type: "web_search_20250305", name: "web_search", max_uses: 2}];
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {"x-api-key": key, "anthropic-version": "2023-06-01",
                "content-type": "application/json"},
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) { console.error("AI review HTTP", r.status, JSON.stringify(j).slice(0, 300)); return null; }
    const text = (j.content || []).filter(b => b.type === "text").map(b => b.text).join("\n");
    const m = text.match(/\{[\s\S]*\}/);
    if (!m) return null;
    const out = JSON.parse(m[0]);
    if (!["CONFIRM", "CAUTION", "VETO"].includes(out.verdict)) return null;
    return {verdict: out.verdict, conv2: out.adjusted_conviction,
      summary: String(out.summary || "").slice(0, 300),
      risks: (out.risks || []).slice(0, 4).map(x => String(x).slice(0, 160))};
  } catch (e) { console.error("AI review:", e.message); return null; }
}

/* ---------------- dummy DOM so the dashboard script runs headless -------- */
function dummyEl() {
  const el = {
    style: {setProperty() {}}, dataset: {}, classList: {add() {}, remove() {}},
    children: [], textContent: "", className: "", hidden: false, checked: true,
    value: "", title: "", type: "", tabIndex: 0,
    appendChild(c) { this.children.push(c); return c; },
    setAttribute() {}, getAttribute() { return null; }, addEventListener() {},
    querySelector() { return dummyEl(); }, focus() {}, scrollTo() {},
    getBoundingClientRect() { return {width: 100, height: 100, left: 0, top: 0}; },
  };
  return el;
}
const dummyDoc = {
  querySelector: () => dummyEl(), querySelectorAll: () => [],
  createElement: () => dummyEl(), createElementNS: () => dummyEl(),
  createTextNode: () => ({}), documentElement: dummyEl(),
};

/* fetch wrapper: relative "data/x.json" -> local file; absolute -> network */
async function wrappedFetch(url, opts) {
  if (typeof url === "string" && !/^https?:/.test(url)) {
    const path = "site/" + url.replace(/^\.?\//, "");
    if (!fs.existsSync(path)) return {ok: false, status: 404, json: async () => ({})};
    return {ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(path, "utf8"))};
  }
  return fetch(url, opts);
}

async function main() {
  /* ---- boot the dashboard engine ---- */
  const html = fs.readFileSync("dashboard.html", "utf8");
  const js = html.match(/<script>([\s\S]*)<\/script>/)[1];
  const sandbox = {
    fetch: wrappedFetch, URLSearchParams, console,
    location: {search: MOCK ? "?mock=1" : "", protocol: "https:"},
    document: dummyDoc, addEventListener() {}, matchMedia: () => ({matches: true}),
    setInterval: () => 0, clearInterval() {}, setTimeout, clearTimeout,
    Date, Math, JSON, Promise, Object, Array, Number, String, Boolean, RegExp,
  };
  sandbox.globalThis = sandbox; sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(js + `
    ;globalThis.__api = {
      get DATA(){return DATA}, get INSTR(){return INSTR}, get TFS(){return TFS},
      get UNIVERSES(){return UNIVERSES}, get PAIRS(){return PAIRS},
      loadUniverse, scanStrategies, alignmentPicks, mtfProfile,
      setUni: k => { activeUni = k; }, get UNI_STATE(){return UNI_STATE},
      STRATEGIES,
    };`, sandbox, {timeout: 60000});
  const api = sandbox.__api;

  /* wait for the crypto boot loop to finish (boot() runs inside the script) */
  const t0 = Date.now();
  while (Date.now() - t0 < 180000) {
    const d = api.DATA["BTCUSDT"];
    if (d && d["Q"] && d["5m"]) break;
    await new Promise(r => setTimeout(r, 1500));
  }
  /* load every backend universe */
  for (const u of api.UNIVERSES) {
    if (u.key === "crypto") continue;
    try { await api.loadUniverse(u.key); } catch (e) {}
  }

  /* ---- collect current >=MIN_CONV picks across all universes ---- */
  const picks = {};
  for (const u of api.UNIVERSES) {
    api.setUni(u.key);
    const best = {};
    const scan = api.scanStrategies();
    for (const key of Object.keys(scan))
      for (const m of scan[key])
        if (!best[m.sym] || m.conv > best[m.sym].conv) best[m.sym] = m;
    for (const m of api.alignmentPicks())
      if (!best[m.sym] || m.conv > best[m.sym].conv) best[m.sym] = m;
    for (const m of Object.values(best))
      if (m.conv >= MIN_CONV && m.plan && isFinite(m.plan.sl)) picks[m.sym] = m;
  }
  console.log(`picks >= ${MIN_CONV}: ${Object.keys(picks).length}`);

  /* ---- load journal ---- */
  let journal = {open: [], closed: []};
  if (fs.existsSync(JOURNAL)) {
    try { journal = JSON.parse(fs.readFileSync(JOURNAL, "utf8")); } catch (e) {}
  }
  journal.open = journal.open || []; journal.closed = journal.closed || [];
  const now = Date.now();

  /* ---- evaluate open entries against fresh candles ---- */
  const stillOpen = [];
  for (const p of journal.open) {
    const cell = api.DATA[p.sym] && api.DATA[p.sym][p.tfKey];
    if (!cell) { stillOpen.push(p); continue; }
    const cs = cell.candles.filter(c => c.t > p.ts);
    let tpHit = p.tpHit || 0;   // highest TP reached so far
    let outcome = null, r = null;
    /* per-pick structural R multiples (legacy entries default to 1/2/3) */
    const R1 = p.r1 || 1, R2 = p.r2 || 2, R3 = p.r3 || 3;
    const lockedR = h => h >= 2 ? (R1 + R2) / 3 : h === 1 ? R1 / 3 : 0;
    for (const c of cs) {
      const hiTouch = lvl => p.dir === 1 ? c.h >= lvl : c.l <= lvl;
      const loTouch = lvl => p.dir === 1 ? c.l <= lvl : c.h >= lvl;
      const stopLvl = tpHit >= 1 ? p.entry : p.sl;   // BE after TP1
      if (loTouch(stopLvl)) {                        // conservative: stop first
        outcome = tpHit >= 1 ? "BE" : "SL";
        r = tpHit >= 1 ? +lockedR(tpHit).toFixed(2) : -1;
        break;
      }
      if (tpHit < 1 && hiTouch(p.tp1)) tpHit = 1;
      if (tpHit < 2 && hiTouch(p.tp2)) tpHit = 2;
      if (tpHit < 3 && hiTouch(p.tp3)) {
        tpHit = 3; outcome = "TP3"; r = +((R1 + R2 + R3) / 3).toFixed(2); break;
      }
    }
    if (!outcome && now - p.ts > EXPIRE_DAYS * 864e5) {
      const last = cell.candles[cell.candles.length - 1].c;
      const curR = (p.dir === 1 ? last - p.entry : p.entry - last) / p.risk;
      const locked = lockedR(tpHit);
      const openFrac = tpHit === 2 ? 1/3 : tpHit === 1 ? 2/3 : 1;
      outcome = "EXPIRED"; r = +(locked + openFrac * curR).toFixed(2);
    }
    if (outcome) {
      journal.closed.push({...p, tpHit, outcome, r, closedTs: now});
      console.log(`  closed ${p.sym} ${p.dir === 1 ? "LONG" : "SHORT"}: ${outcome} (${r >= 0 ? "+" : ""}${r}R)`);
    } else { p.tpHit = tpHit; stillOpen.push(p); }
  }
  journal.open = stillOpen;
  journal.closed = journal.closed.slice(-500);

  /* ---- open new entries ---- */
  const openSyms = new Set(journal.open.map(p => p.sym));
  const recentClosed = new Set(journal.closed
    .filter(c => now - c.closedTs < 24 * 3600e3).map(c => c.sym + c.dir));
  const fresh = [];
  for (const m of Object.values(picks)) {
    if (openSyms.has(m.sym) || recentClosed.has(m.sym + m.dir)) continue;
    const meta = api.INSTR[m.sym] || {};
    fresh.push({
      id: m.sym + "-" + now, sym: m.sym, name: meta.name || m.sym,
      cls: meta.cls, dir: m.dir, tfKey: m.tfKey, conv: m.conv,
      entryQ: m.entryQ != null ? m.entryQ : null,
      grade: m.grade || null, quality: m.quality != null ? m.quality : null,
      type: m.prof ? m.prof.type : "", strat: m.strat.name, ts: now,
      entry: +m.plan.entry, sl: +m.plan.sl, risk: +m.plan.risk,
      tp1: +m.plan.tp1, tp2: +m.plan.tp2, tp3: +m.plan.tp3, tpHit: 0,
      r1: +(m.plan.r1 || 1), r2: +(m.plan.r2 || 2), r3: +(m.plan.r3 || 3),
    });
  }
  /* ---- AI review of fresh picks (no-op until ANTHROPIC_API_KEY exists) ---- */
  let newsItems = [];
  try { newsItems = JSON.parse(fs.readFileSync("site/data/news.json", "utf8")).items || []; }
  catch (e) {}
  for (const p of fresh.slice(0, MAX_REVIEWS)) {
    const cell = api.DATA[p.sym] && api.DATA[p.sym][p.tfKey];
    const f = cell && cell.feats;
    const prof = api.mtfProfile(p.sym);
    const ctx = {
      tech: f ? `RSI ${f.rsi.toFixed(0)}, stretch ${f.stretch.toFixed(1)}×ATR past 50EMA, ` +
        `structure ${f.structure.state}, squeeze ${f.inSqueeze ? "on" : f.released ? "just fired" : "off"}, ` +
        `volume z ${f.volZ.toFixed(1)}` +
        (prof ? `; groups LTF ${prof.gL.toFixed(2)} MTF ${prof.gM.toFixed(2)} HTF ${prof.gH.toFixed(2)}` : "")
        : "n/a",
      fund: (function () {
        try {
          const fx = JSON.parse(fs.readFileSync("site/data/fundamentals.json", "utf8"))
            .instruments[p.sym];
          return fx ? (fx.flags || []).join("; ") || "no flags" : "none on file";
        } catch (e) { return "none on file"; }
      })(),
      news: newsItems.filter(x => (x.instruments || []).includes(p.sym))
        .slice(0, 5).map(x => x.title).join(" | "),
    };
    const ai = await aiReview(p, ctx);
    if (ai) { p.ai = ai; console.log(`  🤖 ${p.name}: ${ai.verdict} — ${ai.summary}`); }
  }

  journal.open.push(...fresh);
  journal.generated = now;
  console.log(`new entries: ${fresh.length} · open: ${journal.open.length} · closed total: ${journal.closed.length}`);

  fs.mkdirSync("state", {recursive: true});
  fs.writeFileSync(JOURNAL, JSON.stringify(journal));
  fs.mkdirSync("site/data", {recursive: true});
  fs.writeFileSync("site/data/journal.json", JSON.stringify(journal));

  /* ---- Telegram alerts (new picks + closes) ---- */
  const token = process.env.TELEGRAM_BOT_TOKEN, chat = process.env.TELEGRAM_CHAT_ID;
  if (!MOCK && token && chat) {
    const send = async text => {
      try {
        await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({chat_id: chat, text, parse_mode: "HTML",
            disable_web_page_preview: true}),
        });
      } catch (e) { console.error("telegram:", e.message); }
    };
    const f = v => v >= 1000 ? Math.round(v).toLocaleString("en-GB") :
      v >= 10 ? v.toFixed(2) : v.toPrecision(4);
    /* Alert on GRADE, not raw conviction: only A+/A entries reach Telegram.
       B/C/WAIT are journaled silently so calibration still scores them.
       The AI verdict is ADVISORY — a veto is shown inside the alert, never
       suppresses it, until the journal proves vetoes add value. */
    const alertable = fresh.filter(p => p.grade === "A+" || p.grade === "A" ||
      (!p.grade && p.conv >= MIN_CONV));   // legacy fallback if grade missing
    for (const p of alertable.slice(0, MAX_ALERTS)) {
      const aiLine = p.ai
        ? `🤖 ${p.ai.verdict === "CONFIRM" ? "✅ AI confirms" :
             p.ai.verdict === "VETO" ? "⛔ AI advises against (advisory only)" : "⚠️ AI caution"}` +
          ` (adj ${p.ai.conv2}/100): ${p.ai.summary}\n` +
          (p.ai.risks && p.ai.risks.length ? `   Risks: ${p.ai.risks.join(" · ")}\n` : "")
        : "";
      const gradeLine = p.grade
        ? `★ Grade <b>${p.grade}</b> · direction ${p.conv}/100 · entry ${p.entryQ}/100\n`
        : "";
      await send(
        `${p.dir === 1 ? "🟢 <b>LONG" : "🔴 <b>SHORT"} · ${p.name}</b> (${p.cls})\n` +
        (p.dir !== 1 ? "↳ <i>short — spread-bet/derivative only, can't short spot</i>\n" : "") +
        gradeLine +
        `${p.strat} · ${p.tfKey} · ${p.type}\n` +
        `🎯 Entry ${f(p.entry)} · 🛑 SL ${f(p.sl)}\n` +
        `💰 TP1 ${f(p.tp1)} (${p.r1}R) · TP2 ${f(p.tp2)} (${p.r2}R) · TP3 ${f(p.tp3)} (${p.r3}R)\n` +
        aiLine +
        `⚠️ <i>Systematic signal, not financial advice — size from the stop.</i>`);
    }
    const justClosed = journal.closed.filter(c => c.closedTs === now);
    for (const c of justClosed.slice(0, MAX_ALERTS)) {
      const em = c.r > 0 ? "✅" : c.r < 0 ? "❌" : "➖";
      await send(`${em} <b>${c.name}</b> ${c.dir === 1 ? "long" : "short"} closed: ` +
        `<b>${c.outcome}</b> → ${c.r >= 0 ? "+" : ""}${c.r}R (tracked, thirds model)`);
    }
  }
  process.exit(0);
}

main().catch(e => { console.error(e); process.exit(1); });
