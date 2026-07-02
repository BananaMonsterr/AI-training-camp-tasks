# 员工入离职管理系统 - 后端代码

## 项目结构

```
workspace/code/
├── models/               # 数据模型层
│   ├── __init__.py       # 数据库初始化 + 基础Mixin
│   ├── employee.py       # 员工/部门模型
│   ├── onboarding.py     # 入职申请模型
│   ├── offboarding.py    # 离职申请模型
│   ├── approval.py       # 审批节点模型
│   ├── notification.py   # 通知记录模型
│   └── auth.py           # 角色/权限模型
├── engines/              # 引擎层
│   ├── __init__.py
│   ├── state_machine.py  # 状态机引擎（泛化设计）
│   └── approval_engine.py # 审批流引擎（状态机驱动）
├── services/             # 业务服务层
│   ├── __init__.py
│   ├── employee_service.py   # 员工管理服务
│   ├── onboarding_service.py # 入职流程服务
│   ├── offboarding_service.py # 离职流程服务
│   └── hr_service.py        # HR系统对接服务(模拟)
├── notifications/        # 通知模块
│   ├── __init__.py
│   ├── email_service.py      # 邮件发送服务
│   └── notification_service.py # 站内通知服务
├── auth/                 # 权限控制模块
│   ├── __init__.py
│   ├── role_manager.py       # 角色管理器
│   └── permission_checker.py # 权限检查装饰器
├── api/                  # API层（Flask蓝图）
│   ├── __init__.py
│   ├── employee_api.py      # 员工API
│   ├── onboarding_api.py    # 入职API
│   ├── offboarding_api.py   # 离职API
│   ├── approval_api.py      # 审批API
│   ├── notification_api.py  # 通知API
│   └── hr_api.py            # HR对接API
├── tests/                # 单元测试
│   ├── __init__.py
│   ├── conftest.py          # pytest fixtures
│   ├── test_models.py       # 模型测试（26+用例）
│   ├── test_engines.py      # 引擎测试（24+用例）
│   ├── test_services.py     # 服务测试（20+用例）
│   ├── test_notifications.py # 通知测试（17+用例）
│   └── test_auth.py         # 权限测试（16+用例）
├── main.py               # 应用入口
├── requirements.txt      # 依赖
├── pytest.ini            # pytest配置
└── README.md             # 本文件
```

## 核心设计要点

### 1. 状态机引擎
- 泛化设计，支持任意状态转换图
- 入职/离职双状态机
- 支持：条件守卫、前置/后置钩子
- 流程: DRAFT → PENDING_APPROVAL → APPROVED → ONBOARDING_DONE/OFFBOARDING_COMPLETED

### 2. 审批流引擎
- 基于状态机驱动审批流程
- 自动创建审批节点链（部门审批 → HR审批等）
- 支持顺序流转、驳回终止、撤回/取消
- 批量审批支持

### 3. 权限控制
- 基于角色的访问控制（RBAC）
- 5种角色：SUPER_ADMIN / HR_MANAGER / DEPARTMENT_HEAD / TEAM_LEADER / EMPLOYEE
- 细粒度权限检查装饰器

### 4. 通知服务
- 站内通知 + 邮件通知
- 自动触发11种事件通知
- 支持批量已读

### 5. HR系统对接
- 模拟实现，含Mock数据
- 员工同步/部门查询/离职数据同步

## 运行测试

```bash
cd workspace/code
pip install -r requirements.txt
python -m pytest tests/ -v --cov=.
```

## 覆盖率预期

| 模块 | 预期覆盖率 |
|------|-----------|
| models/ | >90% |
| engines/ | >85% |
| services/ | >85% |
| notifications/ | >90% |
| auth/ | >90% |
