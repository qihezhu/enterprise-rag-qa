<!--
  对话历史页面
  展示当前用户以往的智能问答记录，支持分页、查看详情和删除
  管理员可查看所有用户的对话记录，普通用户只能查看自己的
-->
<template>
    <div class="history-page">
        <h3 class="page-title">对话历史</h3>

        <div class="table-box card-box" v-loading="loading">
            <el-empty v-if="!loading && conversations.length === 0" description="暂无对话记录" />

            <div v-else>
                <!-- 对话列表 -->
                <div
                    v-for="conv in conversations"
                    :key="conv.id"
                    class="history-item"
                >
                    <div class="item-header" @click="toggleExpand(conv.id)">
                        <div class="item-question">
                            <el-icon><ChatDotRound /></el-icon>
                            <span class="question-text">{{ conv.question }}</span>
                        </div>
                        <div class="item-meta">
                            <span v-if="isAdmin" class="item-user">{{ conv.username }}</span>
                            <span class="item-time">{{ conv.created_at }}</span>
                            <el-icon class="expand-icon" :class="{ expanded: expandedId === conv.id }">
                                <ArrowDown />
                            </el-icon>
                        </div>
                    </div>

                    <!-- 展开的回答详情 -->
                    <div v-if="expandedId === conv.id" class="item-detail">
                        <div class="answer-title">
                            <el-icon><Service /></el-icon> 回答：
                        </div>
                        <div class="answer-content">{{ conv.answer }}</div>

                        <!-- 参考来源 -->
                        <div v-if="conv.sources && conv.sources.length > 0" class="sources-section">
                            <div class="sources-title">参考来源：</div>
                            <div v-for="(source, idx) in conv.sources" :key="idx" class="source-item">
                                <el-tag size="small" type="info">{{ source.file_name }}</el-tag>
                                <span class="source-text">{{ source.content_preview }}</span>
                            </div>
                        </div>

                        <div class="detail-actions">
                            <el-button text type="danger" size="small" @click="handleDelete(conv.id)">
                                <el-icon><Delete /></el-icon> 删除
                            </el-button>
                        </div>
                    </div>
                </div>
            </div>
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
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getQaHistoryApi, deleteQaHistoryApi } from "../../api/qa";
import { useAuthStore } from "../../stores/auth";
import Pagination from "../../components/Pagination.vue";

const authStore = useAuthStore();
const conversations = ref([]);
const loading = ref(false);
const expandedId = ref(null);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

const isAdmin = computed(() => authStore.isAdmin);

/** 加载对话历史 */
async function loadHistory() {
    loading.value = true;
    try {
        const res = await getQaHistoryApi({
            page: page.value,
            page_size: pageSize.value,
        });
        conversations.value = res.data.items;
        total.value = res.data.total;
    } finally {
        loading.value = false;
    }
}

/** 展开/收起回答详情 */
function toggleExpand(id) {
    expandedId.value = expandedId.value === id ? null : id;
}

/** 删除某条对话记录 */
async function handleDelete(id) {
    try {
        await ElMessageBox.confirm("确定要删除这条对话记录吗？", "确认删除", {
            type: "warning",
        });
        await deleteQaHistoryApi(id);
        ElMessage.success("删除成功");
        // 如果删除的是当前展开的记录，收起
        if (expandedId.value === id) {
            expandedId.value = null;
        }
        loadHistory();
    } catch {
        // 用户取消
    }
}

function onPageChange(newPage) {
    page.value = newPage;
    loadHistory();
}

function onSizeChange(newSize) {
    pageSize.value = newSize;
    page.value = 1;
    loadHistory();
}

onMounted(() => {
    loadHistory();
});
</script>

<style scoped>
.history-page {
    max-width: 900px;
}

.page-title {
    font-size: 18px;
    color: #303133;
    margin-bottom: 20px;
}

/* ==================== 对话列表项 ==================== */
.history-item {
    border-bottom: 1px solid #ebeef5;
}

.history-item:last-child {
    border-bottom: none;
}

.item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 0;
    cursor: pointer;
    transition: background 0.15s;
}

.item-header:hover {
    background: #f5f7fa;
    margin: 0 -20px;
    padding: 16px 20px;
    border-radius: 4px;
}

.item-question {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    overflow: hidden;
}

.item-question .el-icon {
    color: #409eff;
    flex-shrink: 0;
}

.question-text {
    font-size: 14px;
    color: #303133;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.item-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
    margin-left: 16px;
    font-size: 12px;
    color: #909399;
}

.item-user {
    color: #409eff;
    font-weight: 500;
}

.expand-icon {
    transition: transform 0.2s;
}

.expand-icon.expanded {
    transform: rotate(180deg);
}

/* ==================== 展开详情 ==================== */
.item-detail {
    padding: 0 0 20px 24px;
}

.answer-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: #606266;
    margin-bottom: 8px;
}

.answer-content {
    padding: 12px;
    background: #f5f7fa;
    border-radius: 6px;
    font-size: 14px;
    line-height: 1.8;
    white-space: pre-wrap;
    word-break: break-word;
}

.sources-section {
    margin-top: 12px;
}

.sources-title {
    font-size: 13px;
    color: #606266;
    margin-bottom: 6px;
}

.source-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}

.source-text {
    font-size: 12px;
    color: #909399;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-actions {
    margin-top: 12px;
    text-align: right;
}
</style>
