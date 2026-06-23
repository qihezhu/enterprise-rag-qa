<!--
  聊天消息气泡组件
  props: message {role, content, sources, time}
-->
<template>
    <div class="chat-message" :class="message.role === 'user' ? 'user-msg' : 'assistant-msg'">
        <div class="message-avatar">
            <el-avatar :size="36" :icon="message.role === 'user' ? 'UserFilled' : 'Service'" />
        </div>
        <div class="message-body">
            <div class="message-header">
                <span class="message-role">{{ message.role === "user" ? "我" : "知识库助手" }}</span>
                <span class="message-time">{{ message.time }}</span>
            </div>
            <div class="message-content">{{ message.content }}</div>
            <!-- 来源引用（仅助手消息显示） -->
            <div v-if="message.role === 'assistant' && message.sources && message.sources.length > 0" class="message-sources">
                <el-divider content-position="left">参考来源</el-divider>
                <div v-for="(source, idx) in message.sources" :key="idx" class="source-item">
                    <el-tag size="small" type="info">{{ source.file_name }}</el-tag>
                    <span class="source-preview">{{ source.content_preview }}</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
defineProps({
    message: {
        type: Object,
        required: true,
        // {role: 'user'|'assistant', content, sources, time}
    },
});
</script>

<style scoped>
.chat-message {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}

.user-msg {
    flex-direction: row-reverse;
}

.message-body {
    max-width: 70%;
}

.message-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

.user-msg .message-header {
    flex-direction: row-reverse;
}

.message-role {
    font-size: 13px;
    color: #909399;
}

.message-time {
    font-size: 12px;
    color: #c0c4cc;
}

.message-content {
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
}

.user-msg .message-content {
    background: #409eff;
    color: #fff;
}

.assistant-msg .message-content {
    background: #fff;
    color: #303133;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.message-sources {
    margin-top: 8px;
    padding: 8px 12px;
    background: #f5f7fa;
    border-radius: 6px;
}

.source-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
    font-size: 12px;
}

.source-preview {
    color: #909399;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
