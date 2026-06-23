/**
 * 文档管理相关API接口
 */
import request from "./request";

/** 获取文档列表（分页+搜索） */
export function getDocumentListApi(params) {
    return request.get("/documents", { params });
}

/** 获取文档详情 */
export function getDocumentDetailApi(id) {
    return request.get(`/documents/${id}`);
}

/** 上传文档（multipart/form-data） */
export function uploadDocumentApi(formData) {
    return request.post("/documents", formData, {
        headers: { "Content-Type": "multipart/form-data" },
    });
}

/** 更新文档信息 */
export function updateDocumentApi(id, data) {
    return request.put(`/documents/${id}`, data);
}

/** 删除文档 */
export function deleteDocumentApi(id) {
    return request.delete(`/documents/${id}`);
}

/** 获取主题分类列表 */
export function getTopicsApi() {
    return request.get("/documents/topics");
}
