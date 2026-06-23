<!--
  侧边栏菜单组件
  根据用户角色显示不同的菜单项
-->
<template>
    <div class="sidebar">
        <el-menu
            :default-active="activeMenu"
            :router="true"
            :collapse="false"
            background-color="#304156"
            text-color="#bfcbd9"
            active-text-color="#409eff"
        >
            <!-- 普通用户菜单 -->
            <template v-if="!authStore.isAdmin">
                <el-menu-item index="/user/home">
                    <el-icon><HomeFilled /></el-icon>
                    <span>首页</span>
                </el-menu-item>
                <el-menu-item index="/user/qa">
                    <el-icon><ChatDotRound /></el-icon>
                    <span>智能问答</span>
                </el-menu-item>
                <el-menu-item index="/user/history">
                    <el-icon><Clock /></el-icon>
                    <span>对话历史</span>
                </el-menu-item>
                <el-menu-item index="/user/documents">
                    <el-icon><Document /></el-icon>
                    <span>文档列表</span>
                </el-menu-item>
            </template>

            <!-- 管理员菜单 -->
            <template v-else>
                <el-menu-item index="/admin/dashboard">
                    <el-icon><DataAnalysis /></el-icon>
                    <span>仪表盘</span>
                </el-menu-item>
                <el-menu-item index="/admin/qa">
                    <el-icon><ChatDotRound /></el-icon>
                    <span>智能问答</span>
                </el-menu-item>
                <el-menu-item index="/admin/history">
                    <el-icon><Clock /></el-icon>
                    <span>对话历史</span>
                </el-menu-item>
                <el-menu-item index="/admin/documents">
                    <el-icon><Document /></el-icon>
                    <span>文档管理</span>
                </el-menu-item>
                <el-menu-item index="/admin/documents/upload">
                    <el-icon><Upload /></el-icon>
                    <span>上传文档</span>
                </el-menu-item>
                <el-menu-item index="/admin/users">
                    <el-icon><User /></el-icon>
                    <span>用户管理</span>
                </el-menu-item>
                <el-menu-item index="/admin/logs">
                    <el-icon><Tickets /></el-icon>
                    <span>系统日志</span>
                </el-menu-item>
                <el-menu-item index="/admin/wecom-config">
                    <el-icon><Setting /></el-icon>
                    <span>企微配置</span>
                </el-menu-item>
                <el-menu-item index="/admin/approval">
                    <el-icon><DocumentChecked /></el-icon>
                    <span>审批监控</span>
                </el-menu-item>
                <el-menu-item index="/admin/schedule">
                    <el-icon><Calendar /></el-icon>
                    <span>日程监控</span>
                </el-menu-item>
                <el-menu-item index="/admin/contact-usage">
                    <el-icon><UserFilled /></el-icon>
                    <span>组织大脑</span>
                </el-menu-item>
                <el-menu-item index="/admin/customer-ops">
                    <el-icon><Service /></el-icon>
                    <span>客户运营</span>
                </el-menu-item>
                <el-menu-item index="/admin/health">
                    <el-icon><Monitor /></el-icon>
                    <span>系统健康</span>
                </el-menu-item>
                <el-menu-item index="/admin/metrics">
                    <el-icon><TrendCharts /></el-icon>
                    <span>调用指标</span>
                </el-menu-item>
            </template>
        </el-menu>
    </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const authStore = useAuthStore();

/** 当前激活的菜单项（根据路由路径） */
const activeMenu = computed(() => route.path);
</script>

<style scoped>
.sidebar {
    width: 220px;
    min-height: calc(100vh - 60px);
    background: #304156;
}

.el-menu {
    border-right: none;
}
</style>
