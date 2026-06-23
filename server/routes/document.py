"""
文档管理路由模块
处理知识文档的上传、列表查询、详情查看、更新和删除
"""
import os
import uuid
from datetime import datetime
from flask import Blueprint, request, g, current_app
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models.document import Document
from ..models.document_chunk import DocumentChunk
from ..models.system_log import SystemLog
from ..middleware.auth_middleware import login_required, admin_required
from ..utils.helpers import success_response, error_response, paginated_response, allowed_file, get_file_extension, TOPIC_OPTIONS

# 创建文档管理蓝图，URL前缀 /api/documents
doc_bp = Blueprint("document", __name__, url_prefix="/api/documents")


@doc_bp.route("", methods=["GET"])
@login_required
def list_documents():
    """
    文档列表接口（分页 + 关键词搜索）
    查询参数：page(页码), page_size(每页条数), keyword(搜索关键词)
    所有登录用户均可查看全部知识库文档
    """
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 10, type=int)
    keyword = request.args.get("keyword", "").strip()
    topic = request.args.get("topic", "").strip()

    # 基础查询：只查未删除的文档，所有登录用户均可查看全部知识库文档
    query = Document.query.filter(Document.status == 1)

    # 主题筛选
    if topic:
        query = query.filter(Document.topic == topic)

    # 关键词搜索（标题或内容匹配）
    if keyword:
        query = query.filter(Document.title.contains(keyword))

    # 分页排序（按ID升序，旧文档在前）
    pagination = query.order_by(Document.id.asc()).paginate(
        page=page, per_page=page_size, error_out=False
    )

    items = [doc.to_dict() for doc in pagination.items]

    return success_response(data=paginated_response(
        items=items,
        total=pagination.total,
        page=page,
        page_size=page_size,
    ))


@doc_bp.route("/topics", methods=["GET"])
@login_required
def list_topics():
    """
    获取预定义的主题分类列表
    """
    topics = [{"value": t, "label": t} for t in TOPIC_OPTIONS]
    return success_response(data=topics)


@doc_bp.route("/<int:doc_id>", methods=["GET"])
@login_required
def get_document(doc_id):
    """
    获取文档详情（包含完整文本内容）
    参数：doc_id 文档ID
    """
    doc = Document.query.get(doc_id)
    if doc is None or doc.status != 1:
        return error_response("文档不存在", 404)

    return success_response(data=doc.to_dict(include_content=True))


@doc_bp.route("", methods=["POST"])
@login_required
@admin_required
def upload_document():
    """
    上传文档接口（multipart/form-data格式）
    表单字段：file(文件)、title(可选标题)
    上传流程：保存文件 → 解析文本 → 分块向量化 → 存入Chroma → 记录MySQL
    """
    if "file" not in request.files:
        return error_response("请选择要上传的文件", 400)

    file = request.files["file"]
    if file.filename == "" or file.filename is None:
        return error_response("请选择要上传的文件", 400)

    # 校验文件类型
    if not allowed_file(file.filename):
        return error_response("不支持的文件类型，仅支持 pdf/docx/txt/md", 400)

    # 生成安全的文件名并保存（保留中文等非ASCII字符，仅去除路径分隔符）
    file_type = get_file_extension(file.filename)
    raw_name = (file.filename or "unknown").replace("/", "_").replace("\\", "_").replace("\x00", "")
    # 保留原始文件名用于数据库和向量库元数据，secure_filename 用于磁盘存储
    original_name = raw_name.strip()
    safe_disk_name = secure_filename(raw_name) if raw_name else "unknown"
    if not safe_disk_name or safe_disk_name == raw_name or len(safe_disk_name) < 3:
        # secure_filename 可能因全中文而返回空或仅扩展名，此时保留原始名
        safe_disk_name = raw_name
    saved_name = f"{uuid.uuid4().hex}_{safe_disk_name}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    file_path = os.path.join(upload_dir, saved_name)
    file.save(file_path)

    # 获取文件大小
    file_size = os.path.getsize(file_path)

    # 解析文档内容
    from ..services.document_service import DocumentService
    try:
        parse_result = DocumentService.parse(file_path, file_type)
        content = parse_result["content"]
        langchain_docs = parse_result["documents"]
    except Exception as e:
        # 解析失败时删除已保存的文件
        if os.path.exists(file_path):
            os.remove(file_path)
        return error_response(f"文档解析失败: {str(e)}", 500)

    # 确定文档标题（优先使用用户指定的标题，否则使用文件名）
    title = request.form.get("title", "").strip()
    if not title:
        title = original_name.rsplit(".", 1)[0] if "." in original_name else original_name

    # 主题分类
    topic = request.form.get("topic", "").strip()
    if topic and topic not in TOPIC_OPTIONS:
        topic = None

    # 创建文档记录
    doc = Document(
        title=title,
        content=content,
        file_name=original_name,
        file_type=file_type,
        file_size=file_size,
        topic=topic if topic else None,
        uploader_id=g.current_user.id,
    )
    db.session.add(doc)
    db.session.flush()  # 获取新文档的ID

    # RAG入库：分块 → 向量化 → 存入Chroma
    from ..services.rag_service import RAGService
    print(f"[上传诊断] 开始RAG入库...")
    rag_service = RAGService(current_app.config)
    print(f"[上传诊断] 文档解析后共{len(langchain_docs)}个LangChain Document")
    chunks = rag_service.split_documents(langchain_docs)
    print(f"[上传诊断] 分割为{len(chunks)}个文本块")
    chunk_count, vector_ids = rag_service.add_to_vector_store(chunks, doc.id, original_name, topic)
    print(f"[上传诊断] 成功添加{chunk_count}个向量到Chroma，向量ID示例: {vector_ids[:3] if vector_ids else '无'}")

    # 验证向量库状态
    stats = rag_service.get_vector_store_stats()
    print(f"[上传诊断] 当前向量库总数: {stats}")

    # 记录分块信息到MySQL
    doc.chunk_count = chunk_count
    for i, chunk in enumerate(chunks):
        chunk_record = DocumentChunk(
            document_id=doc.id,
            chunk_index=i,
            content=chunk.page_content,
            vector_id=vector_ids[i] if i < len(vector_ids) else "",
        )
        db.session.add(chunk_record)

    # 记录操作日志
    log = SystemLog(
        user_id=g.current_user.id,
        action="DOC_UPLOAD",
        description=f"上传文档: {original_name}，共{chunk_count}个文本块",
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    return success_response(
        data=doc.to_dict(),
        message=f"文档上传成功，已处理为{chunk_count}个文本块",
        code=201,
    )


@doc_bp.route("/<int:doc_id>", methods=["PUT"])
@login_required
def update_document(doc_id):
    """
    更新文档信息（标题和主题分类）
    请求体：{"title": "新标题", "topic": "财务管理"}
    """
    doc = Document.query.get(doc_id)
    if doc is None or doc.status != 1:
        return error_response("文档不存在", 404)

    # 只能由上传者或管理员修改
    if not g.current_user.is_admin() and doc.uploader_id != g.current_user.id:
        return error_response("无权限修改该文档", 403)

    data = request.get_json()
    if not data:
        return error_response("请提供要更新的字段", 400)

    updated = False
    if "title" in data and data["title"].strip():
        doc.title = data["title"].strip()
        updated = True
    if "topic" in data:
        topic_val = data["topic"].strip() if data["topic"] else None
        if topic_val and topic_val not in TOPIC_OPTIONS:
            return error_response(f"无效的主题分类: {topic_val}", 400)
        doc.topic = topic_val
        updated = True

    if updated:
        doc.updated_at = datetime.now()
        db.session.commit()

    return success_response(data=doc.to_dict(), message="更新成功")


@doc_bp.route("/<int:doc_id>", methods=["DELETE"])
@login_required
def delete_document(doc_id):
    """
    删除文档（软删除 + 清理Chroma向量）
    """
    doc = Document.query.get(doc_id)
    if doc is None or doc.status != 1:
        return error_response("文档不存在", 404)

    # 只能由上传者或管理员删除
    if not g.current_user.is_admin() and doc.uploader_id != g.current_user.id:
        return error_response("无权限删除该文档", 403)

    # 从Chroma向量库中删除该文档的所有向量
    from ..services.rag_service import RAGService
    rag_service = RAGService(current_app.config)
    rag_service.delete_from_vector_store(doc.id)

    # MySQL中软删除文档
    doc.status = 0
    doc.updated_at = datetime.now()

    # 记录日志
    log = SystemLog(
        user_id=g.current_user.id,
        action="DOC_DELETE",
        description=f"删除文档: {doc.file_name}",
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    return success_response(message="文档删除成功")
