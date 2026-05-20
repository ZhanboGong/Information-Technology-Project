import 'element-plus/dist/index.css';
import './assets/main.css';
import { createApp } from 'vue';
import { createPinia } from 'pinia';


import App from './App.vue';
import router from './router'; // 确保这里不带花括号，对接 index.js 的 export default

const app = createApp(App);
const pinia = createPinia();

// 1. 注册 Pinia (建议放在最前面，确保插件和路由守卫能拿到 store)
app.use(pinia);

// 2. 注册 Router
app.use(router);

app.mount('#app');