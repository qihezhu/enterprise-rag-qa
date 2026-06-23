/**
 * 认证相关API接口
 */
import request from "./request";

/** 用户登录 */
export function loginApi(data) {
    return request.post("/auth/login", data);
}

/** 用户注册 */
export function registerApi(data) {
    return request.post("/auth/register", data);
}

/** 获取当前登录用户信息 */
export function getUserInfoApi() {
    return request.get("/auth/userinfo");
}
