import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'
import router from './router'
import './styles/global.css'
import { initTheme } from './utils/themes'
import * as ws from './utils/ws'

initTheme()

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus, { locale: zhCn })
app.use(router)
app.mount('#app')

// V1.2：登录态存在就启动 WS（多端冲突/恢复/配置事件）
const token = localStorage.getItem('token')
if (token) ws.connect()

// 暴露到全局，方便登录页登录后 connect
window.__antrack_ws = ws
