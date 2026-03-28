import { defineConfig } from 'vitepress'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const sidebarPath = path.join(__dirname, 'api-sidebar.json')

function loadSidebar() {
  if (!fs.existsSync(sidebarPath)) {
    return [
      {
        text: 'API 文档',
        items: [
          { text: '接口总览', link: '/api/' },
          { text: '接口变更', link: '/api/changelog' },
          { text: '在线调试', link: '/api/playground' },
        ],
      },
    ]
  }

  return JSON.parse(fs.readFileSync(sidebarPath, 'utf-8'))
}

export default defineConfig({
  title: 'AI Chat Docs',
  description: '后端接口文档与变更清单',
  base: process.env.VITEPRESS_BASE || '/',
  cleanUrls: true,
  lastUpdated: true,
  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: 'API 文档', link: '/api/' },
      { text: '接口变更', link: '/api/changelog' },
      { text: '在线调试', link: '/api/playground' },
    ],
    sidebar: loadSidebar(),
  },
})
