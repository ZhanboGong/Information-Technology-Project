import './assets/main.css';
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';

// 引入图标库（如果你登录页用到了 lucide-vue-next，确保已 npm install）
import * as ElementPlusIconsVue from '@element-plus/icons-vue';

import App from './App.vue';
import router from './router'; // 确保这里不带花括号，对接 index.js 的 export default

const app = createApp(App);
const pinia = createPinia();

// 1. 注册 Pinia (建议放在最前面，确保插件和路由守卫能拿到 store)
app.use(pinia);

// 2. 注册 Router
app.use(router);

// 3. 注册 ElementPlus
app.use(ElementPlus);

// 4. (可选) 全局注册 Element Plus 图标，防止组件内图标不显示
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component);
}

app.mount('#app');