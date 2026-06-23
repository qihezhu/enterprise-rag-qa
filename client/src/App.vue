<!--
  根组件
  仅包含 router-view，所有页面通过路由加载
-->
<template>
    <router-view />
</template>

<script setup>
import { onMounted } from "vue";
import { useAuthStore } from "./stores/auth";

const authStore = useAuthStore();

onMounted(() => {
    // 应用启动时，如果有token则获取用户信息
    if (authStore.isLoggedIn) {
        authStore.fetchUserInfo();
    }
});
</script>
