<!--
  智能问答聊天页面
  用户在此与知识库助手对话，基于RAG技术从企业知识库检索并生成回答
-->
<template>
    <div class="qa-chat">
        <div class="chat-header">
            <h3>智能问答助手</h3>
            <el-button text @click="handleClear">清空对话</el-button>
        </div>

        <!-- 消息列表 -->
        <div class="chat-messages" ref="msgContainerRef">
            <div v-if="chatStore.messages.length === 0" class="chat-welcome">
                <el-icon size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
                <p>您好！我是企业知识库智能助手</p>
                <span>您可以向我提问任何企业知识库相关的问题，例如：</span>
                <div class="example-questions">
                    <el-tag
                        v-for="q in exampleQuestions"
                        :key="q"
                        class="example-tag"
                        @click="handleAsk(q)"
                    >
                        {{ q }}
                    </el-tag>
                </div>
            </div>

            <ChatMessage v-for="(msg, idx) in chatStore.messages" :key="idx" :message="msg" />

            <!-- 加载状态 -->
            <div v-if="chatStore.loading" class="loading-msg">
                <el-icon class="loading-icon" size="20"><Loading /></el-icon>
                <span>正在思考中...</span>
            </div>
        </div>

        <!-- 主题选择 -->
        <div class="topic-bar">
            <span class="topic-hint">限定主题：</span>
            <el-select v-model="selectedTopic" placeholder="全部主题" clearable size="small" style="width: 200px">
                <el-option v-for="t in topicOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
        </div>

        <!-- 输入区域 -->
        <div class="chat-input">
            <el-input
                v-model="inputText"
                type="textarea"
                :rows="3"
                placeholder="请输入您的问题...（Enter发送，Shift+Enter换行）"
                :disabled="chatStore.loading"
                @keydown.enter.exact.prevent="handleSend"
            />
            <el-button
                type="primary"
                :disabled="!inputText.trim() || chatStore.loading"
                :loading="chatStore.loading"
                @click="handleSend"
            >
                发送 (Enter)
            </el-button>
        </div>
    </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { useChatStore } from "../../stores/chat";
import { getTopicsApi } from "../../api/document";
import ChatMessage from "../../components/ChatMessage.vue";

const chatStore = useChatStore();
const inputText = ref("");
const msgContainerRef = ref(null);
const selectedTopic = ref("");
const topicOptions = ref([]);

/** 示例问题 */
const exampleQuestions = [
    "公司的年假政策是什么？",
    "入职需要准备哪些材料？",
    "IT安全密码有什么要求？",
    "加班费如何计算？",
];

/** 自动滚动到底部 */
watch(
    () => chatStore.messages.length,
    async () => {
        await nextTick();
        if (msgContainerRef.value) {
            msgContainerRef.value.scrollTop = msgContainerRef.value.scrollHeight;
        }
    }
);

/** 发送问题 */
async function handleSend() {
    const question = inputText.value.trim();
    if (!question || chatStore.loading) return;

    inputText.value = "";
    await chatStore.sendQuestion(question, selectedTopic.value || null);
}

/** 点击示例问题 */
function handleAsk(question) {
    inputText.value = question;
    handleSend();
}

/** 清空对话 */
function handleClear() {
    chatStore.clearMessages();
    ElMessage.success("对话已清空");
}

onMounted(async () => {
    try {
        const res = await getTopicsApi();
        topicOptions.value = res.data || [];
    } catch { /* ignore */ }
});
</script>

<style scoped>
.qa-chat {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 100px);
    max-width: 900px;
    margin: 0 auto;
}

.chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 0;
}

.chat-header h3 {
    font-size: 18px;
    color: #303133;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px 0;
}

.chat-welcome {
    text-align: center;
    padding: 60px 20px;
}

.chat-welcome p {
    font-size: 18px;
    color: #303133;
    margin: 16px 0 8px;
}

.chat-welcome span {
    font-size: 14px;
    color: #909399;
}

.example-questions {
    margin-top: 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
}

.example-tag {
    cursor: pointer;
}

.example-tag:hover {
    background: #ecf5ff;
    border-color: #409eff;
    color: #409eff;
}

.loading-msg {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    color: #909399;
    font-size: 14px;
}

.loading-icon {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.topic-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
}

.topic-hint {
    font-size: 13px;
    color: #909399;
    white-space: nowrap;
}

.chat-input {
    display: flex;
    align-items: flex-end;
    gap: 12px;
    padding: 16px 0;
    border-top: 1px solid #e4e7ed;
    background: #f0f2f5;
}
</style>
