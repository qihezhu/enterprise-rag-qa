import request from "./request";

/** 获取企微连接状态 */
export function getWeComStatusApi() {
  return request.get("/wecom/status");
}

/** 测试企微 Token */
export function testTokenApi() {
  return request.post("/wecom/test-token");
}
