/**
 * VitePress 自定义主题
 * 扩展默认主题，注入全局样式和组件
 */
import DefaultTheme from 'vitepress/theme'
import './custom.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    // 全局组件注册（按需）
  },
}
