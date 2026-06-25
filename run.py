"""
启动入口脚本
在项目根目录下运行: python run.py
"""
from server.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
