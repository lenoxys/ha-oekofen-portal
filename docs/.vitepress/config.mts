import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'ÖkoFEN Portal',
  description: "The controller's parameters, their names, and how the Home Assistant integration uses them",
  base: '/ha-oekofen-portal/',
  cleanUrls: true,
  lastUpdated: true,
  themeConfig: {
    nav: [
      { text: 'Guide', link: '/parameters' },
      { text: 'Reference', link: '/variables' },
      { text: 'Releases', link: 'https://github.com/lenoxys/ha-oekofen-portal/releases' },
    ],
    sidebar: [
      { text: 'Parameters and nomenclature', link: '/parameters' },
      {
        text: 'Reference',
        items: [
          { text: 'Portal variables', link: '/variables' },
          { text: 'Local JSON interface', link: '/local' },
        ],
      },
    ],
    outline: { level: [2, 3] },
    search: { provider: 'local' },
    socialLinks: [{ icon: 'github', link: 'https://github.com/lenoxys/ha-oekofen-portal' }],
    editLink: {
      pattern: 'https://github.com/lenoxys/ha-oekofen-portal/edit/main/docs/:path',
    },
    footer: { message: 'Unofficial, not affiliated with ÖkoFEN.' },
  },
})
