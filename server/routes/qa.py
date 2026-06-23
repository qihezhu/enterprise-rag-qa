"""
智能问答路由模块
处理用户提问（RAG检索增强生成）、对话历史查询和删除
"""
from flask import Blueprint, request, g, current_app
from ..extensions import db
from ..models.conversation import Conversation
from ..models.system_log import SystemLog
from ..middleware.auth_middleware import login_required
from ..utils.helpers import success_response, error_response, paginated_response

# 创建问答蓝图，URL前缀 /api/qa
qa_bp = Blueprint("qa", __name__, url_prefix="/api/qa")


def get_rag_service():
    """
    获取RAG服务实例（懒加载，避免循环导入）
    返回：RAGService实例
    """
    from ..services.rag_service import RAGService
    return RAGService(current_app.config)


@qa_bp.route("/ask", methods=["POST"])
@login_required
def ask_question():
    """
    智能问答接口：用户提交问题，系统执行RAG流程并返回回答
    请求体：{"question": "公司年假有多少天？"}
    流程：问题向量化 → Chroma检索 → 拼接上下文 → LLM生成回答 → 保存对话记录
    """
    data = request.get_json()
    if not data:
        return error_response("请提供问题内容", 400)

    question = data.get("question", "").strip()
    if not question:
        return error_response("问题不能为空", 400)

    if len(question) > 2000:
        return error_response("问题长度不能超过2000字符", 400)

    # 可选的主题过滤
    from ..utils.helpers import TOPIC_OPTIONS
    topic = data.get("topic", "").strip() or None
    if topic and topic not in TOPIC_OPTIONS:
        topic = None

    # 执行RAG问答流程
    try:
        rag_service = get_rag_service()
        # 检查向量库状态（用于诊断检索是否正常）
        vector_stats = rag_service.get_vector_store_stats()
        print(f"[RAG诊断] 向量库状态: {vector_stats}, topic: {topic or '全部'}")
        result = rag_service.ask(question, topic=topic)
        result["vector_store_stats"] = vector_stats
        print(f"[RAG诊断] 检索到 {len(result.get('sources', []))} 个相关文档块")
    except Exception as e:
        # 如果Ollama服务未启动或其他异常
        print(f"[RAG诊断] 问答异常: {e}")
        return error_response(f"问答服务异常: {str(e)}", 500)

    # 保存对话记录到MySQL
    conversation = Conversation(
        user_id=g.current_user.id,
        question=question,
        answer=result["answer"],
        sources=result["sources"],
    )
    db.session.add(conversation)

    # 记录操作日志
    log = SystemLog(
        user_id=g.current_user.id,
        action="QA_ASK",
        description=f"提问: {question[:200]}",
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    return success_response(data={
        "id": conversation.id,
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"],
        "vector_store_stats": result.get("vector_store_stats", {}),
        "created_at": conversation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    })


@qa_bp.route("/history", methods=["GET"])
@login_required
def get_history():
    """
    获取当前用户的对话历史（分页）
    查询参数：page(页码), page_size(每页条数)
    管理员可查看所有用户的对话记录
    """
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    query = Conversation.query

    # 非管理员只能看自己的对话
    if not g.current_user.is_admin():
        query = query.filter(Conversation.user_id == g.current_user.id)

    pagination = query.order_by(Conversation.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )

    items = [conv.to_dict() for conv in pagination.items]

    return success_response(data=paginated_response(
        items=items,
        total=pagination.total,
        page=page,
        page_size=page_size,
    ))


@qa_bp.route("/history/<int:conv_id>", methods=["DELETE"])
@login_required
def delete_history(conv_id):
    """
    删除某条对话记录（只能删除自己的记录，管理员可删除任何记录）
    """
    conv = Conversation.query.get(conv_id)
    if conv is None:
        return error_response("对话记录不存在", 404)

    if not g.current_user.is_admin() and conv.user_id != g.current_user.id:
        return error_response("无权限删除该记录", 403)

    db.session.delete(conv)
    db.session.commit()

    return success_response(message="删除成功")
