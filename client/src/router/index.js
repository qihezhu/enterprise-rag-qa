/**
 * Vue Router路由配置
 * 包含公开路由、普通用户路由、管理员路由
 * 导航守卫验证登录状态和角色权限
 */
import { createRouter, createWebHistory } from "vue-router";

const routes = [
    {
        path: "/",
        redirect: "/login",
    },
    {
        path: "/login",
        name: "Login",
        component: () => import("../views/Login.vue"),
        meta: { guest: true },
    },
    {
        path: "/register",
        name: "Register",
        component: () => import("../views/Register.vue"),
        meta: { guest: true },
    },
    {
        path: "/user",
        component: () => import("../views/Layout.vue"),
        meta: { requiresAuth: true, role: "user" },
        children: [
            {
                path: "home",
                name: "UserHome",
                component: () => import("../views/user/Home.vue"),
            },
            {
                path: "qa",
                name: "QAChat",
                component: () => import("../views/user/QAChat.vue"),
            },
            {
                path: "history",
                name: "UserHistory",
                component: () => import("../views/common/ConversationHistory.vue"),
            },
            {
                path: "documents",
                name: "DocumentList",
                component: () => import("../views/user/DocumentList.vue"),
            },
        ],
    },
    {
        path: "/admin",
        component: () => import("../views/Layout.vue"),
        meta: { requiresAuth: true, role: "admin" },
        children: [
            {
                path: "dashboard",
                name: "AdminDashboard",
                component: () => import("../views/admin/Dashboard.vue"),
            },
            {
                path: "qa",
                name: "AdminQAChat",
                component: () => import("../views/user/QAChat.vue"),
            },
            {
                path: "history",
                name: "AdminHistory",
                component: () => import("../views/common/ConversationHistory.vue"),
            },
            {
                path: "documents",
                name: "AdminDocuments",
                component: () => import("../views/admin/DocumentManage.vue"),
            },
            {
                path: "documents/upload",
                name: "AdminDocumentUpload",
                component: () => import("../views/user/DocumentUpload.vue"),
            },
            {
                path: "users",
                name: "UserManage",
                component: () => import("../views/admin/UserManage.vue"),
            },
            {
                path: "logs",
                name: "SystemLog",
                component: () => import("../views/admin/SystemLog.vue"),
            },
            {
                path: "wecom-config",
                name: "WeComConfig",
                component: () => import("../views/admin/WeComConfig.vue"),
            },
            {
                path: "approval",
                name: "ApprovalMonitor",
                component: () => import("../views/admin/ApprovalMonitor.vue"),
            },
            {
                path: "schedule",
                name: "ScheduleMonitor",
                component: () => import("../views/admin/ScheduleMonitor.vue"),
            },
            {
                path: "contact-usage",
                name: "ContactUsage",
                component: () => import("../views/admin/ContactUsage.vue"),
            },
            {
                path: "customer-ops",
                name: "CustomerOps",
                component: () => import("../views/admin/CustomerOps.vue"),
            },
            {
                path: "health",
                name: "SystemHealth",
                component: () => import("../views/admin/SystemHealth.vue"),
            },
            {
                path: "metrics",
                name: "MetricsView",
                component: () => import("../views/admin/Metrics.vue"),
            },
        ],
    },
    {
        path: "/:pathMatch(.*)*",
        redirect: "/login",
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

/**
 * 全局导航守卫：验证登录状态和角色权限
 */
router.beforeEach((to, _from, next) => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");

    // 需要登录但未登录 → 跳转到登录页
    if (to.meta.requiresAuth && !token) {
        return next("/login");
    }

    // 已登录但访问游客页面 → 跳转到对应首页
    if (to.meta.guest && token) {
        return next(role === "admin" ? "/admin/dashboard" : "/user/home");
    }

    // 角色权限不足 → 跳转到自己角色的首页
    if (to.meta.role && to.meta.role !== role) {
        return next(role === "admin" ? "/admin/dashboard" : "/user/home");
    }

    next();
});

export default router;
