/**
 * Vue3应用入口文件
 * 注册Router、Pinia全局状态管理，挂载应用
 */
import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import App from "./App.vue";
import router from "./router";
import "./assets/styles/global.css";

const app = createApp(App);

// 全局状态管理
const pinia = createPinia();
app.use(pinia);

// 路由
app.use(router);

// Element Plus UI组件库
app.use(ElementPlus, { locale: undefined });

app.mount("#app");
