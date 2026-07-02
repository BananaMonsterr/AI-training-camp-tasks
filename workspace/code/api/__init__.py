"""API蓝图模块"""
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# 导入各模块的路由（触发装饰器注册）
from . import employee_api      # noqa: E402, F401
from . import onboarding_api    # noqa: E402, F401
from . import offboarding_api   # noqa: E402, F401
from . import approval_api      # noqa: E402, F401
from . import notification_api  # noqa: E402, F401
from . import hr_api            # noqa: E402, F401
