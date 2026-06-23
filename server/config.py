"""
Flask应用配置文件
包含数据库连接、Ollama服务、Chroma向量库、JWT等所有配置项
"""
import os


class Config:
    """应用配置类"""

    # ==================== MySQL数据库配置 ====================
    # 请根据实际情况修改用户名和密码
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:526112@127.0.0.1:3306/db_enterprise_ge"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # 设为True可打印SQL语句，调试时使用

    # ==================== JWT认证配置 ====================
    SECRET_KEY = os.environ.get("SECRET_KEY", "enterprise-rag-secret-key-2026")
    JWT_EXPIRATION_HOURS = 24  # Token有效期（小时）

    # ==================== Ollama服务配置 ====================
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_MODEL_NAME = "qwen3:8b"              # 对话生成大模型
    EMBEDDING_MODEL_NAME = "qwen3-embedding:4b"  # 文本嵌入模型

    # ==================== Chroma向量数据库配置 ====================
    # 获取项目根目录（server的上级目录）
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db")
    CHROMA_COLLECTION_NAME = "knowledge_base"

    # ==================== 文本分割参数 ====================
    CHUNK_SIZE = 500       # 每个文本块的最大字符数
    CHUNK_OVERLAP = 50     # 相邻文本块的重叠字符数

    # ==================== 检索参数 ====================
    TOP_K_RETRIEVAL = 6    # 每次检索返回的最相关文本块数量

    # ==================== 文件上传配置 ====================
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大上传文件大小 16MB
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

    # ==================== 企业微信配置 ====================
    WECOM_CORP_ID = os.environ.get("WECOM_CORP_ID", "wwd286a2dd91eab108")
    WECOM_AGENT_ID = os.environ.get("WECOM_AGENT_ID", "1000002")
    WECOM_SECRET = os.environ.get("WECOM_SECRET", "eW0LOcKEg9FxPDlVaSwUXm-5sxURFahE2swmMkbiVcU")
    WECOM_CONTACT_SECRET = os.environ.get("WECOM_CONTACT_SECRET", "VRYnBUe6v_0mURKHwL_u9KKHzv5JrWPtLHEmrnQrHCM")
    WECOM_TOKEN = os.environ.get("WECOM_TOKEN", "mZOpY8L8Kd59QjyDBlAPNx5IeM5")                # 回调验签Token
    WECOM_ENCODING_AES_KEY = os.environ.get("WECOM_ENCODING_AES_KEY", "4rlEY2ezFbw11HEFzI6lmWhBzOkO4jkikzd6c2liq35")  # 43位消息加密密钥
    WECOM_API_BASE = "https://qyapi.weixin.qq.com"

    # ==================== Redis 配置 ====================
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # ==================== 千问Agent平台配置 ====================
    QWEN_TOOL_API_KEY = os.environ.get("QWEN_TOOL_API_KEY", "test_api_key")

    # ==================== 百炼 Agent 平台配置 ====================
    DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "sk-ws-H.REXRHXH.K7ml.MEUCIQCCm1sLH1K2HXJKN7yOerVu_QRLZYU3FttezZQWJyRv7gIgXTp74aqApcZaNuBAX99Km_pZH3qvw0aXKY2goeXVRFs")
    BAILIAN_APP_ID = os.environ.get("BAILIAN_APP_ID", "f033c5b653724b769aa5d001461d0e2e")
    BAILIAN_TIMEOUT = int(os.environ.get("BAILIAN_TIMEOUT", "120"))
