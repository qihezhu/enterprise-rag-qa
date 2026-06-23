/**
 * 对话状态管理（Pinia Store）
 * 管理聊天消息列表和发送消息操作
 */
import { defineStore } from "pinia";
import { ref } from "vue";
import { askQuestionApi } from "../api/qa";

export const useChatStore = defineStore("chat", () => {
    // ==================== 状态 ====================
    /** 消息列表 [{role: 'user'|'assistant', content, sources, time}] */
    const messages = ref([]);
    /** 是否正在等待回答 */
    const loading = ref(false);

    // ==================== 操作 ====================

    /**
     * 发送问题并获取回答
     * @param {string} question 用户问题
     */
    async function sendQuestion(question, topic = null) {
        // 添加用户消息
        messages.value.push({
            role: "user",
            content: question,
            topic: topic,
            time: new Date().toLocaleTimeString(),
        });

        loading.value = true;

        try {
            const payload = { question };
            if (topic) {
                payload.topic = topic;
            }
            const res = await askQuestionApi(payload);
            const { answer, sources } = res.data;

            // 添加助手回答
            messages.value.push({
                role: "assistant",
                content: answer,
                sources: sources || [],
                time: new Date().toLocaleTimeString(),
            });
        } catch {
            // 请求失败时也保持用户消息在列表中
            messages.value.push({
                role: "assistant",
                content: "抱歉，问答服务暂时不可用，请稍后重试。",
                sources: [],
                time: new Date().toLocaleTimeString(),
            });
        } finally {
            loading.value = false;
        }
    }

    /**
     * 清空当前对话记录
     */
    function clearMessages() {
        messages.value = [];
    }

    return { messages, loading, sendQuestion, clearMessages };
});
