<!--
  通用布局组件
  包含顶部导航栏、侧边栏和内容区域
  管理员和普通用户共用此布局，区别在于侧边栏菜单不同
-->
<template>
    <div class="layout">
        <Navbar />
        <div class="layout-body">
            <Sidebar />
            <div class="layout-content">
                <router-view />
            </div>
        </div>
    </div>
</template>

<script setup>
import Navbar from "../components/Navbar.vue";
import Sidebar from "../components/Sidebar.vue";
</script>

<style scoped>
.layout {
    height: 100vh;
    display: flex;
    flex-direction: column;
}

.layout-body {
    display: flex;
    flex: 1;
    overflow: hidden;
}

.layout-content {
    flex: 1;
    overflow-y: auto;
    background: #f0f2f5;
    padding: 20px;
}
</style>
