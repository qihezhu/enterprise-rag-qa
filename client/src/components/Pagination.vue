<!--
  分页组件
  基于Element Plus的Pagination二次封装
  props: total, page, pageSize
  emits: update:page, update:pageSize
-->
<template>
    <div class="pagination-wrapper" v-if="total > 0">
        <el-pagination
            :current-page="page"
            :page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            :total="total"
            layout="total, sizes, prev, pager, next"
            background
            @current-change="$emit('update:page', $event)"
            @size-change="$emit('update:pageSize', $event)"
        />
    </div>
</template>

<script setup>
defineProps({
    total: { type: Number, default: 0 },
    page: { type: Number, default: 1 },
    pageSize: { type: Number, default: 10 },
});

defineEmits(["update:page", "update:pageSize"]);
</script>

<style scoped>
.pagination-wrapper {
    display: flex;
    justify-content: center;
    margin-top: 20px;
}
</style>
