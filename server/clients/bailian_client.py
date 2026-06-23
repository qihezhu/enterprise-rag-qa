"""
百炼 (Bailian) Agent 客户端
封装 DashScope Application.call()，支持多轮会话
"""
from flask import current_app


class BailianClient:
    """百炼 Agent 客户端，单例模式"""

    def __init__(self, app=None):
        self._api_key = None
        self._app_id = None
        self._timeout = 120
        if app:
            self.init_app(app)

    def init_app(self, app):
        self._api_key = app.config.get("DASHSCOPE_API_KEY", "")
        self._app_id = app.config.get("BAILIAN_APP_ID", "")
        self._timeout = app.config.get("BAILIAN_TIMEOUT", 120)

    @property
    def configured(self):
        return bool(self._api_key and self._app_id)

    def chat(self, user_id, message):
        """
        调用百炼 Agent 进行对话
        user_id 直接作为 session_id，百炼云端维护多轮上下文
        返回 {"success": bool, "text": str, "usage": dict|None}
        """
        if not self.configured:
            return {"success": False, "text": "", "error": "未配置 DASHSCOPE_API_KEY 或 BAILIAN_APP_ID"}

        import dashscope

        # 确保 API Key 已设置（DashScope SDK 使用模块级全局变量）
        dashscope.api_key = self._api_key

        try:
            response = dashscope.Application.call(
                app_id=self._app_id,
                prompt=message,
                session_id=user_id,
            )
        except Exception as e:
            current_app.logger.error(f"[Bailian] API 调用异常: {e}", exc_info=True)
            return {"success": False, "text": "", "error": str(e)}

        if response.status_code == 200:
            text = ""
            if hasattr(response, "output") and response.output:
                text = response.output.get("text", "")
            usage = response.usage if hasattr(response, "usage") and response.usage else None
            current_app.logger.info(f"[Bailian] Agent 回复成功 len={len(text)}")
            return {"success": True, "text": text, "usage": usage}
        else:
            err = f"status={response.status_code} code={response.code} msg={response.message}"
            current_app.logger.error(f"[Bailian] Agent 调用失败: {err}")
            return {"success": False, "text": "", "error": err}


bailian_client = BailianClient()
