"""
员工入离职管理系统 - Flask 应用入口
前后端一体化部署
"""

import logging
import os
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS

# ─── 路径配置（基于本文件绝对路径）─────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# ─── 日志配置 ───────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "employee-lifecycle-management-secret-key"
    CORS(app, supports_credentials=True)

    # ─── 注册 API 蓝图 ──────────────────────────────
    from api import api_bp
    app.register_blueprint(api_bp)

    # ─── 登录接口 ────────────────────────────────────
    @app.route("/api/auth/login", methods=["POST"])
    def api_auth_login():
        """用户登录 - 供前端 login.html 调用"""
        data = request.get_json() or {}
        username = data.get("username", "")
        password = data.get("password", "")

        if username == "admin" and password == "123456":
            import time
            return jsonify({
                "code": 0,
                "data": {
                    "token": "mock-token-" + str(time.time()),
                    "userName": "管理员",
                    "role": "HR_ADMIN",
                },
                "message": "登录成功",
            })
        else:
            return jsonify({
                "code": 1001,
                "data": None,
                "message": "账号或密码错误，请重试",
            })

    # ─── 前端页面路由（使用绝对路径）─────────────────

    @app.route("/")
    @app.route("/index.html")
    def index_page():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/login.html")
    def login_page():
        return send_from_directory(FRONTEND_DIR, "login.html")

    @app.route("/styles.css")
    def styles():
        return send_from_directory(FRONTEND_DIR, "styles.css")

    @app.route("/app.js")
    def app_js():
        return send_from_directory(FRONTEND_DIR, "app.js")

    # ─── 健康检查 ────────────────────────────────────
    @app.route("/health")
    def health_check():
        import time
        return {
            "status": "ok",
            "timestamp": int(time.time() * 1000),
            "version": "1.0.0",
            "service": "employee-lifecycle-management",
        }

    # ─── 全局错误处理 ────────────────────────────────
    @app.errorhandler(404)
    def not_found(err):
        return jsonify({
            "success": False,
            "error": {"code": "NOT_FOUND", "message": "接口不存在"}
        }), 404

    @app.errorhandler(500)
    def server_error(err):
        return jsonify({
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "服务器内部错误"}
        }), 500

    # ─── 请求日志中间件 ──────────────────────────────
    @app.before_request
    def log_request():
        if not request.path.startswith("/styles.css") and not request.path.startswith("/app.js"):
            logger.info(f"{request.method} {request.path}")

    logger.info(f"Flask 应用初始化完成 (frontend: {FRONTEND_DIR})")
    return app


# ─── 创建 app 实例 ───────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
