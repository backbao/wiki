/**
 * API 文档自动生成脚本
 * 从 Flask 后端拉取 OpenAPI spec，按 tag 分组生成 Markdown 文档
 * 同时输出侧边栏配置供 VitePress 使用
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DOCS_DIR = path.resolve(__dirname, '../docs')
const API_DIR = path.resolve(DOCS_DIR, 'api')
const API_SIDEBAR_FILE = path.resolve(DOCS_DIR, '.vitepress/api-sidebar.json')
const OPENAPI_CACHE = path.resolve(DOCS_DIR, '.vitepress/openapi-spec.json')
const OPENAPI_PREVIOUS_CACHE = path.resolve(DOCS_DIR, '.vitepress/openapi-spec.prev.json')
const CHANGELOG_FILE = path.resolve(API_DIR, 'changelog.md')

// 后端 OpenAPI 地址 (可通过环境变量覆盖)
const OPENAPI_URL = process.env.OPENAPI_URL || 'http://127.0.0.1:5000/openapi/openapi.json'

/* ──────── 工具函数 ──────── */

/** HTTP method 到颜色 badge 的映射 */
const METHOD_BADGE = {
  get: '🟢 GET',
  post: '🔵 POST',
  put: '🟡 PUT',
  patch: '🟠 PATCH',
  delete: '🔴 DELETE',
  head: '⚪ HEAD',
  options: '⚪ OPTIONS',
}

const METHOD_ORDER = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

function safeStringify(value) {
  return JSON.stringify(value, null, 2)
}

/** 解析 $ref 引用 */
function resolveRef(spec, ref) {
  if (!ref || !ref.startsWith('#/')) return null
  const parts = ref.replace('#/', '').split('/')
  let result = spec
  for (const p of parts) {
    result = result?.[p]
  }
  return result
}

function getSchemaType(schema) {
  if (!schema) return '-'
  if (schema.$ref) return schema.$ref.split('/').at(-1) || schema.$ref
  if (schema.type) return schema.type
  if (schema.oneOf) return 'oneOf'
  if (schema.anyOf) return 'anyOf'
  if (schema.allOf) return 'allOf'
  return 'object'
}

function simplifySchema(spec, schema, seen = new Set()) {
  if (!schema) return null

  if (schema.$ref) {
    if (seen.has(schema.$ref)) return { $ref: schema.$ref }
    const resolved = resolveRef(spec, schema.$ref)
    if (!resolved) return { $ref: schema.$ref }
    seen.add(schema.$ref)
    return simplifySchema(spec, resolved, seen)
  }

  const result = {}
  for (const key of ['type', 'title', 'description', 'default', 'example', 'format', 'nullable', 'enum']) {
    if (schema[key] !== undefined) result[key] = schema[key]
  }

  if (schema.required) result.required = [...schema.required]

  if (schema.properties) {
    result.properties = {}
    for (const [name, prop] of Object.entries(schema.properties)) {
      result.properties[name] = simplifySchema(spec, prop, seen)
    }
  }

  if (schema.items) result.items = simplifySchema(spec, schema.items, seen)
  if (schema.oneOf) result.oneOf = schema.oneOf.map((item) => simplifySchema(spec, item, seen))
  if (schema.anyOf) result.anyOf = schema.anyOf.map((item) => simplifySchema(spec, item, seen))
  if (schema.allOf) result.allOf = schema.allOf.map((item) => simplifySchema(spec, item, seen))

  return result
}

function simplifyOperation(spec, operation) {
  const requestBodySchema = operation.requestBody?.content?.['application/json']?.schema
  const responses = {}

  for (const [code, resp] of Object.entries(operation.responses || {})) {
    if (code === '422') continue
    responses[code] = {
      description: resp.description || '',
      schema: simplifySchema(spec, resp.content?.['application/json']?.schema || null),
    }
  }

  return {
    summary: operation.summary || '',
    description: operation.description || '',
    tags: operation.tags || [],
    parameters: (operation.parameters || []).map((param) => ({
      name: param.name,
      in: param.in,
      required: !!param.required,
      description: param.description || '',
      type: param.schema?.type || '-',
    })),
    requestBody: requestBodySchema ? simplifySchema(spec, requestBodySchema) : null,
    responses,
  }
}

function flattenEndpoints(spec) {
  const endpoints = []

  for (const [httpPath, methods] of Object.entries(spec.paths || {})) {
    for (const [method, operation] of Object.entries(methods)) {
      if (!METHOD_ORDER.includes(method)) continue
      endpoints.push({
        key: `${method.toUpperCase()} ${httpPath}`,
        method,
        path: httpPath,
        operation,
        normalized: simplifyOperation(spec, operation),
      })
    }
  }

  return endpoints.sort((a, b) => a.key.localeCompare(b.key))
}

function buildDiff(previousSpec, currentSpec) {
  if (!previousSpec) {
    return {
      previousVersion: 'baseline',
      currentVersion: currentSpec.info?.version || 'unknown',
      added: [],
      removed: [],
      changed: [],
    }
  }

  const prevMap = new Map(flattenEndpoints(previousSpec).map((item) => [item.key, item]))
  const curMap = new Map(flattenEndpoints(currentSpec).map((item) => [item.key, item]))
  const added = []
  const removed = []
  const changed = []

  for (const [key, item] of curMap.entries()) {
    const prev = prevMap.get(key)
    if (!prev) {
      added.push(item)
      continue
    }

    if (safeStringify(prev.normalized) !== safeStringify(item.normalized)) {
      changed.push({ before: prev, after: item })
    }
  }

  for (const [key, item] of prevMap.entries()) {
    if (!curMap.has(key)) removed.push(item)
  }

  return {
    previousVersion: previousSpec.info?.version || 'unknown',
    currentVersion: currentSpec.info?.version || 'unknown',
    added,
    removed,
    changed,
  }
}

/** 将 schema 渲染成 Markdown 表格 */
function renderSchemaTable(spec, schema, depth = 0) {
  if (!schema) return ''

  // 解析引用
  if (schema.$ref) {
    schema = resolveRef(spec, schema.$ref)
    if (!schema) return ''
  }

  if (schema.type !== 'object' || !schema.properties) return ''

  const required = new Set(schema.required || [])
  let md = ''

  if (depth === 0) {
    md += '| 参数名 | 类型 | 必填 | 描述 | 默认值 |\n'
    md += '| --- | --- | --- | --- | --- |\n'
  }

  for (const [name, prop] of Object.entries(schema.properties)) {
    let resolvedProp = prop
    if (prop.$ref) {
      resolvedProp = resolveRef(spec, prop.$ref) || prop
    }

    const type = getSchemaType(resolvedProp)
    const isRequired = required.has(name) ? '✅' : ''
    const desc = resolvedProp.description || ''
    const defaultVal = resolvedProp.default !== undefined ? `\`${JSON.stringify(resolvedProp.default)}\`` : '-'
    const example = resolvedProp.example ? ` (示例: \`${resolvedProp.example}\`)` : ''
    const indent = '  '.repeat(depth)

    md += `| ${indent}\`${name}\` | \`${type}\` | ${isRequired} | ${desc}${example} | ${defaultVal} |\n`
  }

  return md
}

function renderChangelog(diff, currentSpec) {
  let md = `---\nlayout: doc\n---\n\n# 接口变更清单\n\n`
  md += `> 版本基线：\`${diff.previousVersion}\` -> 当前：\`${diff.currentVersion}\`\n\n`

  if (!diff.added.length && !diff.removed.length && !diff.changed.length) {
    md += '本次没有检测到接口变化。\n'
    return md
  }

  md += `## 概览\n\n`
  md += `- 新增接口：${diff.added.length}\n`
  md += `- 删除接口：${diff.removed.length}\n`
  md += `- 变更接口：${diff.changed.length}\n\n`

  if (diff.added.length) {
    md += `## 新增接口\n\n`
    for (const ep of diff.added) {
      md += `### ${ep.key}\n\n`
      md += `- ${ep.operation.summary || '未命名接口'}\n`
      md += `- 路径：\`${ep.path}\`\n\n`
      md += '```json\n'
      md += safeStringify(ep.normalized) + '\n'
      md += '```\n\n'
    }
  }

  if (diff.removed.length) {
    md += `## 删除接口\n\n`
    for (const ep of diff.removed) {
      md += `### ${ep.key}\n\n`
      md += `- ${ep.operation.summary || '未命名接口'}\n`
      md += `- 路径：\`${ep.path}\`\n\n`
    }
  }

  if (diff.changed.length) {
    md += `## 变更接口\n\n`
    for (const item of diff.changed) {
      md += `### ${item.after.key}\n\n`
      md += `- 变更说明：接口定义不一致\n\n`
      md += `#### 旧版本\n\n`
      md += '```json\n'
      md += safeStringify(item.before.normalized) + '\n'
      md += '```\n\n'
      md += `#### 新版本\n\n`
      md += '```json\n'
      md += safeStringify(item.after.normalized) + '\n'
      md += '```\n\n'
    }
  }

  md += `## 当前快照\n\n`
  md += `- 标题：\`${currentSpec.info?.title || 'API'}\`\n`
  md += `- 版本：\`${currentSpec.info?.version || 'unknown'}\`\n`

  return md
}

/** 生成单个接口的 Markdown */
function renderEndpoint(spec, httpPath, method, operation) {
  const badge = METHOD_BADGE[method] || method.toUpperCase()
  const summary = operation.summary || '未命名接口'
  const description = operation.description || ''

  let md = `### ${badge} \`${httpPath}\`\n\n`
  md += `**${summary}**\n\n`

  if (description) {
    md += `${description}\n\n`
  }

  // 请求参数 (query / path)
  if (operation.parameters?.length) {
    md += '#### 请求参数\n\n'
    md += '| 参数名 | 位置 | 类型 | 必填 | 描述 |\n'
    md += '| --- | --- | --- | --- | --- |\n'
    for (const param of operation.parameters) {
      md += `| \`${param.name}\` | ${param.in} | \`${param.schema?.type || '-'}\` | ${param.required ? '✅' : ''} | ${param.description || ''} |\n`
    }
    md += '\n'
  }

  // 请求体
  if (operation.requestBody) {
    md += '#### 请求体\n\n'
    const content = operation.requestBody.content
    if (content?.['application/json']?.schema) {
      const bodySchema = content['application/json'].schema
      let resolvedSchema = bodySchema
      if (bodySchema.$ref) {
        resolvedSchema = resolveRef(spec, bodySchema.$ref)
      }
      md += renderSchemaTable(spec, resolvedSchema)

      // 生成示例
      if (resolvedSchema?.properties) {
        md += '\n**请求示例：**\n\n'
        md += '```json\n'
        const example = {}
        for (const [k, v] of Object.entries(resolvedSchema.properties)) {
          if (v.example !== undefined) example[k] = v.example
          else if (v.default !== undefined) example[k] = v.default
          else if (v.type === 'string') example[k] = 'string'
          else if (v.type === 'number' || v.type === 'integer') example[k] = 0
          else if (v.type === 'boolean') example[k] = false
          else example[k] = null
        }
        md += JSON.stringify(example, null, 2) + '\n'
        md += '```\n\n'
      }
    }
  }

  // 响应
  if (operation.responses) {
    md += '#### 响应\n\n'
    for (const [code, resp] of Object.entries(operation.responses)) {
      if (code === '422') continue // 跳过验证错误
      md += `**${code}** - ${resp.description || ''}\n\n`
      const json = resp.content?.['application/json']?.schema
      if (json) {
        let resolvedResp = json
        if (json.$ref) resolvedResp = resolveRef(spec, json.$ref)
        md += renderSchemaTable(spec, resolvedResp)
        md += '\n'
      }
    }
  }

  md += '---\n\n'
  return md
}

/* ──────── 主流程 ──────── */

async function fetchSpec() {
  console.log(`📡 正在从 ${OPENAPI_URL} 获取 OpenAPI 规范...`)
  try {
    const resp = await fetch(OPENAPI_URL)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const spec = await resp.json()
    // 缓存 spec 到本地
    fs.mkdirSync(path.dirname(OPENAPI_CACHE), { recursive: true })
    fs.writeFileSync(OPENAPI_CACHE, JSON.stringify(spec, null, 2), 'utf-8')
    console.log('✅ OpenAPI 规范获取成功')
    return spec
  } catch (err) {
    console.warn(`⚠️  无法连接后端 (${err.message})，尝试使用缓存...`)
    if (fs.existsSync(OPENAPI_CACHE)) {
      return JSON.parse(fs.readFileSync(OPENAPI_CACHE, 'utf-8'))
    }
    throw new Error('无法获取 OpenAPI 规范且没有缓存可用')
  }
}

function groupByTag(spec) {
  const groups = {} // tag -> [{ path, method, operation }]
  const tagMeta = {} // tag -> { name, description }

  // 收集 tag 元信息
  for (const t of spec.tags || []) {
    tagMeta[t.name] = t
  }

  // 按 tag 分组
  for (const [httpPath, methods] of Object.entries(spec.paths || {})) {
    for (const [method, operation] of Object.entries(methods)) {
      if (!METHOD_ORDER.includes(method)) continue
      const tags = operation.tags || ['default']
      for (const tag of tags) {
        if (!groups[tag]) groups[tag] = []
        if (!tagMeta[tag]) tagMeta[tag] = { name: tag, description: '' }
        groups[tag].push({ path: httpPath, method, operation })
      }
    }
  }

  return { groups, tagMeta }
}

function toSlug(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
}

function loadPreviousSpec() {
  if (!fs.existsSync(OPENAPI_CACHE)) return null
  try {
    return JSON.parse(fs.readFileSync(OPENAPI_CACHE, 'utf-8'))
  } catch {
    return null
  }
}

function writeSnapshot(spec) {
  fs.mkdirSync(path.dirname(OPENAPI_PREVIOUS_CACHE), { recursive: true })
  if (fs.existsSync(OPENAPI_CACHE)) {
    fs.copyFileSync(OPENAPI_CACHE, OPENAPI_PREVIOUS_CACHE)
  }
  fs.writeFileSync(OPENAPI_CACHE, JSON.stringify(spec, null, 2), 'utf-8')
}

function generateDocs(spec, previousSpec) {
  const { groups, tagMeta } = groupByTag(spec)
  const diff = buildDiff(previousSpec, spec)

  // 确保目录存在
  fs.mkdirSync(API_DIR, { recursive: true })

  const sidebar = []
  const generatedFiles = new Set()

  // 生成总览页
  let overviewMd = `---
layout: doc
---

# 📡 API 接口总览

> [!TIP]
> 此文档由 \`generate-api-docs\` 脚本自动生成，与后端代码实时同步。请勿手动编辑。

**API 版本：** \`${spec.info?.version || 'unknown'}\` &nbsp; | &nbsp; **标题：** ${spec.info?.title || 'API'}

## 分组列表

- [接口变更清单](/api/changelog)

`

  for (const [tag, endpoints] of Object.entries(groups)) {
    const meta = tagMeta[tag]
    const slug = toSlug(tag)
    overviewMd += `### ${meta.name}\n\n`
    overviewMd += `${meta.description || ''}\n\n`
    overviewMd += `| 方法 | 路径 | 描述 |\n`
    overviewMd += `| --- | --- | --- |\n`
    for (const ep of endpoints) {
      const badge = METHOD_BADGE[ep.method] || ep.method.toUpperCase()
      overviewMd += `| ${badge} | [\`${ep.path}\`](/api/${slug}#${toSlug(ep.method + '-' + ep.path)}) | ${ep.operation.summary || ''} |\n`
    }
    overviewMd += `\n[查看完整文档 →](/api/${slug})\n\n`
  }

  const overviewPath = path.join(API_DIR, 'index.md')
  fs.writeFileSync(overviewPath, overviewMd.trimEnd() + '\n', 'utf-8')
  generatedFiles.add(overviewPath)

  const changelogPath = CHANGELOG_FILE
  fs.writeFileSync(changelogPath, renderChangelog(diff, spec).trimEnd() + '\n', 'utf-8')
  generatedFiles.add(changelogPath)

  // 按 tag 生成独立页面
  for (const [tag, endpoints] of Object.entries(groups)) {
    const meta = tagMeta[tag]
    const slug = toSlug(tag)
    const fileName = `${slug}.md`
    const filePath = path.join(API_DIR, fileName)

    let md = `---
layout: doc
---

# ${meta.name}

${meta.description ? `> ${meta.description}` : ''}

<div class="api-badge-bar">
  <span class="api-badge">${endpoints.length} 个接口</span>
</div>

`

    for (const ep of endpoints) {
      md += renderEndpoint(spec, ep.path, ep.method, ep.operation)
    }

    fs.writeFileSync(filePath, md.trimEnd() + '\n', 'utf-8')
    generatedFiles.add(filePath)

    sidebar.push({
      text: `${meta.name}`,
      link: `/api/${slug}`,
    })

    console.log(`  📄 生成：api/${fileName} (${endpoints.length} 个接口)`)
  }

  // 添加 Scalar 在线调试页面
  const scalarMd = `---
layout: doc
---

<script setup>
import ScalarApiRef from '../.vitepress/theme/components/ScalarApiRef.vue'
</script>

# 🧪 在线调试 (Scalar)

> [!TIP]
> 使用 Scalar 交互式组件直接在浏览器中测试 API 接口。数据来自后端实时 OpenAPI 规范。

<ClientOnly>
  <ScalarApiRef />
</ClientOnly>
`
  const scalarPath = path.join(API_DIR, 'playground.md')
  fs.writeFileSync(scalarPath, scalarMd.trimEnd() + '\n', 'utf-8')
  generatedFiles.add(scalarPath)

  // 构建侧边栏配置
  const sidebarConfig = [
    {
      text: 'API 文档',
      items: [
        { text: '📡 接口总览', link: '/api/' },
        { text: '📝 接口变更', link: '/api/changelog' },
        ...sidebar,
        { text: '🧪 在线调试', link: '/api/playground' },
      ],
    },
  ]

  fs.writeFileSync(API_SIDEBAR_FILE, JSON.stringify(sidebarConfig, null, 2), 'utf-8')
  console.log(`  📋 侧边栏配置已更新`)

  // 清理不再需要的旧文件
  const existingFiles = fs.readdirSync(API_DIR).map((f) => path.join(API_DIR, f))
  for (const f of existingFiles) {
    if (f.endsWith('.md') && !generatedFiles.has(f)) {
      fs.unlinkSync(f)
      console.log(`  🗑️  删除旧文件：${path.basename(f)}`)
    }
  }
}

/* ──────── 入口 ──────── */

async function main() {
  const mode = process.argv[2] || 'build'

  console.log('🚀 API 文档生成器启动...\n')

  const syncOnce = async () => {
    const previousSpec = loadPreviousSpec()
    const spec = await fetchSpec()
    generateDocs(spec, previousSpec)
    writeSnapshot(spec)
    console.log('\n✨ 文档生成完成！')
  }

  if (mode === 'watch') {
    // 开发模式：定时轮询
    const INTERVAL = parseInt(process.env.POLL_INTERVAL || '5000', 10)
    console.log(`👀 开发模式：每 ${INTERVAL}ms 检查后端变更...\n`)

    let lastHash = ''

    const poll = async () => {
      try {
        const previousSpec = loadPreviousSpec()
        const spec = await fetchSpec()
        const hash = JSON.stringify(spec)
        if (hash !== lastHash) {
          lastHash = hash
          generateDocs(spec, previousSpec)
          writeSnapshot(spec)
          console.log(`\n✨ 文档已更新 (${new Date().toLocaleTimeString()})\n`)
        }
      } catch (err) {
        // 静默：后端可能还没启动
      }
    }

    await poll()
    setInterval(poll, INTERVAL)
  } else {
    await syncOnce()
  }
}

main().catch((err) => {
  console.error('❌ 错误:', err.message)
  process.exit(1)
})
