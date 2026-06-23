import request from "./request";

/** 获取审批记录列表 */
export function getApprovalRecordsApi(params) {
  return request.get("/wecom/approval-records", { params });
}

/** 更新审批记录状态 */
export function updateApprovalStatusApi(id, status) {
  return request.put(`/wecom/approval-records/${id}/status`, { status });
}

/** 管理员代提交审批 */
export function adminSubmitApprovalApi(data) {
  return request.post("/wecom/approval-submit", data);
}
