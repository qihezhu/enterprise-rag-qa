"""
健康检查端点
聚合所有依赖的状态：MySQL、Redis、Chroma、企微 Token、Ollama
"""
from flask import Blueprint, current_app
from ..extensions import db, redis_client
from ..utils.helpers import success_response

health_bp = Blueprint("health", __name__, url_prefix="/api/health")


@health_bp.route("/", methods=["GET"])
def health_check():
    """全量健康检查"""
    return success_response({
        "status": "ok",
        "checks": {
            "mysql": _check_mysql(),
            "redis": _check_redis(),
            "chroma": _check_chroma(),
            "wecom_token": _check_wecom_token(),
            "ollama": _check_ollama(),
        },
    })


@health_bp.route("/ready", methods=["GET"])
def readiness():
    """就绪探针（K8s readiness probe）"""
    checks = {
        "mysql": _check_mysql(),
        "redis": _check_redis(),
        "chroma": _check_chroma(),
    }
    all_ok = all(c["status"] in ("ok", "warning") for c in checks.values())
    return {"ready": all_ok, "checks": checks}, 200 if all_ok else 503


@health_bp.route("/live", methods=["GET"])
def liveness():
    """存活探针（K8s liveness probe）"""
    return {"alive": True}


def _check_mysql():
    try:
        db.session.execute(db.text("SELECT 1"))
        return {"status": "ok", "message": "MySQL 连接正常"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_redis():
    try:
        if redis_client and redis_client.ping():
            return {"status": "ok", "message": "Redis 连接正常"}
        return {"status": "warning", "message": "Redis 不可用，使用内存缓存降级"}
    except Exception as e:
        return {"status": "warning", "message": f"Redis 不可用: {e}"}


def _check_chroma():
    try:
        from ..services.vector_store_service import VectorStoreService
        config = current_app.config
        store = VectorStoreService(
            persist_directory=config["CHROMA_PERSIST_DIR"],
            embedding_function=None,
            collection_name=config["CHROMA_COLLECTION_NAME"],
        )
        stats = store.get_collection_stats()
        return {"status": "ok", "message": f"Chroma 正常，共 {stats.get('count', 0)} 个向量"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_wecom_token():
    try:
        if not current_app.config.get("WECOM_CORP_ID") or not current_app.config.get("WECOM_SECRET"):
            return {"status": "warning", "message": "企微凭证未配置"}
        from ..clients.wecom_client import wecom_client
        token = wecom_client.get_access_token()
        if token:
            return {"status": "ok", "message": "企微 Token 有效"}
        return {"status": "error", "message": "Token 获取失败"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_ollama():
    try:
        import requests
        base_url = current_app.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            names = [m.get("name", "") for m in models]
            return {"status": "ok", "message": f"Ollama 正常，已加载: {', '.join(names[:5])}"}
        return {"status": "error", "message": f"Ollama 响应异常: {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
