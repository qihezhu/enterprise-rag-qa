<!--
  登录页面
  支持管理员登录和普通用户登录两种模式，通过顶部切换按钮切换
  管理员账号只能登录管理员后台，普通用户只能登录用户端
-->
<template>
    <div class="login-page" :class="loginMode === 'admin' ? 'admin-bg' : 'user-bg'">
        <div class="login-card">
            <!-- 登录端切换 -->
            <div class="mode-switch">
                <span
                    :class="['mode-item', { active: loginMode === 'admin' }]"
                    @click="switchMode('admin')"
                >
                    <el-icon><UserFilled /></el-icon>
                    管理员登录
                </span>
                <span class="mode-divider">|</span>
                <span
                    :class="['mode-item', { active: loginMode === 'user' }]"
                    @click="switchMode('user')"
                >
                    <el-icon><User /></el-icon>
                    用户登录
                </span>
            </div>

            <h2 class="login-title">
                {{ loginMode === "admin" ? "管理员后台" : "企业知识库问答系统" }}
            </h2>
            <p class="login-subtitle">
                {{ loginMode === "admin" ? "系统管理控制台" : "基于AI的智能知识管理平台" }}
            </p>

            <el-form ref="formRef" :model="form" :rules="rules" size="large">
                <el-form-item prop="username">
                    <el-input
                        v-model="form.username"
                        placeholder="请输入用户名"
                        :prefix-icon="UserIcon"
                    />
                </el-form-item>
                <el-form-item prop="password">
                    <el-input
                        v-model="form.password"
                        type="password"
                        placeholder="请输入密码"
                        prefix-icon="Lock"
                        show-password
                        @keyup.enter="handleLogin"
                    />
                </el-form-item>
                <el-form-item>
                    <el-button
                        type="primary"
                        :loading="loading"
                        class="login-btn"
                        :class="loginMode === 'admin' ? 'btn-admin' : 'btn-user'"
                        @click="handleLogin"
                    >
                        {{ loginMode === "admin" ? "管理员登录" : "用户登录" }}
                    </el-button>
                </el-form-item>
            </el-form>

            <!-- 用户端显示注册入口 -->
            <div v-if="loginMode === 'user'" class="login-footer">
                还没有账号？
                <router-link to="/register">立即注册</router-link>
            </div>
        </div>
    </div>
</template>

<script setup>
import { reactive, ref, markRaw } from "vue";
import { ElMessage } from "element-plus";
import { User, UserFilled } from "@element-plus/icons-vue";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const formRef = ref(null);
const loading = ref(false);

/** 当前登录模式：admin 管理员端 / user 用户端 */
const loginMode = ref("user");

/** 用户图标组件引用 */
const UserIcon = markRaw(User);

/** 登录表单数据（不预填，用户自己输入） */
const form = reactive({
    username: "",
    password: "",
});

/** 表单验证规则 */
const rules = {
    username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
    password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

/** 切换登录模式 */
function switchMode(mode) {
    if (loginMode.value !== mode) {
        loginMode.value = mode;
        formRef.value?.clearValidate();
    }
}

/** 处理登录提交 */
async function handleLogin() {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;

    loading.value = true;
    try {
        // 传入登录端角色，后端会校验账号身份是否匹配
        await authStore.login(form.username, form.password, loginMode.value);
        ElMessage.success("登录成功");
    } catch {
        // Axios拦截器已处理错误提示
    } finally {
        loading.value = false;
    }
}
</script>

<style scoped>
.login-page {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    transition: background 0.4s ease;
}

/* 用户端背景（蓝色渐变） */
.user-bg {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 管理员端背景（深色渐变） */
.admin-bg {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.login-card {
    width: 420px;
    padding: 36px 40px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

/* ==================== 模式切换 ==================== */
.mode-switch {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 24px;
    padding: 6px;
    background: #f0f2f5;
    border-radius: 8px;
}

.mode-item {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px 0;
    font-size: 14px;
    color: #909399;
    cursor: pointer;
    border-radius: 6px;
    transition: all 0.2s;
}

.mode-item:hover {
    color: #606266;
}

.mode-item.active {
    background: #fff;
    color: #303133;
    font-weight: 600;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.mode-divider {
    color: #dcdfe6;
    margin: 0 8px;
    font-size: 16px;
}

/* ==================== 标题 ==================== */
.login-title {
    text-align: center;
    font-size: 22px;
    color: #303133;
    margin-bottom: 8px;
}

.login-subtitle {
    text-align: center;
    color: #909399;
    font-size: 13px;
    margin-bottom: 28px;
}

/* ==================== 按钮 ==================== */
.login-btn {
    width: 100%;
}

.btn-admin {
    background: #1a1a2e;
    border-color: #1a1a2e;
}

.btn-admin:hover {
    background: #16213e;
}

.login-footer {
    text-align: center;
    color: #909399;
    font-size: 14px;
}

.login-footer a {
    color: #409eff;
    text-decoration: none;
}
</style>
