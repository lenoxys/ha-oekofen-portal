<script setup lang="ts">
// The real panel (custom_components/okofen_portal/frontend) with the sample values of scripts/preview.html,
// in a Home Assistant sidebar look-alike; package.json copies both into public/demo before dev and build.
import { computed, onMounted, ref } from 'vue'
import { useData, withBase } from 'vitepress'

const { isDark: siteDark } = useData()
// the theme is only known in the browser: the pre-rendered page is light, then follows the site once mounted
const mounted = ref(false)
onMounted(() => (mounted.value = true))
const isDark = computed(() => mounted.value && siteDark.value)
const lang = ref('en')
const night = ref(false)
const boost = ref(false)
const code = ref('800')

const src = computed(() => {
  const q = new URLSearchParams({ lang: lang.value, fake: '10', code: code.value })
  if (night.value) q.set('night', '1')
  if (boost.value) q.set('boost', 'active')
  if (isDark.value) q.set('dark', '')
  return withBase('/demo/scripts/preview.html') + '?' + q
})

// Material Design Icons (Apache 2.0), and the integration's own icon (okofen-icons.js)
const P = {
  overview: 'M13,3V9H21V3M13,21H21V11H13M3,21H11V15H3M3,13H11V3H3V13Z',
  energy: 'M11 15H6L13 1V9H18L11 23V15Z',
  map: 'M15,19L9,16.89V5L15,7.11M20.5,3C20.44,3 20.39,3 20.34,3L15,5.1L9,3L3.36,4.9C3.15,4.97 3,5.15 3,5.38V20.5A0.5,0.5 0 0,0 3.5,21C3.55,21 3.61,21 3.66,20.97L9,18.9L15,21L20.64,19.1C20.85,19 21,18.85 21,18.62V3.5A0.5,0.5 0 0,0 20.5,3Z',
  logbook: 'M5,9.5L7.5,14H2.5L5,9.5M3,4H7V8H3V4M5,20A2,2 0 0,0 7,18A2,2 0 0,0 5,16A2,2 0 0,0 3,18A2,2 0 0,0 5,20M9,5V7H21V5H9M9,19H21V17H9V19M9,13H21V11H9V13Z',
  history: 'M9 17H7V10H9V17M13 17H11V7H13V17M17 17H15V13H17V17M19 19H5V5H19V19.1M19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3Z',
  okofen: 'M6,14q0,1.3 0.53,2.46t1.5,2.04Q8,18.38 8,18.27q0-0.1 0-0.22q0-0.8 0.3-1.5t0.88-1.28L12,12.5l2.83,2.78q0.57,0.57 0.88,1.28t0.3,1.5q0,0.13 0,0.22q0,0.1-0.02,0.23q0.97-0.88 1.5-2.04T18,14q0-1.25-0.46-2.36T16.2,9.65q-0.5,0.33-1.05,0.49T14.03,10.3q-1.55,0-2.69-1.03T10.03,6.75Q9.05,7.57 8.3,8.46t-1.26,1.8T6.26,12.13T6,14Zm6,1.3l-1.42,1.4q-0.28,0.28-0.43,0.63Q10,17.68 10,18.05q0,0.8 0.59,1.38T12,20t1.41-0.57T14,18.05q0-0.4-0.15-0.74T13.43,16.7L12,15.3ZM12,3V6.3q0,0.85 0.59,1.42T14.03,8.3q0.45,0 0.84-0.19q0.39-0.19 0.69-0.56L16,7q1.85,1.05 2.93,2.92T20,14q0,3.35-2.32,5.68T12,22T6.33,19.68T4,14q0-3.23 2.16-6.13Q8.33,4.97 12,3Z',
  tools: 'M2 19.63L13.43 8.2L12.72 7.5L14.14 6.07L12 3.89C13.2 2.7 15.09 2.7 16.27 3.89L19.87 7.5L18.45 8.91H21.29L22 9.62L18.45 13.21L17.74 12.5V9.62L16.27 11.04L15.56 10.33L4.13 21.76L2 19.63Z',
  settings: 'M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z',
  bell: 'M21,19V20H3V19L5,17V11C5,7.9 7.03,5.17 10,4.29C10,4.19 10,4.1 10,4A2,2 0 0,1 12,2A2,2 0 0,1 14,4C14,4.1 14,4.19 14,4.29C16.97,5.17 19,7.9 19,11V17L21,19M14,21A2,2 0 0,1 12,23A2,2 0 0,1 10,21',
  menu: 'M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z',
}
// what the sidebar says in each language of the panel
const NAMES: Record<string, string[]> = {
  en: ['Overview', 'Energy', 'Map', 'Logbook', 'History', 'Developer tools', 'Settings', 'Notifications'],
  fr: ['Aperçu', 'Énergie', 'Carte', 'Journal', 'Historique', 'Outils de développement', 'Paramètres', 'Notifications'],
  de: ['Übersicht', 'Energie', 'Karte', 'Logbuch', 'Verlauf', 'Entwicklerwerkzeuge', 'Einstellungen', 'Benachrichtigungen'],
  es: ['Resumen', 'Energía', 'Mapa', 'Registro', 'Historial', 'Herramientas para desarrolladores', 'Ajustes', 'Notificaciones'],
  pt: ['Visão geral', 'Energia', 'Mapa', 'Registo', 'Histórico', 'Ferramentas de programador', 'Definições', 'Notificações'],
  ja: ['概要', 'エネルギー', '地図', 'ログブック', '履歴', '開発者ツール', '設定', '通知'],
  zh: ['概览', '能源', '地图', '日志', '历史', '开发者工具', '设置', '通知'],
}
const top = computed(() => {
  const n = NAMES[lang.value]
  return [['overview', n[0]], ['energy', n[1]], ['map', n[2]], ['logbook', n[3]], ['history', n[4]], ['okofen', 'ÖkoFEN']]
})
const bottom = computed(() => {
  const n = NAMES[lang.value]
  return [['tools', n[5]], ['settings', n[6]], ['bell', n[7]]]
})
</script>

<template>
  <div class="demo">
    <div class="controls">
      <label>Language
        <select v-model="lang">
          <option value="en">English</option><option value="fr">Français</option><option value="de">Deutsch</option>
          <option value="es">Español</option><option value="pt">Português</option><option value="ja">日本語</option>
          <option value="zh">中文</option>
        </select>
      </label>
      <label>Weather
        <select v-model="code">
          <option value="800">Sunny</option><option value="802">Cloudy</option><option value="501">Rain</option>
          <option value="601">Snow</option><option value="211">Storm</option><option value="741">Fog</option>
        </select>
      </label>
      <label><input v-model="night" type="checkbox"> Night</label>
      <label><input v-model="boost" type="checkbox"> Solar boost running</label>
    </div>
    <div class="ha" :class="{ dark: isDark }">
      <nav aria-hidden="true">
        <div class="title"><svg viewBox="0 0 24 24"><path :d="P.menu" /></svg><span>Home Assistant</span></div>
        <a v-for="[icon, name] in top" :key="icon" :class="{ on: icon === 'okofen' }" :title="name">
          <svg viewBox="0 0 24 24"><path :d="P[icon]" /></svg><span>{{ name }}</span>
        </a>
        <div class="spacer" />
        <a v-for="[icon, name] in bottom" :key="icon" :title="name">
          <svg viewBox="0 0 24 24"><path :d="P[icon]" /></svg><span>{{ name }}</span>
        </a>
        <a class="user"><b>A</b><span>Alex</span></a>
      </nav>
      <iframe :key="src" :src="src" title="ÖkoFEN panel, live demo" loading="lazy" />
    </div>
    <p class="note">The real panel of the integration with made-up values and ten made-up days of history: open the tabs, hover the scheme, replay a day.</p>
  </div>
</template>

<style scoped>
.demo { margin: 24px 0; }
.controls { display: flex; flex-wrap: wrap; gap: 8px 20px; align-items: center; margin-bottom: 12px; font-size: 14px; }
.controls select { margin-left: 6px; padding: 2px 6px; border: 1px solid var(--vp-c-divider); border-radius: 6px; background: var(--vp-c-bg); color: var(--vp-c-text-1); }
.controls input { margin-right: 4px; vertical-align: -1px; }
.ha {
  --side: #ffffff; --ink: #212121; --icon: #44739e; --sel: #03a9f4; --line: #e0e0e0;
  display: flex; height: 820px; border: 1px solid var(--vp-c-divider); border-radius: 12px; overflow: hidden;
  box-shadow: 0 10px 30px #0002; background: var(--side);
}
.ha.dark { --side: #1c1c1c; --ink: #e1e1e1; --icon: #9b9b9b; --line: #2f2f2f; }
nav { pointer-events: none; user-select: none; width: 256px; flex: none; display: flex; flex-direction: column; border-right: 1px solid var(--line); color: var(--ink); font: 14px/1 Roboto, system-ui, sans-serif; padding-bottom: 8px; }
nav .title { display: flex; align-items: center; gap: 12px; height: 56px; padding: 0 16px; border-bottom: 1px solid var(--line); font-size: 20px; font-weight: 400; margin-bottom: 4px; }
nav .title svg { width: 24px; fill: var(--icon); }
nav a { display: flex; align-items: center; gap: 22px; height: 40px; margin: 2px 4px; padding: 0 12px; border-radius: 4px; color: var(--ink); text-decoration: none; cursor: default; font-weight: 500; }
nav a svg { width: 24px; flex: none; fill: var(--icon); }
nav a.on { background: color-mix(in srgb, var(--sel) 12%, transparent); color: var(--sel); }
nav a.on svg { fill: var(--sel); }
nav .spacer { flex: 1; border-bottom: 1px solid var(--line); margin-bottom: 4px; }
nav .user b { width: 24px; height: 24px; flex: none; border-radius: 50%; background: var(--sel); color: #fff; display: grid; place-items: center; font-size: 12px; }
iframe { flex: 1; border: 0; min-width: 0; height: 100%; }
.note { font-size: 13px; color: var(--vp-c-text-2); }
@media (max-width: 960px) {
  nav { width: 56px; }
  nav span { display: none; }
  nav a { gap: 0; justify-content: center; padding: 0; }
  nav .title { justify-content: center; padding: 0; }
}
</style>
