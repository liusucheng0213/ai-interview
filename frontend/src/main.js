import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// Element Plus 组件和 CSS 由 unplugin-vue-components 按需自动引入
// 无需在此全量 import，可减少约 60% 的初始 bundle 体积

const app = createApp(App)
app.use(router)
app.mount('#app')
