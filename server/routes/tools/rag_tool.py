"""
知识库 RAG Tool 端点
将现有 RAG 问答系统封装为千问平台 Tool (search_knowledge_base)
零改动复用 rag_service.py / vector_store_service.py / document_service.py
"""
from flask import request, current_app
from ...services.rag_service import RAGService
from ...middleware.auth_middleware import require_tool_api_key
from ...utils.helpers import success_response, error_response, clean_tool_inputs

from .approval_tool import tool_bp

# 懒初始化 RAG 服务（复用现有配置）
_rag_service = None


def _get_rag_service():
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(current_app.config)
    return _rag_service


@tool_bp.route("/knowledge/search", methods=["POST"])
@require_tool_api_key
def search_knowledge():
    """
    知识库检索问答
    千问平台注册为 search_knowledge_base Tool

    输入: {"query": "公司年假政策是什么？", "topic": "人力资源"}  (topic可选)
    输出: {"answer": "...", "sources": [{file_name, chunk_index, content_preview, relevance_score}]}
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    query = data.get("query", "")
    topic = data.get("topic", None)

    if not query:
        return error_response("缺少 query 参数", 400)

    try:
        rag = _get_rag_service()
        result = rag.ask(query, topic=topic)

        # 安全网：确保答案末尾包含真实的来源文件名
        sources = result.get("sources", [])
        if sources:
            real_names = list(dict.fromkeys(s["file_name"] for s in sources if s.get("file_name")))
            if real_names:
                # 检查答案中是否已包含真实来源文件名
                answer = result["answer"]
                has_real_source = any(name in answer for name in real_names)
                if not has_real_source:
                    # LLM可能编造了来源名，在末尾追加真实来源
                    source_line = "\n来源：" + "、".join(real_names)
                    result["answer"] = answer + source_line

        return success_response(result, "查询完成")
    except Exception as e:
        current_app.logger.error(f"[RAG Tool] 查询异常: {e}", exc_info=True)
        return error_response(f"知识库查询失败: {str(e)}", 500)
