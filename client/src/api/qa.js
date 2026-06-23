/**
 * 智能问答相关API接口
 */
import request from "./request";

/** 提交问题，获取RAG回答 */
export function askQuestionApi(data) {
    return request.post("/qa/ask", data);
}

/** 获取对话历史 */
export function getQaHistoryApi(params) {
    return request.get("/qa/history", { params });
}

/** 删除某条对话记录 */
export function deleteQaHistoryApi(id) {
    return request.delete(`/qa/history/${id}`);
}
