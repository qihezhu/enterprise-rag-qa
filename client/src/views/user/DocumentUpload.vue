<!--
  文档上传页面
  支持拖拽或点击上传PDF/DOCX/TXT/MD文件到知识库
  上传后自动解析、分块、向量化并存入Chroma
-->
<template>
    <div class="upload-page">
        <h3 class="page-title">上传知识文档</h3>

        <div class="upload-card">
            <!-- 文件拖拽上传区域 -->
            <el-upload
                ref="uploadRef"
                class="upload-area"
                drag
                :auto-upload="false"
                :limit="1"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                :accept="'.pdf,.docx,.txt,.md'"
            >
                <el-icon class="upload-icon" size="48"><UploadFilled /></el-icon>
                <div class="upload-text">
                    <p>将文件拖到此处，或 <em>点击上传</em></p>
                    <span>支持 PDF、DOCX、TXT、Markdown 格式，单个文件不超过16MB</span>
                </div>
            </el-upload>

            <!-- 文档信息表单 -->
            <el-form v-if="selectedFile" :model="form" label-position="top" class="upload-form">
                <el-form-item label="文档标题（可选，默认使用文件名）">
                    <el-input v-model="form.title" placeholder="请输入文档标题" />
                </el-form-item>
                <el-form-item label="主题分类">
                    <el-select v-model="form.topic" placeholder="请选择主题分类" clearable style="width: 100%">
                        <el-option v-for="t in topicOptions" :key="t.value" :label="t.label" :value="t.value" />
                    </el-select>
                </el-form-item>
                <el-form-item label="文件信息">
                    <div class="file-info">
                        <el-tag>{{ selectedFile.name }}</el-tag>
                        <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
                    </div>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" :loading="uploading" @click="handleUpload">
                        {{ uploading ? "正在上传并处理中..." : "确认上传" }}
                    </el-button>
                </el-form-item>
            </el-form>
        </div>
    </div>
</template>

<script setup>
import { reactive, ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { uploadDocumentApi, getTopicsApi } from "../../api/document";
import { formatFileSize } from "../../utils";
import { useRouter } from "vue-router";

const router = useRouter();
const uploadRef = ref(null);
const selectedFile = ref(null);
const uploading = ref(false);
const topicOptions = ref([]);

/** 上传表单 */
const form = reactive({
    title: "",
    topic: "",
});

/** 文件选择变化时 */
function handleFileChange(file) {
    selectedFile.value = file.raw;
    if (!form.title) {
        // 默认使用文件名（去掉扩展名）作为标题
        const name = file.name.replace(/\.[^.]+$/, "");
        form.title = name;
    }
}

/** 移除文件时 */
function handleFileRemove() {
    selectedFile.value = null;
    form.title = "";
}

/** 加载主题列表 */
onMounted(async () => {
    try {
        const res = await getTopicsApi();
        topicOptions.value = res.data || [];
    } catch { /* ignore */ }
});

/** 确认上传 */
async function handleUpload() {
    if (!selectedFile.value) {
        ElMessage.warning("请先选择文件");
        return;
    }

    // 校验文件大小（16MB）
    if (selectedFile.value.size > 16 * 1024 * 1024) {
        ElMessage.warning("文件大小不能超过16MB");
        return;
    }

    uploading.value = true;
    try {
        const formData = new FormData();
        formData.append("file", selectedFile.value);
        if (form.title) {
            formData.append("title", form.title);
        }
        if (form.topic) {
            formData.append("topic", form.topic);
        }

        const res = await uploadDocumentApi(formData);
        ElMessage.success(res.message || "文档上传成功");
        router.push("/admin/documents");
    } catch {
        // 错误已在拦截器处理
    } finally {
        uploading.value = false;
    }
}
</script>

<style scoped>
.upload-page {
    max-width: 700px;
}

.page-title {
    font-size: 18px;
    color: #303133;
    margin-bottom: 20px;
}

.upload-card {
    background: #fff;
    border-radius: 8px;
    padding: 32px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.upload-area {
    width: 100%;
}

.upload-icon {
    color: #409eff;
}

.upload-text p {
    font-size: 15px;
    color: #606266;
    margin: 8px 0;
}

.upload-text em {
    color: #409eff;
    font-style: normal;
}

.upload-text span {
    font-size: 12px;
    color: #909399;
}

.upload-form {
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid #ebeef5;
}

.file-info {
    display: flex;
    align-items: center;
    gap: 12px;
}

.file-size {
    font-size: 13px;
    color: #909399;
}
</style>
