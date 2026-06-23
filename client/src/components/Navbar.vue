<!--
  顶部导航栏组件
  显示系统名称、当前用户信息和退出按钮
-->
<template>
    <div class="navbar">
        <div class="navbar-left">
            <span class="navbar-title">企微 AI Agent 管理控制台</span>
        </div>
        <div class="navbar-right">
            <el-dropdown trigger="click">
                <span class="user-info">
                    <el-avatar :size="32" icon="UserFilled" />
                    <span class="username">{{ authStore.username }}</span>
                    <el-tag :type="authStore.isAdmin ? 'danger' : 'info'" size="small">
                        {{ authStore.isAdmin ? "管理员" : "普通用户" }}
                    </el-tag>
                </span>
                <template #dropdown>
                    <el-dropdown-menu>
                        <el-dropdown-item @click="authStore.logout()">
                            <el-icon><SwitchButton /></el-icon> 退出登录
                        </el-dropdown-item>
                    </el-dropdown-menu>
                </template>
            </el-dropdown>
        </div>
    </div>
</template>

<script setup>
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
</script>

<style scoped>
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 60px;
    padding: 0 20px;
    background: #fff;
    border-bottom: 1px solid #e4e7ed;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.navbar-title {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
}

.user-info {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
}

.username {
    font-size: 14px;
    color: #606266;
}
</style>
