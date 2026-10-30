/* ÖkoFEN Portal: sidebar panel with an animated schematic of the installation.
 * Data comes from the integration through the websocket command okofen_portal/dashboard.
 * The layout is one fixed reference scheme: buffer tank with a low solar coil, back-up boiler,
 * heating circuit with a mixing valve, instant hot water through a plate exchanger, and a pool
 * exchanger. Elements the controller does not report simply show "–". */
// The texts come from i18n/<language>.json through the websocket command (key "strings").
const SCENARIOS = {
  summer: {contact: 0, boilT: 48, bPump: 0, mixer: 0, coll: 120, ecsP: 70.5, top: 70, mid: 66, bot: 55, solarPump: 60, heat: false, flow: 8, pool: 24, poolPump: 40, out: 25, room: 23.5},
  winter: {contact: 1, boilT: 68, bPump: 60, mixer: 1, coll: 8, ecsP: 58.5, top: 58, mid: 52, bot: 40, solarPump: 0, heat: true, flow: 45, pool: 9, poolPump: 0, out: 3, room: 20.5},
};
const CSS = `
:host{display:block;min-height:100%;background:var(--primary-background-color,#f6f4ef);color:var(--primary-text-color,#1f2933);font:15px/1.45 var(--paper-font-body1_-_font-family,system-ui,sans-serif);
--bg:var(--primary-background-color,#f6f4ef);--card:var(--card-background-color,#fff);--fg:var(--primary-text-color,#1f2933);--mut:var(--secondary-text-color,#66727f);--line:var(--divider-color,#d9d4c8);--track:#cfc9bb;--hot:#e8590c;--solar:#f59f00;--cold:#1c7ed6;--warm:#d6336c;--ok:#2b8a3e;--red:#e03131}
:host([dark]){--track:#3a4651;--hot:#ff8a4c;--solar:#ffc233;--cold:#5aa9f0;--warm:#f06595;--ok:#69db7c;--red:#ff6b6b}



*{box-sizing:border-box}

main{max-width:1100px;margin:0 auto;padding:16px 16px 32px}
h1{font-size:22px;margin:0 0 4px;font-weight:500}
.sub{color:var(--mut);margin:0 0 14px}
.bar{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin-bottom:12px}
select,button{font:inherit;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
button{cursor:pointer}
label{display:flex;gap:6px;align-items:center}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px}
svg{width:100%;height:auto;display:block}
svg text{fill:var(--fg);font-size:13px}
svg .mut{fill:var(--mut);font-size:12px}
svg .big{font-size:15px;font-weight:600}
.box{fill:var(--card);stroke:var(--line);stroke-width:2}
.tank{stroke:var(--fg);stroke-width:3;fill:url(#tg)}
.tt{fill:#fff;font-weight:600;paint-order:stroke;stroke:#0006;stroke-width:3px}
.coil{fill:none;stroke:#fff9;stroke-width:6;stroke-linejoin:round;stroke-linecap:round}
.track{fill:none;stroke:var(--track);stroke-width:7;stroke-linecap:round;stroke-linejoin:round}
.flow{fill:none;stroke-width:5;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:2 14;opacity:0}
.flow.on{opacity:1;animation:dash var(--d,2s) linear infinite}
.hot{stroke:var(--hot)}.solar{stroke:var(--solar)}.cold{stroke:var(--cold)}.warm{stroke:var(--warm)}
@keyframes dash{to{stroke-dashoffset:-16}}
#motor.on{stroke:var(--ok);stroke-width:3.5}
.ctl{fill:none;stroke:var(--mut);stroke-width:2;stroke-dasharray:3 5}
.ctl.on{stroke:var(--ok);stroke-width:3;animation:dash .8s linear infinite}
.pump circle{fill:var(--card);stroke:var(--fg);stroke-width:2}
.pump path{fill:var(--mut)}
.pump.on path{fill:var(--ok);animation:spin 1s linear infinite;transform-box:fill-box;transform-origin:center}
@keyframes spin{to{transform:rotate(360deg)}}
.xch{fill:var(--card);stroke:var(--fg);stroke-width:2.5}
.xch-l{stroke:var(--mut);stroke-width:2}
.xch.on{stroke:var(--hot);filter:drop-shadow(0 0 5px var(--hot))}
.rays{transform-box:fill-box;transform-origin:center}
.sun.on .rays{animation:spin 12s linear infinite}
.chips{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:12px}
.chip{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 10px}
.chip b{display:block;font-size:19px}.chip span{color:var(--mut);font-size:12px}
.note{color:var(--mut);font-size:13px;margin-top:12px}
.note li{margin:2px 0}
.badge{display:inline-block;border:1px solid var(--line);border-radius:6px;padding:0 6px;font-size:12px;color:var(--mut)}
@media (prefers-reduced-motion:reduce){.flow.on,.pump.on path,.sun.on .rays,.ctl.on{animation:none}.flow{stroke-dasharray:none}}

.bar{margin-top:0}`;
const svgFor = (t) => `<svg viewBox="0 -45 1000 705" role="img" aria-label="${t.aria}">
<defs>
  <linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">
    <stop id="gE" offset="8%" stop-color="#e8590c"/>
    <stop id="g0" offset="32%" stop-color="#e8590c"/>
    <stop id="g1" offset="58%" stop-color="#e8590c"/>
    <stop id="g2" offset="92%" stop-color="#e8590c"/>
  </linearGradient>
  <!-- symbole échangeur à plaques (comme schema echangeur a plaque.png): primaire à droite, secondaire à gauche, contre-courant -->
  <!-- dégradé côté usage (eau chaude sanitaire et piscine): bleu en bas (entrée froide) vers rouge en haut (sortie chaude) -->
  <linearGradient id="ecsg" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" style="stop-color:var(--cold)"/><stop offset="1" style="stop-color:var(--red)"/>
  </linearGradient>
  <g id="plates" fill="none" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">
    <path stroke="var(--hot)" d="M70,25 H56 L36,37 L56,49 L36,61 L56,73 L36,85 H70"/>
    <path stroke="url(#ecsg)" d="M0,85 H24 L44,73 L24,61 L44,49 L24,37 L44,25 H0"/>
  </g>
  <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
    <stop id="pg0" offset="0" stop-color="#1c7ed6"/><stop id="pg1" offset="1" stop-color="#1c7ed6"/>
  </linearGradient>
</defs>

<!-- ===== tuyaux (le tracé donne le sens du flux) ===== -->
<g id="pipes">
  <!-- solaire: capteurs -> spirale basse -> capteurs -->
  <path class="flow solar" data-g="solar" d="M880,40 V376 H430 V392 H530 V408"/>
  <path class="flow solar" data-g="solar" d="M530,408 H430 V424 H920 V40" style="opacity:.55"/>
  <!-- chaudière: retour chaud en haut, aller en bas -->
  <path class="flow hot"  data-g="boiler" d="M700,125 H560"/>
  <path class="flow cold" data-g="boiler" d="M560,170 H700"/>
  <!-- chauffage maison -->
  <path class="flow hot"  data-g="heat" d="M560,262 H700"/>
  <path class="flow cold" data-g="heat" d="M700,325 H560"/>
  <!-- ECS: primaire (ballon) + secondaire (eau réseau) -->
  <path class="flow hot"  data-g="ecs" d="M400,135 H320"/>
  <path class="flow cold" data-g="ecs" d="M320,195 H400"/>
  <path class="flow cold" data-g="ecs" d="M20,195 H250"/>
  <path class="flow warm" data-g="ecs" d="M250,135 H20"/>
  <!-- piscine: primaire (ballon) + secondaire (eau piscine) -->
  <path class="flow hot"  data-g="pool" d="M400,355 H320"/>
  <path class="flow cold" data-g="pool" d="M320,415 H400"/>
  <path class="flow cold" data-g="pool" d="M170,415 H250"/>
  <path class="flow warm" data-g="pool" d="M250,355 H170"/>
</g>

<!-- ===== ballon ===== -->
<text x="480" y="72" text-anchor="middle" class="big">${t.tank}</text>
<rect class="tank" x="400" y="90" width="160" height="350" rx="28"/>
<path class="coil" d="M560,376 H430 V392 H530 V408 H430 V424 H560"/>
<text class="tt" x="480" y="122" text-anchor="middle" id="tProbe">ECS</text>
<text class="tt" x="480" y="195" text-anchor="middle" id="tTop">Haut</text>
<text class="tt" x="480" y="270" text-anchor="middle" id="tMid">Milieu</text>
<text class="tt" x="480" y="350" text-anchor="middle" id="tBot">Bas</text>
<g stroke="#fff8" stroke-dasharray="3 4"><path d="M410,152H550M410,232H550M410,310H550"/></g>
<text class="mut" x="480" y="460" text-anchor="middle">${t.coil}</text>

<!-- ===== pompe de circulation solaire (retour vers les capteurs) ===== -->
<g class="pump" id="pSolar" transform="translate(700 424)"><circle r="13"/><path d="M-6-7L8 0L-6 7Z"/></g>
<text x="700" y="451" text-anchor="middle" class="mut">${t.solarPump}</text>
<text x="700" y="466" text-anchor="middle" class="mut" id="tPSol">–</text>

<!-- ===== capteurs ===== -->
<rect class="box" x="720" y="-30" width="220" height="70" rx="8"/>
<text x="830" y="0" text-anchor="middle" class="big">${t.collectors}</text>
<text x="830" y="24" text-anchor="middle" id="tColl">–</text>
<g class="sun" id="sun" transform="translate(675 5)">
  <circle r="14" fill="#f59f00"/>
  <g class="rays" stroke="#f59f00" stroke-width="3" stroke-linecap="round">
    <path d="M0-24V-19M0 19V24M-24 0H-19M19 0H24M-17-17l3 3M14 14l3 3M-17 17l3-3M14-14l3-3"/>
  </g>
</g>

<!-- ===== chaudière ===== -->
<rect class="box" x="700" y="95" width="160" height="105" rx="12"/>
<text x="780" y="125" text-anchor="middle" class="big">${t.boiler}</text>
<text x="780" y="144" text-anchor="middle" class="mut">${t.boilerSub}</text>
<text x="780" y="172" text-anchor="middle" id="tBoiler">–</text>
<text x="780" y="190" text-anchor="middle" class="mut" id="tBoilSub">–</text>

<g class="pump" id="pBoil" transform="translate(630 170)"><circle r="13"/><path d="M-6-7L8 0L-6 7Z"/></g>
<text x="630" y="200" text-anchor="middle" class="mut">${t.boilerPump}</text>
<text x="630" y="215" text-anchor="middle" class="mut" id="tPBoil">–</text>

<!-- ===== chauffage ===== -->
<rect class="box" x="700" y="240" width="160" height="110" rx="12"/>
<text x="780" y="268" text-anchor="middle" class="big">${t.heating}</text>
<g stroke="var(--mut)" stroke-width="3" stroke-linecap="round"><path d="M725,285V325M740,285V325M755,285V325M770,285V325"/><path d="M795,285V325M810,285V325M825,285V325M840,285V325"/></g>
<text x="780" y="342" text-anchor="middle" id="tHeat" class="mut">–</text>
<g class="pump" id="pHeat" transform="translate(598 262)"><circle r="13"/><path d="M-6-7L8 0L-6 7Z"/></g>
<rect class="box" x="642" y="252" width="38" height="82" rx="8"/>
<path d="M650,262L672,324M672,262L650,324" stroke="var(--fg)" stroke-width="3" stroke-linecap="round"/>
<circle cx="661" cy="293" r="6" fill="var(--card)" stroke="var(--fg)" stroke-width="2.5"/>
<rect class="box" id="motor" x="650" y="226" width="22" height="22" rx="4"/>
<text x="661" y="242" text-anchor="middle" style="font-weight:700">M</text>
<path d="M661,248V253" stroke="var(--fg)" stroke-width="3"/>
<text x="661" y="350" text-anchor="middle" class="mut">${t.mixValve}</text>
<text x="661" y="365" text-anchor="middle" class="mut" id="tMix">motorisée</text>

<!-- ===== ECS ===== -->
<text x="20" y="122" class="big">${t.hotWater}</text>
<rect class="xch" id="xEcs" x="250" y="110" width="70" height="100" rx="6"/>
<use href="#plates" x="250" y="110"/>
<g class="pump" id="pEcs" transform="translate(360 135)"><circle r="13"/><path d="M-6-7L8 0L-6 7Z"/></g>
<path id="ctl" class="ctl" d="M218,124 V95 H360 V121"/>
<rect x="205" y="124" width="26" height="22" rx="4" class="box"/>
<rect id="mag" x="209" y="130" width="8" height="10" rx="2" fill="var(--mut)"/>
<text x="218" y="162" text-anchor="middle" class="mut">${t.magnet}</text>
<text x="20" y="182" class="big">${t.coldWater}</text>

<!-- ===== piscine ===== -->
<rect class="xch" id="xPool" x="250" y="330" width="70" height="105" rx="6"/>
<use href="#plates" x="250" y="330"/>
<g class="pump" id="pPool" transform="translate(360 355)"><circle r="13"/><path d="M-6-7L8 0L-6 7Z"/></g>
<text x="362" y="332" text-anchor="middle" class="mut">${t.poolPump}</text>
<rect class="box" x="20" y="330" width="150" height="120" rx="12" fill="url(#pg)" style="fill:url(#pg)"/>
<text x="95" y="368" text-anchor="middle" class="tt">${t.pool}</text>
<text x="95" y="392" text-anchor="middle" class="tt" id="tPool">–</text>
<text x="285" y="455" text-anchor="middle" class="mut">${t.poolExchanger}</text>

<!-- ===== infos ===== -->
<text x="40" y="520" class="mut">${t.legend}</text>
<g stroke-width="5" stroke-linecap="round">
  <path d="M40,540H80" stroke="var(--solar)"/><text x="90" y="545">${t.lgSolar}</text>
  <path d="M40,562H80" stroke="var(--hot)"/><text x="90" y="567">${t.lgHot}</text>
  <path d="M40,584H80" stroke="var(--cold)"/><text x="90" y="589">${t.lgCold}</text>
  <path d="M40,606H80" stroke="var(--warm)"/><text x="90" y="611">${t.lgWarm}</text>
</g>
<text x="40" y="640" class="mut" id="tOut">–</text>
</svg>`;

const fmt = (n) => (n == null || Number.isNaN(n) ? '–' : Number(n).toFixed(1).replace('.', ','));
const pct = (n) => (n == null ? '–' : Math.round(n) + ' %');
const col = (t) => (t == null ? 'hsl(210 10% 55%)' : `hsl(${Math.max(0, Math.min(220, 220 - (t - 10) / 65 * 220))} 75% 48%)`);

class OkofenDashboard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: 'open'});
    this._cur = {};
    this._scenario = 'live';
    this._draw = false;
    this._src = '';
  }

  set hass(hass) {
    this._hass = hass;
    this.toggleAttribute('dark', !!(hass.themes && hass.themes.darkMode));
    if (!this._timer) { this._poll(); this._timer = setInterval(() => this._poll(), 15000); }
  }

  set narrow(_) {}
  set route(_) {}
  set panel(_) {}

  disconnectedCallback() { clearInterval(this._timer); this._timer = null; }

  _q(id) { return this.shadowRoot.getElementById(id); }

  _build() {
    const t = this._t;
    this.shadowRoot.innerHTML = `<style>${CSS}</style>
<main>
<h1>${t.title}</h1>
<p class="sub">${t.sub} <span id="src" class="badge"></span></p>
<div class="bar">
  <label>${t.scenario}
    <select id="sc"><option value="live">${t.live}</option><option value="summer">${t.summer}</option><option value="winter">${t.winter}</option></select>
  </label>
  <label><input type="checkbox" id="ecs"> ${t.draw}</label>
  <button id="re">${t.refresh}</button>
</div>
<div class="card">${svgFor(t)}</div>
<div class="chips" id="chips"></div>
<ul class="note"><li>${t.note}</li></ul>
</main>`;
    this.shadowRoot.querySelectorAll('path.flow').forEach((p) => {
      const track = p.cloneNode();
      track.removeAttribute('style');
      track.setAttribute('class', 'track');
      p.before(track);
    });
    this._q('sc').onchange = (e) => { this._scenario = e.target.value; this._poll(); };
    this._q('re').onclick = () => this._poll();
    this._q('ecs').onchange = (e) => { this._draw = e.target.checked; this._render(); };
    this._q('sc').value = this._scenario;
    this._q('ecs').checked = this._draw;
    this._render();
  }

  async _poll() {
    let t = this._t || {};
    let v = {};
    try {
      const res = await this._hass.callWS({type: 'okofen_portal/dashboard'});
      v = res.values || {};
      if (!this._t) { this._t = t = res.strings; this._lang = res.language; this._build(); }
    } catch (e) {
      this._cur = {};
      this._src = t.error || '';
      if (this._t) this._render();
      return;
    }
    if (this._scenario !== 'live') {
      this._cur = {...SCENARIOS[this._scenario]};
      this._src = '';
    } else {
      try {
        this._cur = {
          coll: v.coll, ecsP: v.ecs_probe, top: v.tank_top, mid: v.tank_mid, bot: v.tank_bottom, solarPump: v.solar_pump,
          bPump: v.boiler_pump, contact: v.burner, boilT: v.boiler_temp, heat: v.heating_pump > 0, flow: v.flow, pool: v.pool,
          poolPump: v.pool_pump, out: v.outdoor, mixer: v.mixer, room: v.room,
        };
        this._src = `${t.updated} ${new Date().toLocaleTimeString(this._lang)}`;
      } catch (e) {
        this._cur = {};
        this._src = t.error;
      }
    }
    this._render();
  }

  _group(g, on, dur) {
    this.shadowRoot.querySelectorAll(`.flow[data-g="${g}"]`).forEach((p) => {
      p.classList.toggle('on', !!on);
      p.style.setProperty('--d', dur + 's');
    });
  }

  _on(id, on) { const el = this._q(id); if (el) el.classList.toggle('on', !!on); }
  _set(id, text) { const el = this._q(id); if (el) el.textContent = text; }
  _stop(id, color) { const el = this._q(id); if (el) el.setAttribute('stop-color', color); }

  _render() {
    if (!this._t || !this._q('src')) return;
    const t = this._t, s = this._cur, draw = this._draw;
    this._q('src').textContent = this._src;
    this._stop('gE', col(s.ecsP)); this._stop('g0', col(s.top)); this._stop('g1', col(s.mid)); this._stop('g2', col(s.bot));
    this._stop('pg0', col(s.pool == null ? null : s.pool + 6)); this._stop('pg1', col(s.pool == null ? null : s.pool - 4));
    this._set('tProbe', `${t.probe} ${fmt(s.ecsP)} °C`);
    this._set('tTop', `${t.top} ${fmt(s.top)} °C`);
    this._set('tMid', `${t.mid} ${fmt(s.mid)} °C`);
    this._set('tBot', `${t.bot} ${fmt(s.bot)} °C`);
    this._set('tColl', `${fmt(s.coll)} °C`);
    const burner = s.contact == null ? null : s.contact > 0;
    this._set('tBoiler', burner == null ? '–' : burner ? t.burnerOn : t.burnerOff);
    this._set('tBoilSub', s.boilT == null ? '–' : `${fmt(s.boilT)} °C`);
    this._set('tHeat', s.heat ? `${t.flowTxt} ${fmt(s.flow)} °C` : t.off);
    this._set('tPool', `${fmt(s.pool)} °C`);
    this._set('tOut', `${t.outdoor} ${fmt(s.out)} °C`);
    this._group('solar', s.solarPump > 0, 3.2 - 2.4 * (s.solarPump || 0) / 100);
    this._group('boiler', s.bPump > 0, 2);
    this._group('heat', s.heat, 2.4);
    this._group('pool', s.poolPump > 0, 3.2 - 2.4 * (s.poolPump || 0) / 100);
    this._group('ecs', draw, 1.4);
    this._on('pBoil', s.bPump > 0); this._set('tPBoil', pct(s.bPump));
    this._on('pSolar', s.solarPump > 0); this._set('tPSol', pct(s.solarPump));
    this._on('pHeat', s.heat); this._on('pPool', s.poolPump > 0); this._on('pEcs', draw);
    this._on('xPool', s.poolPump > 0); this._on('xEcs', draw); this._on('ctl', draw);
    this._on('sun', s.coll > 40); this._on('motor', s.mixer > 0);
    this._set('tMix', `${t.motor} · ${s.mixer == null ? '–' : t.mixer[s.mixer] || '–'}`);
    const mag = this._q('mag'); if (mag) mag.setAttribute('x', draw ? 221 : 209);
    const c = t.chips;
    this._q('chips').innerHTML = [
      [c[0], `${fmt(s.coll)} °C`], [c[1], `${fmt(s.ecsP)} °C`], [c[2], `${fmt(s.top)} °C`], [c[3], `${fmt(s.mid)} °C`],
      [c[4], `${fmt(s.bot)} °C`], [c[5], pct(s.solarPump)], [c[6], `${fmt(s.pool)} °C`], [c[7], pct(s.poolPump)],
      [c[8], s.heat ? `${fmt(s.flow)} °C` : t.off], [c[9], burner == null ? '–' : burner ? 'ON' : t.off],
      [c[10], `${fmt(s.boilT)} °C`], [c[11], `${fmt(s.room)} °C`],
    ].map(([k, v]) => `<div class="chip"><span>${k}</span><b>${v}</b></div>`).join('');
  }
}
customElements.define('okofen-dashboard', OkofenDashboard);
