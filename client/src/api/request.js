/**
 * Axios请求实例封装
 * 统一的请求/响应拦截器、Token注入、错误处理
 */
import axios from "axios";
import { ElMessage } from "element-plus";
import router from "../router";

// 创建Axios实例
const request = axios.create({
    baseURL: "/api",       // 所有请求以 /api 开头，Vite代理转发到后端
    timeout: 60000,        // 超时60秒（问答接口可能较慢）
    headers: {
        "Content-Type": "application/json",
    },
});

/**
 * 请求拦截器：自动在请求头中注入JWT Token
 */
request.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("token");
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

/**
 * 响应拦截器：统一处理错误
 */
request.interceptors.response.use(
    (response) => {
        return response.data;  // 直接返回 data，方便调用方使用
    },
    (error) => {
        if (error.response) {
            const { status, data } = error.response;

            if (status === 401) {
                // Token过期或未登录，跳转到登录页
                localStorage.removeItem("token");
                localStorage.removeItem("role");
                ElMessage.error("登录已过期，请重新登录");
                router.push("/login");
            } else if (status === 403) {
                ElMessage.error(data.message || "无权限执行此操作");
            } else if (status === 500) {
                ElMessage.error(data.message || "服务器内部错误");
            } else {
                ElMessage.error(data.message || "请求失败");
            }
        } else if (error.code === "ECONNABORTED") {
            ElMessage.error("请求超时，请重试");
        } else {
            ElMessage.error("网络异常，请检查网络连接");
        }

        return Promise.reject(error);
    }
);

export default request;
