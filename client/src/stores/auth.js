/**
 * 认证状态管理（Pinia Store）
 * 管理用户Token、用户信息、登录/登出操作
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { loginApi, registerApi, getUserInfoApi } from "../api/auth";
import { useChatStore } from "./chat";
import router from "../router";

export const useAuthStore = defineStore("auth", () => {
    // ==================== 状态 ====================
    const token = ref(localStorage.getItem("token") || "");
    const userInfo = ref(null);

    // ==================== 计算属性 ====================
    const isLoggedIn = computed(() => !!token.value);
    const isAdmin = computed(() => userInfo.value?.role === "admin");
    const username = computed(() => userInfo.value?.username || "");

    // ==================== 操作 ====================

    /**
     * 用户登录
     * @param {string} loginUsername 用户名
     * @param {string} password 密码（明文，后端会MD5加密）
     * @param {string} role 登录端：admin 或 user
     */
    async function login(loginUsername, password, role) {
        const res = await loginApi({ username: loginUsername, password, role });
        const { token: newToken, user } = res.data;

        token.value = newToken;
        userInfo.value = user;

        // 持久化存储
        localStorage.setItem("token", newToken);
        localStorage.setItem("role", user.role);

        // 根据角色跳转到对应首页
        const targetPath = user.role === "admin" ? "/admin/dashboard" : "/user/home";
        router.push(targetPath);
    }

    /**
     * 用户注册
     * @param {object} data {username, password, email}
     */
    async function register(data) {
        await registerApi(data);
        router.push("/login");
    }

    /**
     * 获取当前用户信息
     */
    async function fetchUserInfo() {
        if (!token.value) return;
        try {
            const res = await getUserInfoApi();
            userInfo.value = res.data;
        } catch {
            // Token失效时清除状态
            logout();
        }
    }

    /**
     * 退出登录
     */
    function logout() {
        token.value = "";
        userInfo.value = null;
        localStorage.removeItem("token");
        localStorage.removeItem("role");
        // 清除对话记录，防止切换账号后看到前一个用户的对话
        useChatStore().clearMessages();
        router.push("/login");
    }

    return { token, userInfo, isLoggedIn, isAdmin, username, login, register, fetchUserInfo, logout };
});
