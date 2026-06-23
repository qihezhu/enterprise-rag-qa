<!--
  文档管理页面（管理员视角）
  查看和管理所有用户上传的知识文档，支持搜索和删除
-->
<template>
    <div class="doc-manage">
        <h3 class="page-title">文档管理</h3>

        <!-- 搜索栏 -->
        <div class="toolbar">
            <el-input
                v-model="keyword"
                placeholder="搜索文档标题..."
                clearable
                style="width: 280px"
                @keyup.enter="handleSearch"
                @clear="handleSearch"
            >
                <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-select v-model="selectedTopic" placeholder="主题分类" clearable style="width: 160px" @change="handleSearch">
                <el-option v-for="t in topicOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>

        <!-- 文档表格 -->
        <div class="table-box card-box">
            <el-table :data="documents" v-loading="loading" stripe>
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="title" label="文档标题" min-width="200" show-overflow-tooltip />
                <el-table-column prop="file_type" label="类型" width="80">
                    <template #default="{ row }">
                        <el-tag size="small">{{ row.file_type?.toUpperCase() }}</el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="topic" label="主题分类" width="110">
                    <template #default="{ row }">
                        <el-tag v-if="row.topic" size="small" :color="getTopicColor(row.topic)" effect="dark">
                            {{ row.topic }}
                        </el-tag>
                        <span v-else style="color:#c0c4cc">-</span>
                    </template>
                </el-table-column>
                <el-table-column prop="chunk_count" label="分块数" width="80" />
                <el-table-column prop="uploader_name" label="上传者" width="120" />
                <el-table-column prop="updated_at" label="更新时间" width="170" />
                <el-table-column label="操作" width="180" fixed="right">
                    <template #default="{ row }">
                        <el-button text type="primary" size="small" @click="handleView(row)">
                            查看
                        </el-button>
                        <el-button text type="warning" size="small" @click="handleEdit(row)">
                            编辑
                        </el-button>
                        <el-button text type="danger" size="small" @click="handleDelete(row)">
                            删除
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>
        </div>

        <Pagination
            :total="total"
            :page="page"
            :pageSize="pageSize"
            @update:page="onPageChange"
            @update:pageSize="onSizeChange"
        />

        <!-- 文档详情对话框 -->
        <el-dialog v-model="detailVisible" title="文档详情" width="700px">
            <div v-if="detail">
                <el-descriptions :column="2" border>
                    <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
                    <el-descriptions-item label="文件名">{{ detail.file_name }}</el-descriptions-item>
                    <el-descriptions-item label="类型">{{ detail.file_type }}</el-descriptions-item>
                    <el-descriptions-item label="分块数">{{ detail.chunk_count }}</el-descriptions-item>
                    <el-descriptions-item label="上传者">{{ detail.uploader_name }}</el-descriptions-item>
                    <el-descriptions-item label="上传时间">{{ detail.created_at }}</el-descriptions-item>
                </el-descriptions>
                <div class="content-section">
                    <h4>文档内容预览</h4>
                    <div class="content-preview">{{ detail.content_preview || detail.content }}</div>
                </div>
            </div>
        </el-dialog>

        <!-- 文档编辑对话框 -->
        <el-dialog v-model="editVisible" title="编辑文档" width="500px">
            <el-form v-if="editForm.id" :model="editForm" label-position="top">
                <el-form-item label="文档标题">
                    <el-input v-model="editForm.title" placeholder="请输入文档标题" />
                </el-form-item>
                <el-form-item label="主题分类">
                    <el-select v-model="editForm.topic" placeholder="请选择主题分类" clearable style="width: 100%">
                        <el-option v-for="t in topicOptions" :key="t.value" :label="t.label" :value="t.value" />
                    </el-select>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="editVisible = false">取消</el-button>
                <el-button type="primary" :loading="editSaving" @click="handleEditSave">保存</el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getDocumentListApi, getDocumentDetailApi, deleteDocumentApi, updateDocumentApi, getTopicsApi } from "../../api/document";
import { getTopicColor } from "../../utils";
import Pagination from "../../components/Pagination.vue";

const documents = ref([]);
const loading = ref(false);
const keyword = ref("");
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

const detailVisible = ref(false);
const detail = ref(null);
const editVisible = ref(false);
const editSaving = ref(false);
const editForm = ref({ id: null, title: "", topic: "" });
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
    } finally {
        loading.value = false;
    }
}

function handleSearch() {
    page.value = 1;
    loadDocuments();
}

/** 查看文档详情 */
async function handleView(row) {
    try {
        const res = await getDocumentDetailApi(row.id);
        detail.value = res.data;
        detailVisible.value = true;
    } catch {
        // 错误已在拦截器处理
    }
}

/** 打开编辑对话框 */
function handleEdit(row) {
    editForm.value = {
        id: row.id,
        title: row.title,
        topic: row.topic || "",
    };
    editVisible.value = true;
}

/** 保存编辑 */
async function handleEditSave() {
    if (!editForm.value.title.trim()) {
        ElMessage.warning("标题不能为空");
        return;
    }
    editSaving.value = true;
    try {
        await updateDocumentApi(editForm.value.id, {
            title: editForm.value.title.trim(),
            topic: editForm.value.topic || "",
        });
        ElMessage.success("文档更新成功");
        editVisible.value = false;
        loadDocuments();
    } catch {
        // 错误已在拦截器处理
    } finally {
        editSaving.value = false;
    }
}

/** 删除文档 */
async function handleDelete(row) {
    try {
        await ElMessageBox.confirm(
            `确定要删除文档 "${row.title}" 吗？该操作不可恢复。`,
            "确认删除",
            { type: "warning" }
        );
        await deleteDocumentApi(row.id);
        ElMessage.success("文档已删除");
        loadDocuments();
    } catch {
        // 用户取消
    }
}

function onPageChange(newPage) {
    page.value = newPage;
    loadDocuments();
}

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
.doc-manage {
    max-width: 1200px;
}

.page-title {
    font-size: 18px;
    color: #303133;
    margin-bottom: 20px;
}

.toolbar {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}

.content-section {
    margin-top: 20px;
}

.content-section h4 {
    font-size: 14px;
    color: #303133;
    margin-bottom: 8px;
}

.content-preview {
    max-height: 300px;
    overflow-y: auto;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 6px;
    font-size: 13px;
    line-height: 1.8;
    white-space: pre-wrap;
}
</style>
