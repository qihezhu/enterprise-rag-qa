<!--
  文档卡片组件
  用于文档列表页展示每个知识文档
  props: document {id, title, file_name, file_type, chunk_count, uploader_name, created_at}
-->
<template>
    <div class="doc-card">
        <div class="doc-icon" :style="{ background: fileColor }">
            {{ fileType.toUpperCase() }}
        </div>
        <div class="doc-info">
            <div class="doc-title">{{ document.title }}</div>
            <div class="doc-meta">
                <el-tag v-if="document.topic" size="small" :color="getTopicColor(document.topic)" effect="dark" class="topic-tag">
                    {{ document.topic }}
                </el-tag>
                <span>{{ document.file_name }}</span>
                <el-divider direction="vertical" />
                <span>{{ document.chunk_count }} 个文本块</span>
                <el-divider direction="vertical" />
                <span>{{ document.created_at }}</span>
            </div>
        </div>
        <div class="doc-actions">
            <el-button text type="primary" @click="$emit('view', document.id)">查看</el-button>
            <el-button text type="danger" @click="$emit('delete', document.id)">删除</el-button>
        </div>
    </div>
</template>

<script setup>
import { computed } from "vue";
import { getFileTypeColor, getTopicColor } from "../utils";

const props = defineProps({
    document: { type: Object, required: true },
});

defineEmits(["view", "delete"]);

/** 文件类型对应的颜色 */
const fileColor = computed(() => getFileTypeColor(props.document.file_type));
/** 文件类型缩写 */
const fileType = computed(() => props.document.file_type || "?");
</script>

<style scoped>
.doc-card {
    display: flex;
    align-items: center;
    padding: 16px;
    background: #fff;
    border-radius: 8px;
    margin-bottom: 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
    transition: box-shadow 0.2s;
}

.doc-card:hover {
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.doc-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 12px;
    font-weight: bold;
    border-radius: 8px;
    flex-shrink: 0;
}

.doc-info {
    flex: 1;
    margin-left: 16px;
    overflow: hidden;
}

.doc-title {
    font-size: 15px;
    font-weight: 500;
    color: #303133;
    margin-bottom: 6px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.doc-meta {
    font-size: 12px;
    color: #909399;
    display: flex;
    align-items: center;
    gap: 4px;
}

.doc-actions {
    flex-shrink: 0;
    margin-left: 16px;
}
</style>
