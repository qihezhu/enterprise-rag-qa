/**
 * 管理员后台相关API接口
 */
import request from "./request";

/** 获取仪表盘统计数据 */
export function getStatisticsApi() {
    return request.get("/admin/statistics");
}

/** 获取用户列表 */
export function getUserListApi(params) {
    return request.get("/admin/users", { params });
}

/** 修改用户信息（状态/角色） */
export function updateUserApi(id, data) {
    return request.put(`/admin/users/${id}`, data);
}

/** 删除用户 */
export function deleteUserApi(id) {
    return request.delete(`/admin/users/${id}`);
}

/** 获取系统日志 */
export function getSystemLogsApi(params) {
    return request.get("/admin/logs", { params });
}
