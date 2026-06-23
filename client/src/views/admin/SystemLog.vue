<!--
  系统日志页面（管理员视角）
  查看系统操作日志，支持按操作类型筛选和分页
-->
<template>
    <div class="system-log">
        <h3 class="page-title">系统日志</h3>

        <!-- 操作类型筛选 -->
        <div class="toolbar">
            <el-select v-model="actionFilter" placeholder="操作类型筛选" clearable style="width: 200px" @change="handleFilter">
                <el-option label="全部" value="" />
                <el-option label="登录" value="LOGIN" />
                <el-option label="注册" value="USER_REGISTER" />
                <el-option label="上传文档" value="DOC_UPLOAD" />
                <el-option label="删除文档" value="DOC_DELETE" />
                <el-option label="智能问答" value="QA_ASK" />
                <el-option label="修改用户" value="USER_UPDATE" />
                <el-option label="删除用户" value="USER_DELETE" />
            </el-select>
        </div>

        <!-- 日志表格 -->
        <div class="table-box card-box">
            <el-table :data="logs" v-loading="loading" stripe>
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="username" label="操作人" width="100" />
                <el-table-column label="操作类型" width="120">
                    <template #default="{ row }">
                        <el-tag :type="getActionTagType(row.action)" size="small">
                            {{ getActionLabel(row.action) }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="description" label="描述" min-width="280" show-overflow-tooltip />
                <el-table-column prop="ip_address" label="IP地址" width="140" />
                <el-table-column prop="created_at" label="时间" width="170" />
            </el-table>
        </div>

        <Pagination
            :total="total"
            :page="page"
            :pageSize="pageSize"
            @update:page="onPageChange"
            @update:pageSize="onSizeChange"
        />
    </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { getSystemLogsApi } from "../../api/admin";
import Pagination from "../../components/Pagination.vue";

const logs = ref([]);
const loading = ref(false);
const actionFilter = ref("");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

/** 加载日志列表 */
async function loadLogs() {
    loading.value = true;
    try {
        const res = await getSystemLogsApi({
            page: page.value,
            page_size: pageSize.value,
            action: actionFilter.value,
        });
        logs.value = res.data.items;
        total.value = res.data.total;
    } finally {
        loading.value = false;
    }
}

/** 操作类型筛选 */
function handleFilter() {
    page.value = 1;
    loadLogs();
}

/** 获取操作类型标签颜色 */
function getActionTagType(action) {
    const types = {
        LOGIN: "success",
        USER_REGISTER: "info",
        DOC_UPLOAD: "primary",
        DOC_DELETE: "danger",
        QA_ASK: "warning",
        USER_UPDATE: "info",
        USER_DELETE: "danger",
    };
    return types[action] || "info";
}

/** 获取操作类型的友好显示名 */
function getActionLabel(action) {
    const labels = {
        LOGIN: "登录",
        USER_REGISTER: "注册",
        DOC_UPLOAD: "上传文档",
        DOC_DELETE: "删除文档",
        QA_ASK: "智能问答",
        USER_UPDATE: "修改用户",
        USER_DELETE: "删除用户",
    };
    return labels[action] || action;
}

function onPageChange(newPage) {
    page.value = newPage;
    loadLogs();
}

function onSizeChange(newSize) {
    pageSize.value = newSize;
    page.value = 1;
    loadLogs();
}

onMounted(() => {
    loadLogs();
});
</script>

<style scoped>
.system-log {
    max-width: 1200px;
}

.page-title {
    font-size: 18px;
    color: #303133;
    margin-bottom: 20px;
}

.toolbar {
    margin-bottom: 20px;
}
</style>
