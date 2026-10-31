/* ÖkoFEN Portal: sidebar panel with an animated schematic of the installation.
 * Data comes from the integration through the websocket command okofen_portal/dashboard and refreshes by itself.
 * The layout is one fixed reference scheme: buffer tank with a low solar coil, back-up boiler,
 * heating circuit with a 4-way mixing valve, instant hot water through a plate exchanger, and a pool
 * exchanger. Hovering (or focusing) an element shows its values. Elements the controller does not report show "–". */
// The texts come from i18n/<language>.json through the websocket command (key "strings").
const CSS = `
:host{display:block;min-height:100%;background:var(--primary-background-color,#f6f4ef);color:var(--primary-text-color,#1f2933);font:14px/1.45 var(--paper-font-body1_-_font-family,system-ui,sans-serif);
--bg:var(--primary-background-color,#f6f4ef);--card:var(--card-background-color,#fff);--fg:var(--primary-text-color,#1f2933);--mut:var(--secondary-text-color,#66727f);--line:var(--divider-color,#d9d4c8);--track:#cfc9bb;--hot:#e8590c;--solar:#f59f00;--cold:#1c7ed6;--warm:#d6336c;--ok:#2b8a3e;--red:#e03131}
:host{--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#6250d6}
:host([dark]){--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9}
:host([dark]){--track:#3a4651;--hot:#ff8a4c;--solar:#ffc233;--cold:#5aa9f0;--warm:#f06595;--ok:#69db7c;--red:#ff6b6b}
*{box-sizing:border-box}
main{max-width:1100px;margin:0 auto;padding:16px 16px 32px}
h1{font-size:22px;margin:0 0 4px;font-weight:500}
.sub{color:var(--mut);margin:0 0 14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px}
svg{width:100%;height:auto;display:block}
svg text{fill:var(--fg);font-size:14px}
svg .mut{fill:var(--mut)}
svg .big{font-weight:600}
.box{fill:var(--card);stroke:var(--line);stroke-width:2}
.tank{stroke:var(--fg);stroke-width:3;fill:url(#tg)}
.tt{fill:#fff;font-weight:600;paint-order:stroke;stroke:#0006;stroke-width:3px}
.coil{fill:none;stroke:#fff9;stroke-width:6;stroke-linejoin:round;stroke-linecap:round}
.track{fill:none;stroke:var(--track);stroke-width:7;stroke-linecap:round;stroke-linejoin:round}
.flow{fill:none;stroke-width:5;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:2 14;opacity:0}
.flow.on{opacity:1;animation:dash var(--d,2s) linear infinite}
.hot{stroke:var(--hot)}.solar{stroke:var(--solar)}.cold{stroke:var(--cold)}.warm{stroke:var(--warm)}
@keyframes dash{to{stroke-dashoffset:-16}}
#sun,#moon,#cloud,#horizon{transition:opacity 1.5s ease,transform 1.5s ease}
#sky .gone{opacity:0}
#sun circle{fill:#f59f00;transition:fill 1.5s ease}#sun .rays{stroke:#f59f00;transition:stroke 1.5s ease,opacity 1.5s ease}
#sun.low,#moon.low{transform:translateY(26px)}#sun.low circle{fill:#f76707}#sun.low .rays{opacity:0}
#sun.down,#moon.down{transform:translateY(48px);opacity:0}
#horizon{stroke:#f76707;stroke-width:2;stroke-linecap:round;transition:opacity 1.5s ease,stroke 1.5s ease}#horizon.night{stroke:#9aa5b1}
#cloud{fill:#aeb8c3;transition:opacity 1.5s ease,fill 1.5s ease}#cloud.rain{fill:#7b8794}#cloud.snow{fill:#c5ced8}
#rain,#snow,#bolt,#fog{transition:opacity 1.5s ease}
#rain{stroke:#4a90d9}#snow{fill:#9fb3c8}#bolt{fill:#f59f00}#fog{stroke:#aeb8c3}
#rain.fall:not(.gone){animation:fall .9s linear infinite}#snow.fall:not(.gone){animation:fall 2.4s linear infinite}
#bolt:not(.gone){animation:flash 3s steps(1) infinite}
@keyframes fall{from{transform:translateY(-4px);opacity:.3}50%{opacity:1}to{transform:translateY(5px);opacity:.3}}
@keyframes flash{0%,8%,14%{opacity:1}5%,11%,20%,100%{opacity:.15}}svg [hidden]{display:none}
#boilIcon{fill:var(--red)}#boilOff,#heatIcon{fill:var(--mut)}#heatIcon.on{fill:var(--red)}
#motor.on{stroke:var(--ok);stroke-width:3.5}
.ctl{fill:none;stroke:var(--mut);stroke-width:2;stroke-dasharray:3 5}
.ctl.on{stroke:var(--ok);stroke-width:3;animation:dash .8s linear infinite}
.pump circle{fill:var(--card);stroke:var(--fg);stroke-width:2}
.pump path{fill:var(--mut)}
.pump.on path{fill:var(--ok);animation:spin 1s linear infinite;transform-box:fill-box;transform-origin:33.333% 50%}
@keyframes spin{to{transform:rotate(360deg)}}
.xch{fill:var(--card);stroke:var(--fg);stroke-width:2.5}
.xch.on{stroke:var(--hot);filter:drop-shadow(0 0 5px var(--hot))}
.rays{transform-box:fill-box;transform-origin:center}
.sun.on .rays{animation:spin 12s linear infinite}
[data-tip]{cursor:help}
[data-tip]:focus{outline:none}
#tip{position:fixed;z-index:9;pointer-events:none;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 10px;box-shadow:0 6px 20px #0003;min-width:190px}
#tip[hidden]{display:none}
#tip b{display:block;margin-bottom:4px}
#tip div{display:flex;justify-content:space-between;gap:14px}#tip span{color:var(--mut)}
nav{display:flex;gap:6px;margin:0 0 10px}
nav button{font:inherit;color:var(--mut);background:none;border:1px solid var(--line);border-radius:8px;padding:4px 12px;cursor:pointer}
nav button[aria-selected=true]{color:var(--fg);background:var(--card);font-weight:500}
.pad{padding:14px 16px}
.head{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;margin-bottom:12px}
.state{font-weight:600;border-radius:6px;padding:2px 10px;background:var(--line)}
.state.active{background:var(--ok);color:#000}.state.restoring{background:var(--solar);color:#000}
.head .mut,.solar .mut{color:var(--mut)}
.head button{margin-left:auto;font:inherit;border:1px solid var(--line);border-radius:8px;padding:5px 14px;background:var(--card);color:var(--fg);cursor:pointer}
.solar h2{font-size:inherit;font-weight:600;margin:14px 0 6px}
.solar table{border-collapse:collapse;width:100%}
.solar td{padding:4px 8px;border-top:1px solid var(--line)}
.solar td:first-child{width:1.6em;text-align:center}
.solar td.v{text-align:right;white-space:nowrap}.solar td.l{color:var(--mut);white-space:nowrap}
.solar tr.no td{color:var(--red)}.solar tr.no td.l{color:var(--mut)}
.hist h2{font-size:inherit;font-weight:600;margin:4px 0 2px}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;margin:0 0 8px}
.legend button{font:inherit;color:var(--fg);background:none;border:0;padding:2px 0;cursor:pointer;display:flex;align-items:center;gap:6px}
.legend button[aria-pressed=false]{color:var(--mut);text-decoration:line-through}
.legend i{display:inline-block;width:14px;height:3px;border-radius:2px}
.hist svg text{fill:var(--mut)}
.hist .grid{stroke:var(--line);stroke-width:1}
.hist .line{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.hist .cross{stroke:var(--mut);stroke-width:1}
.replay{display:flex;align-items:center;gap:12px;margin:6px -8px -8px;padding:12px 16px;border-top:1px solid var(--line);background:var(--bg);border-radius:0 0 12px 12px}
.replay button{font:inherit;border:1px solid var(--line);border-radius:8px;padding:4px 10px;background:var(--card);color:var(--fg);cursor:pointer;white-space:nowrap}
.replay button:disabled,.rpTrack input:disabled{opacity:.4;cursor:default}
.replay #rpPlay{width:40px;height:40px;border-radius:50%;padding:0;background:var(--fg);color:var(--card);border-color:var(--fg)}
.rpTrack{position:relative;flex:1;height:72px}
.rpTrack svg{position:absolute;left:0;right:0;bottom:0;width:100%;height:58px}
.rpTrack span{position:absolute;top:-2px;line-height:1;color:var(--mut);white-space:nowrap}
.rpTrack input{position:absolute;left:0;right:0;bottom:28px;height:30px;width:100%;margin:0;background:none;-webkit-appearance:none;appearance:none;cursor:pointer}
.rpTrack input::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;border-radius:50%;background:var(--card);border:3px solid var(--fg);box-shadow:0 1px 4px #0004;cursor:grab}
.rpTrack input::-moz-range-thumb{width:12px;height:12px;border-radius:50%;background:var(--card);border:3px solid var(--fg);box-shadow:0 1px 4px #0004;cursor:grab}
/* the time being replayed, "now" on hover; all labels stacked in one cell so the button keeps the widest one's size */
#rpNow{display:inline-grid;font-variant-numeric:tabular-nums;color:var(--mut)}#rpNow.past{color:var(--fg)}
#rpNow>span{grid-area:1/1;text-align:center}#rpNow>.n,#rpNow>.z{visibility:hidden}
#rpNow.past:not(:disabled):hover>.t{visibility:hidden}#rpNow.past:not(:disabled):hover>.n{visibility:visible}
.badge{display:inline-block;border:1px solid var(--line);border-radius:6px;padding:0 6px;color:var(--mut)}
@media (prefers-reduced-motion:reduce){.flow.on,.pump.on path,.sun.on .rays,.ctl.on,#rain,#snow,#bolt{animation:none}.flow{stroke-dasharray:none}}`;
const svgFor = (t) => `<svg viewBox="0 -45 1000 505" role="img" aria-label="${t.aria}">
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
  <clipPath id="xclip"><rect width="70" height="100"/></clipPath>
  <g id="plates" clip-path="url(#xclip)" fill="none" stroke-width="7" stroke-linejoin="round" stroke-linecap="round">
    <path stroke="var(--hot)" d="M70,25 H56 L38,45 L56,65 L38,85 H70"/>
    <path stroke="url(#ecsg)" d="M0,85 H24 L42,65 L24,45 L42,25 H0"/>
  </g>
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
  <!-- vanne 4 voies (centre 661,293): gauche = chaud du ballon, haut = départ maison, droite = retour maison, bas = retour ballon -->
  <path class="flow hot"  data-g="heat" d="M560,293 H642"/>
  <path class="flow hot"  data-g="heat" d="M661,274 V262 H700"/>
  <path class="flow cold" data-g="heat" d="M700,293 H680"/>
  <path class="flow cold" data-g="heat" d="M661,312 V325 H560"/>
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

<!-- échangeurs (après les tuyaux): fond, plaques coupées à la bordure, bordure par-dessus le tout -->
<rect x="250" y="110" width="70" height="100" rx="6" style="fill:var(--card)"/>
<use href="#plates" x="250" y="110"/>
<rect class="xch" id="xEcs" x="250" y="110" width="70" height="100" rx="6" style="fill:none"/>
<rect x="250" y="330" width="70" height="100" rx="6" style="fill:var(--card)"/>
<use href="#plates" x="250" y="330"/>
<rect class="xch" id="xPool" x="250" y="330" width="70" height="100" rx="6" style="fill:none"/>

<!-- sens de l'eau sanitaire: chevron sur un fond qui masque le tuyau (froide vers l'échangeur, chaude vers la gauche) -->
<g fill="none" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
  <rect x="122" y="187" width="26" height="16" rx="6" style="fill:var(--card)" stroke="none"/>
  <path d="M131,188 L139,195 L131,202" stroke="var(--cold)"/>
  <rect x="122" y="127" width="26" height="16" rx="6" style="fill:var(--card)" stroke="none"/>
  <path d="M139,128 L131,135 L139,142" stroke="var(--warm)"/>
</g>

<!-- ===== ballon ===== -->
<g data-tip="tank" tabindex="0">
<text x="480" y="72" text-anchor="middle" class="big">${t.tank}</text>
<rect class="tank" x="400" y="90" width="160" height="350" rx="28"/>
<path class="coil" d="M560,376 H430 V392 H530 V408 H430 V424 H560"/>
<text class="tt" x="480" y="122" text-anchor="middle" id="tProbe">ECS</text>
<text class="tt" x="480" y="195" text-anchor="middle" id="tTop">Haut</text>
<text class="tt" x="480" y="270" text-anchor="middle" id="tMid">Milieu</text>
<text class="tt" x="480" y="350" text-anchor="middle" id="tBot">Bas</text>
<g stroke="#fff8" stroke-dasharray="3 4"><path d="M410,152H550M410,232H550M410,310H550"/></g>
</g>

<!-- ===== pompe de circulation solaire (retour vers les capteurs) ===== -->
<g class="pump" id="pSolar" data-tip="pSolar" tabindex="0" transform="translate(700 424)"><circle r="13"/><path d="M13 0L-6.5 11.26L-6.5-11.26Z"/></g>

<!-- ===== capteurs ===== -->
<g data-tip="coll" tabindex="0">
<rect class="box" x="720" y="-30" width="220" height="70" rx="8"/>
<text x="830" y="0" text-anchor="middle" class="big">${t.collectors}</text>
<text x="830" y="24" text-anchor="middle" id="tColl">–</text>
<g id="sky" data-tip="sky" tabindex="0" transform="translate(675 5)">
  <clipPath id="skyClip"><rect x="-40" y="-40" width="80" height="70"/></clipPath>
  <g clip-path="url(#skyClip)"><g class="sun" id="sun">
    <circle r="14"/>
    <g class="rays" stroke-width="3" stroke-linecap="round">
      <path d="M0-24V-19M0 19V24M-24 0H-19M19 0H24M-17-17l3 3M14 14l3 3M-17 17l3-3M14-14l3-3"/>
    </g>
  </g>
  <g id="moon"><circle r="14" fill="#d5dbe3"/><circle cx="7" cy="-5" r="12" style="fill:var(--card)"/></g></g>
  <line id="horizon" class="gone" x1="-30" x2="30" y1="30" y2="30"/>
  <g id="rain" class="gone fall" stroke-width="2" stroke-linecap="round"><path d="M-6 16l-2 6M3 16l-2 6M12 16l-2 6M-1 25l-2 6M8 25l-2 6"/></g>
  <g id="snow" class="gone fall slow"><circle cx="-6" cy="18" r="2"/><circle cx="4" cy="16" r="2"/><circle cx="13" cy="19" r="2"/><circle cx="-1" cy="26" r="2"/><circle cx="9" cy="27" r="2"/></g>
  <path id="bolt" class="gone" d="M4 12l-6 10h5l-3 9 9-12h-5l3-7z"/>
  <g id="fog" class="gone" stroke-width="3" stroke-linecap="round"><path d="M-22 4H22M-26 12H18M-18 20H26"/></g>
  <g id="cloud" transform="translate(-10 -8)"><circle cx="0" cy="12" r="8"/><circle cx="10" cy="6" r="11"/><circle cx="21" cy="13" r="7"/><rect x="-6" y="12" width="32" height="8" rx="4"/></g>
</g>
</g>

<!-- ===== chaudière ===== -->
<g data-tip="boiler" tabindex="0">
<rect class="box" x="700" y="95" width="160" height="110" rx="12"/>
<text x="780" y="124" text-anchor="middle" class="big">${t.boiler}</text>
<path id="boilIcon" transform="translate(762 134) scale(1.5)" d="M6,14q0,1.3 0.53,2.46t1.5,2.04Q8,18.38 8,18.27q0-0.1 0-0.22q0-0.8 0.3-1.5t0.88-1.28L12,12.5l2.83,2.78q0.57,0.57 0.88,1.28t0.3,1.5q0,0.13 0,0.22q0,0.1-0.02,0.23q0.97-0.88 1.5-2.04T18,14q0-1.25-0.46-2.36T16.2,9.65q-0.5,0.33-1.05,0.49T14.03,10.3q-1.55,0-2.69-1.03T10.03,6.75Q9.05,7.57 8.3,8.46t-1.26,1.8T6.26,12.13T6,14Zm6,1.3l-1.42,1.4q-0.28,0.28-0.43,0.63Q10,17.68 10,18.05q0,0.8 0.59,1.38T12,20t1.41-0.57T14,18.05q0-0.4-0.15-0.74T13.43,16.7L12,15.3ZM12,3V6.3q0,0.85 0.59,1.42T14.03,8.3q0.45,0 0.84-0.19q0.39-0.19 0.69-0.56L16,7q1.85,1.05 2.93,2.92T20,14q0,3.35-2.32,5.68T12,22T6.33,19.68T4,14q0-3.23 2.16-6.13Q8.33,4.97 12,3Z"/>
<path id="boilOff" transform="translate(762 134) scale(1.5)" d="M12,12Zm0,0Zm0,0Zm0,0Zm7.78,10.63L1.38,4.22L2.8,2.8L12,12l9.2,9.2l-1.43,1.43Zm-0.53-6.25l-1.52-1.53q0.13-0.45 0.2-0.91T18,13q0-1.25-0.46-2.36T16.2,8.65q-0.5,0.33-1.05,0.49T14.03,9.3q-1.55,0-2.69-1.03T10.03,5.75Q9.83,5.9 9.65,6.06Q9.48,6.22 9.28,6.4L7.85,4.97Q8.73,4.13 9.76,3.39T12,2V5.3q0,0.85 0.59,1.42T14.03,7.3q0.45,0 0.84-0.2t0.69-0.55L16,6q1.85,1.05 2.93,2.92T20,13q0,0.9-0.19,1.75t-0.56,1.63ZM12,21q-3.35,0-5.68-2.32T4,13q0-1.73 0.64-3.36T6.48,6.5L7.9,7.93Q6.95,9.17 6.48,10.45T6,13q0,1.3 0.53,2.46t1.5,2.04Q8,17.38 8,17.27q0-0.1 0-0.22q0-0.8 0.3-1.5t0.88-1.28l2.57-2.5l1.43,1.43l-2.6,2.5q-0.28,0.28-0.43,0.63Q10,16.68 10,17.05q0,0.8 0.59,1.38T12,19t1.41-0.57T14,17.05q0-0.4-0.16-0.73t-0.44-0.6l1.15-1.15l3.57,3.57Q17,19.48 15.44,20.24T12,21Z"/>
<text x="780" y="191" text-anchor="middle" class="mut" id="tBoilSub">–</text>
</g>

<g class="pump" id="pBoil" data-tip="pBoil" tabindex="0" transform="translate(630 170)"><circle r="13"/><path d="M13 0L-6.5 11.26L-6.5-11.26Z"/></g>

<!-- ===== chauffage ===== -->
<g data-tip="heat" tabindex="0">
<rect class="box" x="700" y="240" width="160" height="110" rx="12"/>
<text x="780" y="269" text-anchor="middle" class="big">${t.heating}</text>
<path id="heatIcon" transform="translate(762 279) scale(1.5)" d="M13.3,20.73q-0.15,0.13-0.31,0.2T12.63,21t-0.4-0.09t-0.35-0.24q-1.02-1.1-1.51-2.25Q9.88,17.27 9.88,16q0-0.93 0.28-1.95T11.1,11.4q0.57-1.42 0.8-2.19T12.13,7.8q0-0.85-0.38-1.59T10.58,4.72q-0.15-0.15-0.24-0.35q-0.09-0.2-0.09-0.4t0.08-0.36t0.2-0.31q0.15-0.15 0.34-0.22T11.25,3t0.38,0.07t0.33,0.2q1.1,1.02 1.64,2.15T14.13,7.8q0,0.87-0.26,1.84t-0.91,2.51q-0.63,1.5-0.85,2.3t-0.23,1.53q0,0.88 0.36,1.69t1.11,1.64q0.13,0.15 0.2,0.32T13.63,20t-0.07,0.39T13.3,20.73Zm4.88,0q-0.15,0.13-0.31,0.2T17.5,21t-0.4-0.09t-0.35-0.24q-1.02-1.1-1.51-2.24t-0.49-2.41q0-0.92 0.28-1.97t0.95-2.65q0.57-1.42 0.8-2.17T17,7.82q0-0.85-0.38-1.61T15.45,4.72Q15.3,4.57 15.23,4.39T15.15,4t0.06-0.36q0.06-0.16 0.19-0.31q0.15-0.15 0.35-0.24T16.15,3t0.36,0.07q0.16,0.07 0.31,0.2q1.1,1.02 1.64,2.15T19,7.8q0,0.87-0.26,1.84t-0.91,2.54q-0.63,1.5-0.85,2.3t-0.23,1.5q0,0.88 0.38,1.71t1.13,1.64q0.13,0.15 0.19,0.32Q18.5,19.83 18.5,20q0,0.2-0.07,0.4t-0.25,0.33Zm-9.75,0q-0.15,0.13-0.31,0.2T7.75,21t-0.4-0.09T7,20.68q-1.02-1.1-1.51-2.24T5,16.02q0-0.92 0.28-1.97T6.23,11.4Q6.8,9.98 7.03,9.23t0.22-1.4q0-0.85-0.38-1.61T5.7,4.72Q5.53,4.57 5.45,4.39T5.38,4T5.45,3.63T5.65,3.3Q5.8,3.15 5.99,3.07T6.38,3q0.2,0 0.38,0.07t0.33,0.2Q8.18,4.3 8.71,5.41T9.25,7.8Q9.25,8.67 9,9.64T8.1,12.15q-0.62,1.5-0.85,2.3T7.03,15.98q0,0.88 0.36,1.71T8.5,19.33q0.13,0.15 0.19,0.32Q8.75,19.83 8.75,20q0,0.2-0.07,0.4T8.43,20.73Z"/>
<text x="780" y="336" text-anchor="middle" id="tHeat">–</text>
</g>
<g class="pump" id="pHeat" data-tip="pHeat" tabindex="0" transform="translate(598 293)"><circle r="13"/><path d="M13 0L-6.5 11.26L-6.5-11.26Z"/></g>
<g data-tip="mixer" tabindex="0">
<rect x="608" y="240" width="72" height="86" fill="transparent"/>
<path d="M661,293L633,265" stroke="var(--fg)" stroke-width="3"/>
<g transform="translate(661 293)" stroke="var(--fg)" stroke-width="2" stroke-linejoin="round">
  <path d="M-19-10L-19 10L0 0ZM19-10L19 10L0 0ZM-10-19L10-19L0 0ZM-10 19L10 19L0 0Z" style="fill:var(--card)"/>
</g>
<rect class="box" id="motor" x="611" y="243" width="22" height="22" rx="4"/>
<text x="622" y="259" text-anchor="middle" style="font-weight:700">M</text>
</g>

<!-- ===== ECS ===== -->
<g data-tip="ecs" tabindex="0">
<text x="20" y="122" class="big">${t.hotWater}</text>
<rect x="250" y="110" width="70" height="100" fill="transparent"/>
</g>
<g class="pump" id="pEcs" data-tip="pEcs" tabindex="0" transform="translate(360 135)"><circle r="13"/><path d="M13 0L-6.5 11.26L-6.5-11.26Z"/></g>
<path id="ctl" class="ctl" d="M218,124 V95 H360 V121"/>
<rect x="205" y="124" width="26" height="22" rx="4" class="box"/>
<rect id="mag" x="209" y="130" width="8" height="10" rx="2" fill="var(--mut)"/>
<text x="20" y="182" class="big">${t.coldWater}</text>

<!-- ===== piscine ===== -->
<g data-tip="pool" tabindex="0">
<rect x="250" y="330" width="70" height="100" fill="transparent"/>
</g>
<g class="pump" id="pPool" data-tip="pPool" tabindex="0" transform="translate(360 355)"><circle r="13"/><path d="M13 0L-6.5 11.26L-6.5-11.26Z"/></g>
<g data-tip="pool" tabindex="0">
<rect class="box" x="20" y="330" width="150" height="100" rx="12"/>
<text x="95" y="351" text-anchor="middle" class="big">${t.pool}</text>
<path id="poolIcon" transform="translate(75.8 358) scale(1.6)" d="M2,21V19q0.95,0 1.43-0.5T5.3,18t1.92,0.5T8.65,19t1.43-0.5T12,18t1.93,0.5T15.35,19t1.43-0.5T18.7,18t1.88,0.5T22,19v2q-1.47,0-1.94-0.5T18.7,20t-1.42,0.5T15.35,21t-1.93-0.5T12,20t-1.42,0.5T8.65,21T6.73,20.5T5.3,20T3.94,20.5Q3.48,21 2,21Zm0-4.5v-2q0.95,0 1.43-0.5T5.3,13.5T7.24,14t1.41,0.5q0.9,0 1.43-0.5T12,13.5T13.93,14t1.43,0.5T16.78,14t1.92-0.5T20.58,14T22,14.5v2q-1.47,0-1.94-0.5T18.7,15.5T17.31,16t-1.96,0.5q-1.43,0-1.94-0.5T12,15.5q-0.95,0-1.41,0.5T8.65,16.5T6.69,16T5.3,15.5T3.94,16Q3.48,16.5 2,16.5Zm4.9-5.1l3.33-3.32l-1-1Q8.4,6.25 7.48,5.88T5.2,5.5V3Q7.08,3 8.3,3.41T10.7,5l6.4,6.4q-0.43,0.28-0.82,0.44T15.35,12q-0.9,0-1.43-0.5T12,11t-1.92,0.5T8.65,12q-0.53,0-0.92-0.16Q7.33,11.68 6.9,11.4ZM18.48,3.74Q19.2,4.47 19.2,5.5q0,1.05-0.73,1.77T16.7,8T14.93,7.27T14.2,5.5q0-1.03 0.72-1.76T16.7,3t1.78,0.74Z"/>
<text x="95" y="419" text-anchor="middle" id="tPool">–</text>
</g>

<text x="20" y="5" class="big" id="tOut">–</text>
</svg>`;

const fmt = (n) => (n == null || Number.isNaN(n) ? '–' : Number(n).toFixed(1).replace('.', ','));
const pct = (n) => (n == null ? '–' : Math.round(n) + ' %');
const col = (t) => (t == null ? 'hsl(210 10% 55%)' : `hsl(${Math.max(0, Math.min(220, 220 - (t - 10) / 65 * 220))} 75% 48%)`);
const deg = (n) => (n == null || Number.isNaN(n) ? '–' : fmt(n) + ' °C');
const diff = (a, b) => (a == null || b == null ? '–' : (a - b >= 0 ? '+' : '') + fmt(a - b) + ' K');
// useful energy above 40 °C: 1000 L x 1.163 Wh/(L.K), mean of the 3 tank probes
// ponytail: plain mean of the 3 probes, weight by height if the figure looks wrong
const kwh = (s) => (s.top == null || s.mid == null || s.bot == null ? null : Math.max(0, 1.163 * ((s.top + s.mid + s.bot) / 3 - 40)));
const esc = (x) => String(x).replace(/[&<>]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'})[c]);

// sky: day or night from the OpenWeatherMap icon (01d / 01n), clouds from the coverage and the condition code
// dawn / dusk: within 40 min of sunrise / sunset, from the time shown (live or replayed)
const minutes = (hhmm) => { const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm || ''); return m ? +m[1] * 60 + +m[2] : null; };
function skyOf(s, tp) {
  const at = new Date((s.ts ?? Date.now() / 1000) * 1000), now = at.getHours() * 60 + at.getMinutes();
  const rise = minutes(s.sunrise), set = minutes(s.sunset);
  const known = rise != null && set != null;
  const dawn = known && Math.abs(now - rise) <= 40, dusk = known && Math.abs(now - set) <= 40;
  const night = known ? now < rise || now >= set : s.icon ? s.icon.endsWith('n') : (at.getHours() < 7 || at.getHours() >= 19);
  // one body at a time on the horizon: the sun sets then the moon rises; the moon sets then the sun rises
  const sun = !night ? (dawn || dusk ? 'low' : 'up') : 'down';
  const moon = night ? (dawn || dusk ? 'low' : 'up') : 'down';
  const clouds = s.clouds ?? 0, code = s.wcode ?? 800;
  const storm = code >= 200 && code < 300, snow = code >= 600 && code < 700, fog = code >= 700 && code < 800;
  const rain = storm || (code >= 300 && code < 600);
  const cloudy = rain || snow || code > 800 || clouds >= 25, overcast = rain || snow || fog || code === 804 || clouds >= 85;
  const label = storm ? tp.skyStorm : rain ? tp.skyRain : snow ? tp.skySnow : fog ? tp.skyFog : overcast ? tp.skyOvercast : cloudy ? tp.skyCloudy : night ? tp.skyClearNight : tp.skyClear;
  const twilight = dawn ? tp.sunriseNow : dusk ? tp.sunsetNow : null;
  return {night, sun, moon, twilight: dawn || dusk, cloudy, overcast, rain, snow, storm, fog,
    label: twilight ? `${label} (${twilight})` : night && !(label === tp.skyClearNight) ? `${label} (${tp.night})` : label};
}

// panel values (const.DASHBOARD names) and weather -> what the schematic and its tooltips read
const toCur = (v, w, ts) => ({
  ts,
  coll: v.coll, ecsP: v.ecs_probe, top: v.tank_top, mid: v.tank_mid, bot: v.tank_bottom, solarPump: v.solar_pump,
  bPump: v.boiler_pump, contact: v.burner, boilT: v.boiler_temp, heat: v.heating_pump > 0, flow: v.flow, pool: v.pool,
  poolPump: v.pool_pump, out: v.outdoor, mixer: v.mixer, room: v.room, roomSet: v.room_set, flowSet: v.flow_set,
  tankSet: v.tank_set, ecsSet: v.ecs_set, ecsPump: v.ecs_pump,
  icon: w.icon, wcode: w.code, clouds: w.clouds, wind: w.wind, sunrise: w.sunrise, sunset: w.sunset,
  fcTemp: w.forecast_temp, fcClouds: w.forecast_clouds,
});

// history tab: temperature lines in fixed categorical order (--s1..--s7), then the on/off lanes
const HIST_LINES = ['tank_top', 'tank_mid', 'tank_bottom', 'coll', 'flow', 'room', 'outdoor'];
const HIST_LANES = [['burner', 'var(--red)'], ['boiler_pump', 'var(--hot)'], ['solar_pump', 'var(--solar)'], ['heating_pump', 'var(--warm)'], ['boost', 'var(--ok)']];
const HIST = {L: 150, R: 24, W: 1000, PH: 200, LH: 22};
// stretches of 10 min or more where Home Assistant recorded nothing of the installation, as [from, to) unix times
// (before the integration or its entities were enabled, recorder stopped...), so they read as missing, not as all stopped
const NOT_INSTALLATION = new Set(['boost', 'clouds', 'code', 'icon']);
function gaps(h) {
  if (h.gaps) return h.gaps;
  const cols = h.series.map((k, i) => (NOT_INSTALLATION.has(k) ? 0 : i + 1)).filter(Boolean), out = [];
  let from = null;
  h.points.forEach((p, i) => {
    const empty = cols.every((j) => p[j] == null), last = i === h.points.length - 1;
    if (empty && from == null) from = p[0];
    if (from != null && (!empty || last)) {
      const to = empty ? p[0] + 60 : p[0];
      if (to - from >= 600) out.push([from, to]);
      from = null;
    }
  });
  return (h.gaps = out);
}
const inGap = (h, ts) => gaps(h).some(([a, b]) => ts >= a && ts < b);

class OkofenDashboard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: 'open'});
    this._cur = {};
    this._src = '';
    this._tipKey = null;
    this._tab = 'scheme';
    this._hist = null;
    this._histAt = 0;
    this._off = new Set();
    this._replay = null;  // index in the history while replaying, null: live
    this._live = {};
    this._playing = null;
  }

  set hass(hass) {
    const lang = hass.locale?.language || hass.language;  // the language of the user's profile
    const changed = this._userLang && lang !== this._userLang;
    this._hass = hass;
    this._userLang = lang;
    this.toggleAttribute('dark', !!(hass.themes && hass.themes.darkMode));
    if (!this._timer) { this._poll(); this._timer = setInterval(() => this._poll(), 15000); }
    else if (changed) this._poll();
  }

  set narrow(_) {}
  set route(_) {}
  set panel(_) {}

  disconnectedCallback() { clearInterval(this._timer); this._timer = null; this._pause(); }

  _q(id) { return this.shadowRoot.getElementById(id); }

  _build() {
    const t = this._t;
    this.shadowRoot.innerHTML = `<style>${CSS}</style>
<main>
<h1>${t.title}</h1>
<p class="sub">${t.sub} <span id="src" class="badge"></span></p>
<nav role="tablist">${['scheme', 'solar', 'history'].map((k) => `<button role="tab" data-tab="${k}" aria-selected="${this._tab === k}">${t.solar.tabs[k]}</button>`).join('')}</nav>
<div class="card" id="scheme" ${this._tab === 'scheme' ? '' : 'hidden'}>${svgFor(t)}
<div class="replay" id="replay" hidden><button id="rpPlay" aria-label="${t.replay.play}">▶</button>
<div class="rpTrack" id="rpTrack"><svg id="rpStrip" viewBox="0 0 1000 58" preserveAspectRatio="none" aria-hidden="true"></svg>
<input type="range" id="rpRange" min="0" max="0" value="0" aria-label="${t.replay.position}"></div>
<button id="rpNow" aria-label="${t.replay.now}"><span class="t" id="rpTime"></span><span class="n">${t.replay.now}</span><span class="z" id="rpSize"></span><span class="z" id="rpSize2"></span><span class="z">${t.replay.live}</span></button></div></div>
<div class="card pad solar" id="solar" ${this._tab === 'solar' ? '' : 'hidden'}></div>
<div class="card pad hist" id="history" ${this._tab === 'history' ? '' : 'hidden'}></div>
<div id="tip" hidden role="tooltip"></div>
</main>`;
    this.shadowRoot.querySelectorAll('path.flow').forEach((p) => {
      const track = p.cloneNode();
      track.removeAttribute('style');
      track.setAttribute('class', 'track');
      p.before(track);
    });
    this.shadowRoot.querySelector('nav').addEventListener('click', (e) => {
      const b = e.target.closest('[data-tab]');
      if (!b) return;
      this._tab = b.dataset.tab;
      this.shadowRoot.querySelectorAll('nav button').forEach((x) => x.setAttribute('aria-selected', x === b));
      ['scheme', 'solar', 'history'].forEach((k) => this._hide(k, this._tab !== k));
      this._hideTip();
      if (this._tab === 'history') this._loadHistory();
    });
    this._q('solar').addEventListener('click', (e) => {
      const b = e.target.closest('[data-switch]');
      if (b && this._boost?.switch) this._hass.callService('switch', b.dataset.switch, {entity_id: this._boost.switch}).then(() => this._poll());
    });
    this._q('rpRange').addEventListener('mousemove', (e) => this._rpHover(e));
    this._q('rpRange').addEventListener('mouseleave', () => this._hideTip());
    this._q('rpRange').addEventListener('input', (e) => { this._pause(); this._seek(+e.target.value); });
    this._q('rpPlay').addEventListener('click', () => (this._playing ? this._pause() : this._play()));
    this._q('rpNow').addEventListener('click', () => { this._pause(); this._seek(null); });
    const hist = this._q('history');
    hist.addEventListener('click', (e) => {
      const b = e.target.closest('[data-series]');
      if (!b) return;
      const k = b.dataset.series;
      this._off.has(k) ? this._off.delete(k) : this._off.add(k);
      this._renderHistory();
    });
    hist.addEventListener('mousemove', (e) => this._histHover(e));
    hist.addEventListener('mouseleave', () => { this._hideTip(); hist.querySelectorAll('.cross').forEach((l) => l.setAttribute('hidden', '')); });
    const svg = this.shadowRoot.querySelector('svg');
    svg.addEventListener('mousemove', (e) => {
      const g = e.target.closest('[data-tip]');
      if (!g) return this._hideTip();
      if (g.dataset.tip !== this._tipKey) this._showTip(g.dataset.tip);
      this._placeTip(e.clientX, e.clientY);
    });
    svg.addEventListener('mouseleave', () => this._hideTip());
    svg.addEventListener('focusin', (e) => {
      const g = e.target.closest('[data-tip]');
      if (!g) return;
      const r = g.getBoundingClientRect();
      this._showTip(g.dataset.tip);
      this._placeTip(r.left + r.width / 2, r.bottom);
    });
    svg.addEventListener('focusout', () => this._hideTip());
    this.shadowRoot.addEventListener('keydown', (e) => e.key === 'Escape' && this._hideTip());
    this._render();
  }

  async _poll() {
    try {
      const res = await this._hass.callWS({type: 'okofen_portal/dashboard', language: this._userLang});
      if (!this._t || res.language !== this._lang) { this._t = res.strings; this._lang = res.language; this._build(); this._renderHistory(); this._renderReplay(); }
      this._boost = res.boost;
      this._w = res.weather || {};
      this._live = toCur(res.values || {}, this._w, Date.now() / 1000);
      if (this._replay == null) this._cur = this._live;
      this._src = `${this._t.updated} ${new Date().toLocaleTimeString(this._lang)}`;
    } catch (e) {
      this._cur = this._live = {};
      this._boost = null;
      this._src = this._t ? this._t.error : '';
    }
    if (this._t) this._render();
    // every 2 min, every 30 s while there is almost nothing yet
    const histEvery = this._hist && this._hist.points.length >= 2 ? 120000 : 30000;
    if (this._tab !== 'solar' && Date.now() - this._histAt > histEvery) this._loadHistory();
  }

  async _loadHistory() {
    this._histAt = Date.now();
    try { this._hist = await this._hass.callWS({type: 'okofen_portal/history'}); } catch (e) { this._hist = null; }
    this._renderHistory();
    this._renderReplay();
  }

  _group(g, on, dur) {
    this.shadowRoot.querySelectorAll(`.flow[data-g="${g}"]`).forEach((p) => {
      p.classList.toggle('on', !!on);
      p.style.setProperty('--d', dur + 's');
    });
  }

  _on(id, on) { const el = this._q(id); if (el) el.classList.toggle('on', !!on); }
  _hide(id, hidden) { const el = this._q(id); if (el) el.toggleAttribute('hidden', !!hidden); } // .hidden does not exist on SVG elements
  _set(id, text) { const el = this._q(id); if (el) el.textContent = text; }
  _stop(id, color) { const el = this._q(id); if (el) el.setAttribute('stop-color', color); }

  _render() {
    if (!this._t || !this._q('src')) return;
    const t = this._t, s = this._cur, draw = s.ecsPump > 0;
    this._q('src').textContent = this._replay != null ? this._rpLabel : this._src;
    this._stop('gE', col(s.ecsP)); this._stop('g0', col(s.top)); this._stop('g1', col(s.mid)); this._stop('g2', col(s.bot));
    this._q('poolIcon').style.fill = col(s.pool);
    this._set('tProbe', `${t.probe} ${deg(s.ecsP)}`);
    this._set('tTop', `${t.top} ${deg(s.top)}`);
    this._set('tMid', `${t.mid} ${deg(s.mid)}`);
    this._set('tBot', `${t.bot} ${deg(s.bot)}`);
    this._set('tColl', deg(s.coll));
    const burner = s.contact > 0;
    this._hide('boilIcon', !burner); this._hide('boilOff', burner);
    this._set('tBoilSub', deg(s.boilT));
    this._set('tHeat', `${t.room} ${deg(s.room)}`);
    this._set('tPool', deg(s.pool));
    this._set('tOut', `${t.outdoor} ${deg(s.out)}`);
    this._group('solar', s.solarPump > 0, 3.2 - 2.4 * (s.solarPump || 0) / 100);
    this._group('boiler', s.bPump > 0, 2);
    this._group('heat', s.heat, 2.4);
    this._group('pool', s.poolPump > 0, 3.2 - 2.4 * (s.poolPump || 0) / 100);
    this._group('ecs', draw, 1.4);
    this._on('pBoil', s.bPump > 0); this._on('pSolar', s.solarPump > 0);
    this._on('pHeat', s.heat); this._on('heatIcon', s.heat);
    this._on('pPool', s.poolPump > 0); this._on('pEcs', draw);
    this._on('xPool', s.poolPump > 0); this._on('xEcs', draw); this._on('ctl', draw);
    this._on('sun', s.coll > 40); this._on('motor', s.mixer > 0);
    const sky = skyOf(s, t.tip);
    const fade = (id, gone) => this._q(id).classList.toggle('gone', !!gone);  // fades instead of hiding
    // the sun and the moon slide under the horizon and out of it; an overcast sky hides both
    for (const body of ['sun', 'moon']) {
      const el = this._q(body);
      el.classList.toggle('low', sky[body] === 'low');
      el.classList.toggle('down', sky[body] === 'down');
      fade(body, sky.overcast);
    }
    fade('cloud', !sky.cloudy);
    fade('horizon', !sky.twilight || sky.overcast);
    this._q('horizon').classList.toggle('night', sky.night);
    this._q('cloud').classList.toggle('rain', sky.rain);
    this._q('cloud').classList.toggle('snow', sky.snow);
    fade('rain', !sky.rain); fade('snow', !sky.snow); fade('bolt', !sky.storm); fade('fog', !sky.fog);
    const mag = this._q('mag'); if (mag) mag.setAttribute('x', draw ? 221 : 209);
    if (this._tipKey) this._showTip(this._tipKey);
    this._renderSolar();
  }

  // ===== solar tab: the solar boost, its conditions with their values and thresholds =====
  _renderSolar() {
    const t = this._t.solar, b = this._boost, el = this._q('solar');
    if (!b) { el.innerHTML = `<p class="mut">${esc(this._t.error)}</p>`; return; }
    const hhmm = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
    const fmtCheck = (c) => {
      if (c.value == null) return ['', ''];
      switch (c.id) {
        case 'outside_window': return [hhmm(c.value), `${hhmm(c.limit[0])} – ${hhmm(c.limit[1])}`];
        case 'cloudy': return [pct(c.value), `≤ ${pct(c.limit)}`];
        case 'burner': return [c.value ? t.on : t.off, ''];
        case 'manual': return [deg(c.value), `= ${deg(c.limit)}`];
        case 'tank_cold': case 'hot_water_low': return [deg(c.value), `≥ ${deg(c.limit)}`];
        default: return [deg(c.value), `< ${deg(c.limit)}`];
      }
    };
    const reason = t.reasons[b.reason] || (t.checks[b.reason] ? `${t.waitingFor} ${t.checks[b.reason]}` : b.reason);
    const rows = b.checks.map((c) => {
      const [value, limit] = fmtCheck(c);
      return `<tr class="${c.ok ? 'ok' : 'no'}"><td>${c.ok ? '✓' : '✗'}</td><td>${esc(t.checks[c.id] || c.id)}</td><td class="v">${esc(value)}</td><td class="l">${esc(limit)}</td></tr>`;
    }).join('');
    const ses = b.session;
    el.innerHTML = `<div class="head"><span class="state ${b.state}">${esc(t.states[b.state] || b.state)}</span><span class="mut">${esc(reason)}</span>
${b.switch ? `<button data-switch="${b.enabled ? 'turn_off' : 'turn_on'}">${esc(b.enabled ? t.turnOff : t.turnOn)}</button>` : ''}</div>
<p class="mut">${esc(t.intro)}</p>
<h2>${esc(ses ? t.keepIf : t.startIf)}</h2><table>${rows}</table>
${ses ? `<h2>${esc(t.current)}</h2><p>${esc(t.since)} ${new Date(ses.since * 1000).toLocaleTimeString(this._lang, {hour: '2-digit', minute: '2-digit'})} · ${esc(t.comfort)} ${deg(ses.comfort)} → ${deg(ses.target)} · ${esc(t.heads)} ${Object.keys(ses.heads).length}</p>` : ''}
<h2>${esc(t.settings)}</h2><p>${esc(t.comfort)} ${deg(b.target)} · ${esc(t.heads)} ${b.heads.length ? esc(b.heads.map((e) => this._hass.states[e]?.attributes.friendly_name || e).join(', ')) : '–'}</p><p class="mut">${esc(t.settingsHint)}</p>`;
  }

  // ===== replay under the schematic: yesterday and today, play / pause, back to now =====
  _renderReplay() {
    const range = this._q('rpRange'), strip = this._q('rpStrip'), h = this._hist;
    if (!range) return;
    const n = h ? h.points.length : 0;
    // always shown, greyed out until the integration has recorded something (it starts at install)
    this._q('replay')?.removeAttribute('hidden');
    range.disabled = this._q('rpPlay').disabled = n < 2;
    range.max = Math.max(0, n - 1);
    range.value = this._replay ?? range.max;
    this._rpTime();
    if (!n) {
      this._q('rpTrack').querySelectorAll('span').forEach((e) => e.remove());
      strip.innerHTML = '<rect x="0" y="12" width="1000" height="6" rx="3" fill="var(--line)"/>';
      return;
    }
    // progression strip: day boundaries and when the burner and the solar pump ran, so the moments to look at stand out
    const idx = Object.fromEntries(h.series.map((k, i) => [k, i + 1])), t0 = h.points[0][0], span = Math.max(60, h.points[n - 1][0] - t0);
    const x = (ts) => ((ts - t0) / span * 1000).toFixed(1);
    let g = `<rect x="0" y="12" width="1000" height="6" rx="3" fill="var(--line)"/>`;
    const day0 = new Date(); day0.setHours(0, 0, 0, 0);
    const midnight = day0.getTime() / 1000;
    if (midnight > t0) g += `<line x1="${x(midnight)}" x2="${x(midnight)}" y1="0" y2="58" stroke="var(--mut)" stroke-dasharray="2 2" vector-effect="non-scaling-stroke"/>`;
    // day names as page text (the strip is stretched, its own text would be too)
    const tr = this._q('rpTrack');
    tr.querySelectorAll('span').forEach((e) => e.remove());
    const label = (text, left) => tr.insertAdjacentHTML('beforeend', `<span style="left:${left}">${esc(text)}</span>`);
    // a day's name goes where its data starts when its first hours were not recorded
    const shown = (ts) => gaps(h).find(([a, b]) => ts >= a && ts < b)?.[1] ?? ts;
    if (midnight > t0 && shown(t0) < midnight) label(this._t.history.yesterday, `calc(${x(shown(t0)) / 10}% + 4px)`);
    if (midnight > t0) label(this._t.history.today, `calc(${x(shown(midnight)) / 10}% + 4px)`);
    else label(this._t.history.today, '0');
    // nothing recorded: the track is cut to a dotted line
    for (const [a, b] of gaps(h)) {
      g += `<rect x="${x(a)}" y="11" width="${x(b) - x(a)}" height="8" fill="var(--bg)"/><line x1="${x(a)}" x2="${x(b)}" y1="15" y2="15" stroke="var(--mut)" stroke-dasharray="2 4" vector-effect="non-scaling-stroke"/>`;
    }
    // under the track, below the cursor, so it never hides them; named on hover (_rpHover)
    const runs = this._rpRuns = [];
    this._rpSpan = [t0, span];
    // same order and colours as the History tab's lanes, the pool pump last
    [['burner', 'var(--red)'], ['boiler_pump', 'var(--hot)'], ['solar_pump', 'var(--solar)'], ['heating_pump', 'var(--warm)'], ['pool_pump', 'var(--cold)']].forEach(([k, color], row) => {
      const y = 27 + row * 6;
      if (!idx[k]) return;
      let run = null;
      h.points.forEach((p, i) => {
        const on = p[idx[k]] > 0, last = i === n - 1;
        if (on && run == null) run = p[0];
        if (run != null && (!on || last)) { runs.push([k, run, p[0]]); g += `<rect x="${x(run)}" y="${y}" width="${Math.max(2, x(p[0]) - x(run))}" height="4" rx="2" fill="${color}"/>`; run = null; }
      });
    });
    strip.innerHTML = g;
  }

  // the time under the mouse, and the burner or solar pump run there with its start, end and duration
  _rpHover(e) {
    const h = this._hist, box = e.currentTarget.getBoundingClientRect();
    if (!h || h.points.length < 2 || !this._rpSpan) return;
    const [t0, span] = this._rpSpan, ts = t0 + (e.clientX - box.left) / box.width * span, near = span / box.width * 6;  // 6 px either side
    const hm = (t) => new Date(t * 1000).toLocaleTimeString(this._lang, {hour: '2-digit', minute: '2-digit'});
    const day0 = new Date(); day0.setHours(0, 0, 0, 0);
    const rows = this._rpRuns.filter(([, a, b]) => ts >= a - near && ts <= b + near)
      .map(([k, a, b]) => `<div><span>${esc(this._t.history.series[k] || this._t.tip.poolPump)}</span>${hm(a)}–${hm(b)} · ${Math.max(1, Math.round((b - a) / 60))} min</div>`);
    if (inGap(h, ts)) rows.push(`<div>${esc(this._t.history.noData)}</div>`);
    const tip = this._q('tip');
    tip.innerHTML = `<b>${esc(ts * 1000 < day0 ? this._t.history.yesterday : this._t.history.today)} ${hm(ts)}</b>${rows.join('')}`;
    tip.hidden = false;
    this._placeTip(e.clientX, e.clientY);
  }

  _rpTime() {
    const el = this._q('rpTime'), btn = this._q('rpNow'), h = this._hist, tr = this._t.replay;
    if (!el) return;
    const p = this._replay != null && h ? h.points[this._replay] : null;
    const hm = (d) => d.toLocaleTimeString(this._lang, {hour: '2-digit', minute: '2-digit'});
    // the widest times (AM and PM in 12-hour languages), so the button does not move
    this._q('rpSize').textContent = hm(new Date(2000, 0, 1, 10, 58));
    this._q('rpSize2').textContent = hm(new Date(2000, 0, 1, 22, 58));
    btn.classList.toggle('past', !!p);
    const empty = !h || h.points.length < 2;
    btn.title = empty ? this._t.history.empty : '';  // explains where the history comes from
    if (!p) { el.textContent = empty ? tr.empty : tr.live; return; }
    const d = new Date(p[0] * 1000), day0 = new Date(); day0.setHours(0, 0, 0, 0);
    el.textContent = hm(d);
    this._rpLabel = `${d < day0 ? this._t.history.yesterday : this._t.history.today} ${hm(d)}`;  // with the day, for the badge at the top
    if (inGap(h, p[0])) { btn.classList.remove('past'); btn.title = this._t.history.empty; }  // greyed: nothing recorded at that time
  }

  _seek(i) {
    const h = this._hist;
    if (i == null || !h || i >= h.points.length - 1) {
      this._replay = null;
      this._cur = this._live;
    } else {
      this._replay = i;
      const p = h.points[i], v = Object.fromEntries(h.series.map((k, j) => [k, p[j + 1]]));
      // the sky of that moment when it was recorded (forecast, wind and sun times stay the current ones)
      const w = 'icon' in v ? {...this._w, clouds: v.clouds, code: v.code, icon: v.icon} : this._w || {};
      this._cur = toCur(v, w, p[0]);
    }
    const range = this._q('rpRange');
    if (range) range.value = this._replay ?? range.max;
    this._rpTime();
    this._render();
  }

  _play() {
    const h = this._hist;
    if (!h || !h.points.length) return;
    // from live: start at the first recorded minute, not in the empty hours before it
    if (this._replay == null) this._replay = Math.max(0, h.points.findIndex((p) => !inGap(h, p[0])));
    this._playing = setInterval(() => {
      const next = this._replay + 5;  // 5 min of history every 100 ms: two days in about a minute
      if (next >= h.points.length - 1) { this._pause(); this._seek(null); } else this._seek(next);
    }, 100);
    this._q('rpPlay').textContent = '⏸';
    this._q('rpPlay').setAttribute('aria-label', this._t.replay.pause);
  }

  _pause() {
    clearInterval(this._playing);
    this._playing = null;
    const b = this._q('rpPlay');
    if (b) { b.textContent = '▶'; b.setAttribute('aria-label', this._t.replay.play); }
  }

  // ===== history tab: today and yesterday, temperatures on one °C axis, on/off lanes below =====
  _renderHistory() {
    const el = this._q('history'), t = this._t?.history;
    if (!el || !t) return;
    const h = this._hist;
    if (!h || !h.points.length) { el.innerHTML = `<p class="mut">${esc(h ? t.empty : this._t.error)}</p>`; return; }
    const idx = Object.fromEntries(h.series.map((k, i) => [k, i + 1]));
    const lines = HIST_LINES.filter((k) => idx[k]), shown = lines.filter((k) => !this._off.has(k));
    const day0 = new Date(); day0.setHours(0, 0, 0, 0);
    const days = [[t.today, day0.getTime() / 1000], [t.yesterday, day0.getTime() / 1000 - 86400]];
    let lo = Infinity, hi = -Infinity;
    for (const p of h.points) for (const k of shown) { const v = p[idx[k]]; if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }
    if (lo > hi) { lo = 0; hi = 60; }
    lo = Math.floor(lo / 10) * 10; hi = Math.max(lo + 10, Math.ceil(hi / 10) * 10);
    this._histGeo = {days, idx, lo, hi};
    const legend = lines.map((k, i) => `<button data-series="${k}" aria-pressed="${!this._off.has(k)}"><i style="background:var(--s${i + 1})"></i>${esc(t.series[k])}</button>`).join('');
    el.innerHTML = `<div class="legend">${legend}</div>` + days.map(([label, start], d) => `<h2>${esc(label)}</h2>${this._histSvg(h, start, d, lines, idx, lo, hi)}`).join('');
  }

  _histSvg(h, start, d, lines, idx, lo, hi) {
    const t = this._t.history, {L, R, W, PH, LH} = HIST, y = (v) => PH - (v - lo) / (hi - lo) * PH + 6, x = (ts) => L + (ts - start) / 86400 * (W - L - R);
    const pts = h.points.filter((p) => p[0] >= start && p[0] < start + 86400);
    let g = '';
    for (let v = lo; v <= hi; v += 10) g += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v} °C</text>`;
    for (let hr = 0; hr <= 24; hr += 3) g += `<text x="${x(start + hr * 3600)}" y="${PH + 38 + HIST_LANES.length * LH}" text-anchor="${hr === 24 ? 'end' : hr ? 'middle' : 'start'}">${String(hr).padStart(2, '0')}h</text>`;
    lines.forEach((k, i) => {
      if (this._off.has(k)) return;
      let path = '', prev = null;
      for (const p of pts) {
        const v = p[idx[k]];
        if (v == null) { prev = null; continue; }
        path += `${prev == null || p[0] - prev > 180 ? 'M' : 'L'}${x(p[0]).toFixed(1)},${y(v).toFixed(1)}`;
        prev = p[0];
      }
      if (path) g += `<path class="line" style="stroke:var(--s${i + 1})" d="${path}"/>`;
    });
    HIST_LANES.forEach(([k, color], j) => {
      const top = PH + 20 + j * LH;
      g += `<text x="${L - 8}" y="${top + 14}" text-anchor="end">${esc(t.series[k])}</text><rect x="${L}" y="${top}" width="${W - L - R}" height="${LH - 4}" rx="2" fill="var(--line)" opacity=".5"/>`;
      let run = null;
      const close = (end) => { g += `<rect x="${x(run)}" y="${top}" width="${Math.max(1.5, x(end) - x(run))}" height="${LH - 4}" rx="2" fill="${color}"/>`; run = null; };
      for (const p of pts) {
        const on = p[idx[k]] > 0;
        if (on && run == null) run = p[0];
        else if (!on && run != null) close(p[0]);
      }
      if (run != null) close(pts[pts.length - 1][0] + 60);
    });
    const H = PH + 46 + HIST_LANES.length * LH, bottom = PH + 16 + HIST_LANES.length * LH;
    // nothing recorded: hatched over the plot and the lanes, so it does not read as everything stopped (the tooltip says why)
    for (const [a, b] of gaps(h)) {
      const x0 = x(Math.max(a, start)), x1 = x(Math.min(b, start + 86400));
      if (x1 - x0 < 1) continue;
      g += `<rect x="${x0}" y="0" width="${x1 - x0}" height="${bottom}" fill="url(#gap${d})"/>`;
    }
    const hatch = `<defs><pattern id="gap${d}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="var(--bg)"/><line x1="0" y1="0" x2="0" y2="8" stroke="var(--mut)" stroke-opacity=".35" stroke-width="2"/></pattern></defs>`;
    return `<svg viewBox="0 0 ${W} ${H}" data-day="${d}" role="img" aria-label="${esc(t.aria)}">${hatch}${g}<line class="cross" hidden y1="0" y2="${H - 18}"/></svg>`;
  }

  _histHover(e) {
    const svg = e.target.closest('svg[data-day]'), geo = this._histGeo;
    if (!svg || !geo || !this._hist) return;
    const {L, R, W} = HIST, box = svg.getBoundingClientRect(), px = (e.clientX - box.left) / box.width * W;
    const [label, start] = geo.days[+svg.dataset.day];
    const ts = start + (px - L) / (W - L - R) * 86400;
    let best = null;
    for (const p of this._hist.points) if (Math.abs(p[0] - ts) < 180 && (!best || Math.abs(p[0] - ts) < Math.abs(best[0] - ts))) best = p;
    this.shadowRoot.querySelectorAll('.cross').forEach((l) => l.setAttribute('hidden', ''));
    if (px < L || px > W - R || !best) { this._hideTip(); return; }
    const cross = svg.querySelector('.cross');
    cross.removeAttribute('hidden'); cross.setAttribute('x1', px); cross.setAttribute('x2', px);
    const t = this._t.history, tp = this._t.tip, val = (k) => best[geo.idx[k]];
    const rows = [...HIST_LINES.filter((k) => geo.idx[k] && !this._off.has(k)).map((k) => [t.series[k], deg(val(k))]),
      ...HIST_LANES.map(([k]) => [t.series[k], val(k) > 0 ? tp.running : tp.stopped])];
    const tip = this._q('tip'), gap = inGap(this._hist, best[0]);
    tip.innerHTML = `<b>${esc(label)} ${new Date(best[0] * 1000).toLocaleTimeString(this._lang, {hour: '2-digit', minute: '2-digit'})}</b>` +
      (gap ? `<div>${esc(t.noData)}</div>` : '') +
      (gap ? [] : rows).map(([k, v]) => `<div><span>${esc(k)}</span>${esc(v)}</div>`).join('');
    tip.hidden = false;
    this._placeTip(e.clientX, e.clientY);
  }

  // ===== tooltips: the values of an element and a few figures computed from them =====
  _tip(key) {
    const t = this._t, tp = t.tip, s = this._cur, draw = s.ecsPump > 0;
    const state = (on, p) => (on ? (p == null ? tp.running : `${tp.running} · ${Math.round(p)} %`) : tp.stopped);
    const pump = (p) => state(p > 0, p);
    const set = (x) => (x == null || x <= 8 ? tp.inactive : deg(x)); // 8 °C: the idle setpoint
    const burner = s.contact > 0 ? tp.burnerOn : t.off;
    const sky = skyOf(s, tp);
    const energy = kwh(s);
    return {
      sky: [tp.weather, [tp.sky, sky.label], [tp.clouds, s.clouds == null ? '–' : s.clouds + ' %'], [tp.wind, s.wind || '–'], [t.outdoor, deg(s.out)],
        s.sunrise && [tp.sun, `${s.sunrise} / ${s.sunset}`], s.fcTemp != null && [tp.forecast, `${deg(s.fcTemp)} · ${s.fcClouds} % ${tp.forecastClouds}`]],
      coll: [t.collectors, [tp.temperature, deg(s.coll)], [tp.vsTankBottom, diff(s.coll, s.bot)], [tp.solarPump, pump(s.solarPump)], [t.outdoor, deg(s.out)]],
      pSolar: [tp.solarPump, [tp.state, pump(s.solarPump)], [tp.collToTank, diff(s.coll, s.bot)]],
      tank: [t.tank, [tp.ecsProbe, deg(s.ecsP)], [t.top, deg(s.top)], [t.mid, deg(s.mid)], [t.bot, deg(s.bot)], [tp.stratification, diff(s.top, s.bot)],
        [tp.usefulEnergy, energy == null ? '–' : '≈ ' + fmt(energy) + ' kWh'], [tp.setpoint, set(s.tankSet)]],
      boiler: [t.boiler, [tp.burner, burner], [tp.temperature, s.boilT == null ? tp.notRead : deg(s.boilT)], [tp.vsTankTop, diff(s.boilT, s.top)], [tp.boilerPump, pump(s.bPump)]],
      pBoil: [tp.boilerPump, [tp.state, pump(s.bPump)], [tp.burner, burner]],
      heat: [t.heating, [tp.flow, s.heat ? deg(s.flow) : t.off], [tp.flowSet, set(s.flowSet)], [tp.flowDiff, s.flowSet > 8 ? diff(s.flow, s.flowSet) : '–'],
        [tp.roomTemp, deg(s.room)], [tp.roomSet, set(s.roomSet)], [t.outdoor, deg(s.out)],
        this._boost && this._boost.state !== 'inactive' && [tp.boost, tp.boostStates[this._boost.state] || this._boost.state]],
      pHeat: [tp.heatPump, [tp.state, state(s.heat)], [tp.flow, deg(s.flow)]],
      mixer: [tp.valve, [tp.status, s.mixer == null ? tp.notRead : t.mixer[s.mixer] || '–'], [tp.flowAndTop, `${deg(s.flow)} / ${deg(s.top)}`]],
      ecs: [t.hotWater, [tp.ecsProbe, deg(s.ecsP)], [tp.setpoint, set(s.ecsSet)], [tp.draw, state(draw)]],
      pEcs: [tp.ecsPump, [tp.state, state(draw)]],
      pool: [t.pool, [tp.temperature, deg(s.pool)], [tp.poolDiff, diff(s.bot, s.pool)], [tp.poolPump, pump(s.poolPump)]],
      pPool: [tp.poolPump, [tp.state, pump(s.poolPump)], [tp.tankToPool, diff(s.bot, s.pool)]],
    }[key];
  }

  _showTip(key) {
    const [title, ...rows] = this._tip(key);
    const tip = this._q('tip');
    tip.innerHTML = `<b>${esc(title)}</b>` + rows.filter(Boolean).map(([k, v]) => `<div><span>${esc(k)}</span>${esc(v)}</div>`).join('');
    tip.hidden = false;
    this._tipKey = key;
  }

  _placeTip(x, y) {
    const tip = this._q('tip'), w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(x + 14, innerWidth - w - 8) + 'px';
    tip.style.top = (y + 14 + h > innerHeight ? y - h - 10 : y + 14) + 'px';
  }

  _hideTip() { const tip = this._q('tip'); if (tip) tip.hidden = true; this._tipKey = null; }
}
customElements.define('okofen-dashboard', OkofenDashboard);
