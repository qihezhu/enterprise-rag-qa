<!--
  文档列表页面
  展示当前用户上传的知识文档，支持搜索和分页
  管理员在此看到所有用户的文档，普通用户只看到自己的
-->
<template>
    <div class="doc-list-page">
        <div class="page-header">
            <h3>知识文档列表</h3>
        </div>

        <!-- 搜索栏 -->
        <div class="search-bar">
            <el-input
                v-model="keyword"
                placeholder="搜索文档标题..."
                clearable
                @keyup.enter="handleSearch"
                @clear="handleSearch"
            >
                <template #prefix>
                    <el-icon><Search /></el-icon>
                </template>
            </el-input>
            <el-select v-model="selectedTopic" placeholder="主题分类" clearable style="width: 160px" @change="handleSearch">
                <el-option v-for="t in topicOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>

        <!-- 文档列表 -->
        <div v-loading="loading" class="doc-list">
            <el-empty v-if="!loading && documents.length === 0" description="暂无文档" />
            <DocumentCard
                v-for="doc in documents"
                :key="doc.id"
                :document="doc"
                @view="handleView"
                @delete="handleDelete"
            />
        </div>

        <Pagination
            :total="total"
            :page="page"
            :pageSize="pageSize"
            @update:page="onPageChange"
            @update:pageSize="onSizeChange"
        />

        <!-- 文档详情弹窗 -->
        <el-dialog v-model="detailVisible" :title="detailDoc?.title || '文档详情'" width="700px" top="5vh">
            <div v-loading="detailLoading" class="doc-detail">
                <div class="detail-meta">
                    <el-tag :type="fileTypeColor(detailDoc?.file_type)">{{ detailDoc?.file_type?.toUpperCase() }}</el-tag>
                    <span>文件名：{{ detailDoc?.file_name }}</span>
                    <span>上传时间：{{ detailDoc?.created_at }}</span>
                    <span>文本块数：{{ detailDoc?.chunk_count }}</span>
                </div>
                <div class="detail-content">{{ detailDoc?.content || '暂无内容' }}</div>
            </div>
        </el-dialog>
    </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getDocumentListApi, getDocumentDetailApi, deleteDocumentApi, getTopicsApi } from "../../api/document";
import DocumentCard from "../../components/DocumentCard.vue";
import Pagination from "../../components/Pagination.vue";

const documents = ref([]);
const loading = ref(false);
const keyword = ref("");
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

const detailVisible = ref(false);
const detailLoading = ref(false);
const detailDoc = ref(null);
const selectedTopic = ref("");
const topicOptions = ref([]);

/** 加载文档列表 */
async function loadDocuments() {
    loading.value = true;
    try {
        const res = await getDocumentListApi({
            page: page.value,
            page_size: pageSize.value,
            keyword: keyword.value,
            topic: selectedTopic.value || undefined,
        });
        documents.value = res.data.items;
        total.value = res.data.total;
    } catch {
        // 错误已在拦截器处理
    } finally {
        loading.value = false;
    }
}

/** 搜索 */
function handleSearch() {
    page.value = 1;
    loadDocuments();
}

/** 查看文档详情 */
async function handleView(docId) {
    detailVisible.value = true;
    detailLoading.value = true;
    detailDoc.value = null;
    try {
        const res = await getDocumentDetailApi(docId);
        detailDoc.value = res.data;
    } catch {
        ElMessage.error("获取文档详情失败");
        detailVisible.value = false;
    } finally {
        detailLoading.value = false;
    }
}

/** 文件类型对应标签颜色 */
function fileTypeColor(fileType) {
    const map = { pdf: "danger", docx: "primary", txt: "success", md: "warning" };
    return map[fileType] || "info";
}

/** 删除文档 */
async function handleDelete(docId) {
    try {
        await ElMessageBox.confirm("确定要删除该文档吗？删除后不可恢复。", "确认删除", {
            type: "warning",
        });
        await deleteDocumentApi(docId);
        ElMessage.success("文档删除成功");
        loadDocuments();
    } catch {
        // 用户取消
    }
}

/** 页码改变 */
function onPageChange(newPage) {
    page.value = newPage;
    loadDocuments();
}

/** 每页条数改变 */
function onSizeChange(newSize) {
    pageSize.value = newSize;
    page.value = 1;
    loadDocuments();
}

onMounted(async () => {
    try {
        const res = await getTopicsApi();
        topicOptions.value = res.data || [];
    } catch { /* ignore */ }
    loadDocuments();
});
</script>

<style scoped>
.doc-list-page {
    max-width: 1000px;
}

.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
}

.page-header h3 {
    font-size: 18px;
    color: #303133;
}

.search-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}

.search-bar .el-input {
    width: 320px;
}

.doc-list {
    min-height: 200px;
}

.detail-meta {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    padding-bottom: 16px;
    border-bottom: 1px solid #ebeef5;
    margin-bottom: 16px;
    font-size: 13px;
    color: #909399;
}

.detail-content {
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.8;
    font-size: 14px;
    color: #303133;
    max-height: 60vh;
    overflow-y: auto;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 6px;
}
</style>
