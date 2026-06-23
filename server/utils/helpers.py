"""
工具函数模块
提供MD5加密、统一响应格式、文件类型校验等辅助功能
"""
import hashlib


def clean_tool_inputs(data):
    """递归去除百炼Tool输入中字符串值的多余引号"""
    if isinstance(data, dict):
        return {k: clean_tool_inputs(v) for k, v in data.items()}
    if isinstance(data, list):
        return [clean_tool_inputs(v) for v in data]
    if isinstance(data, str):
        return data.strip().strip('"\'')
    return data
from flask import jsonify

# 允许上传的文件扩展名
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

# 文档主题分类选项
TOPIC_OPTIONS = ["财务管理", "行政管理", "技术管理", "IT运维", "数据管理", "开发规范", "组织管理", "人力资源", "安全管理"]


def md5_encrypt(raw_string):
    """
    对字符串进行MD5加密
    参数：
        raw_string: 原始字符串
    返回：
        32位MD5十六进制密文
    """
    return hashlib.md5(raw_string.encode("utf-8")).hexdigest()


def success_response(data=None, message="操作成功", code=200):
    """
    构造成功响应
    参数：
        data: 返回的数据
        message: 提示消息
        code: HTTP状态码
    返回：
        Flask JSON响应对象
    """
    return jsonify({
        "code": code,
        "message": message,
        "data": data,
    }), code


def error_response(message="操作失败", code=400, data=None):
    """
    构造错误响应
    参数：
        message: 错误提示消息
        code: HTTP状态码
        data: 附加错误数据
    返回：
        Flask JSON响应对象
    """
    return jsonify({
        "code": code,
        "message": message,
        "data": data,
    }), code


def paginated_response(items, total, page, page_size):
    """
    构造分页响应数据
    参数：
        items: 当前页数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页条数
    返回：
        分页数据字典
    """
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
    }


def allowed_file(filename):
    """
    检查上传文件名是否为允许的格式
    参数：
        filename: 上传的文件名
    返回：
        bool: 是否允许
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename):
    """
    获取文件扩展名（不含点号）
    参数：
        filename: 文件名
    返回：
        小写扩展名字符串，如 'pdf'
    """
    if "." in filename:
        return filename.rsplit(".", 1)[1].lower()
    return ""
