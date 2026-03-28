<template>
  <div class="scalar-container">
    <div v-if="loading" class="scalar-loading">
      <div class="loading-spinner"></div>
      <p>正在加载 API 文档...</p>
    </div>
    <div v-else-if="error" class="scalar-error">
      <div class="error-icon">⚠️</div>
      <p>{{ error }}</p>
      <button @click="retry" class="retry-btn">重试</button>
    </div>
    <div v-else ref="scalarEl" id="scalar-api-reference"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const SPEC_URL = 'http://127.0.0.1:5000/openapi/openapi.json'

const scalarEl = ref(null)
const loading = ref(true)
const error = ref('')

let cleanup = null

async function initScalar() {
  loading.value = true
  error.value = ''

  try {
    // 先检查后端是否可达
    const resp = await fetch(SPEC_URL, { signal: AbortSignal.timeout(5000) })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    // 动态加载 Scalar
    const { createScalarReferences } = await import('@scalar/api-reference')

    // 等待 DOM 更新
    await new Promise((r) => setTimeout(r, 100))

    if (scalarEl.value) {
      const instance = createScalarReferences(scalarEl.value, {
        spec: { url: SPEC_URL },
        theme: 'kepler',
        layout: 'classic',
        darkMode: true,
        hideModels: false,
        hideDownloadButton: false,
        showSidebar: true,
      })
      cleanup = instance?.destroy || null
    }

    loading.value = false
  } catch (err) {
    loading.value = false
    if (err.name === 'TimeoutError' || err.message.includes('fetch')) {
      error.value = '无法连接到后端服务 (127.0.0.1:5000)，请确保 Flask 已启动'
    } else {
      error.value = `加载失败: ${err.message}`
    }
  }
}

function retry() {
  initScalar()
}

onMounted(() => {
  initScalar()
})

onBeforeUnmount(() => {
  if (cleanup) cleanup()
})
</script>

<style scoped>
.scalar-container {
  min-height: 600px;
  border-radius: 12px;
  overflow: hidden;
  margin-top: 16px;
}

.scalar-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 16px;
  color: var(--vp-c-text-2);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--vp-c-divider);
  border-top-color: var(--vp-c-brand-1);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.scalar-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 12px;
  color: var(--vp-c-text-2);
  background: var(--vp-c-bg-soft);
  border-radius: 12px;
  padding: 40px;
}

.error-icon {
  font-size: 48px;
}

.retry-btn {
  margin-top: 8px;
  padding: 8px 24px;
  background: var(--vp-c-brand-1);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: opacity 0.2s;
}

.retry-btn:hover {
  opacity: 0.85;
}

#scalar-api-reference {
  min-height: 600px;
}
</style>
