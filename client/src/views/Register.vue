<!--
  注册页面
  注册后默认为普通用户角色
-->
<template>
    <div class="register-container">
        <div class="register-card">
            <h2 class="register-title">创建账号</h2>
            <p class="register-subtitle">注册成为企业知识库用户</p>

            <el-form ref="formRef" :model="form" :rules="rules" size="large">
                <el-form-item prop="username">
                    <el-input v-model="form.username" placeholder="请输入用户名（2-50个字符）" />
                </el-form-item>
                <el-form-item prop="password">
                    <el-input v-model="form.password" type="password" placeholder="请输入密码（至少6位）" />
                </el-form-item>
                <el-form-item prop="confirmPassword">
                    <el-input v-model="form.confirmPassword" type="password" placeholder="请确认密码" />
                </el-form-item>
                <el-form-item prop="email">
                    <el-input v-model="form.email" placeholder="请输入邮箱（选填）" />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" :loading="loading" class="register-btn" @click="handleRegister">
                        注 册
                    </el-button>
                </el-form-item>
            </el-form>

            <div class="register-footer">
                已有账号？<router-link to="/login">返回登录</router-link>
            </div>
        </div>
    </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const formRef = ref(null);
const loading = ref(false);

/** 注册表单数据 */
const form = reactive({
    username: "",
    password: "",
    confirmPassword: "",
    email: "",
});

/** 自定义密码确认验证 */
const validateConfirmPassword = (_rule, value, callback) => {
    if (value !== form.password) {
        callback(new Error("两次输入的密码不一致"));
    } else {
        callback();
    }
};

/** 表单验证规则 */
const rules = {
    username: [
        { required: true, message: "请输入用户名", trigger: "blur" },
        { min: 2, max: 50, message: "用户名长度须在2-50个字符之间", trigger: "blur" },
    ],
    password: [
        { required: true, message: "请输入密码", trigger: "blur" },
        { min: 6, message: "密码长度不能少于6位", trigger: "blur" },
    ],
    confirmPassword: [
        { required: true, message: "请确认密码", trigger: "blur" },
        { validator: validateConfirmPassword, trigger: "blur" },
    ],
    email: [{ type: "email", message: "请输入正确的邮箱格式", trigger: "blur" }],
};

/** 处理注册提交 */
async function handleRegister() {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;

    loading.value = true;
    try {
        await authStore.register({
            username: form.username,
            password: form.password,
            email: form.email,
        });
        ElMessage.success("注册成功，请登录");
    } catch {
        // Axios拦截器已处理错误提示
    } finally {
        loading.value = false;
    }
}
</script>

<style scoped>
.register-container {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
    width: 420px;
    padding: 40px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.register-title {
    text-align: center;
    font-size: 24px;
    color: #303133;
    margin-bottom: 8px;
}

.register-subtitle {
    text-align: center;
    color: #909399;
    font-size: 14px;
    margin-bottom: 30px;
}

.register-btn {
    width: 100%;
}

.register-footer {
    text-align: center;
    color: #909399;
    font-size: 14px;
}

.register-footer a {
    color: #409eff;
    text-decoration: none;
}
</style>
