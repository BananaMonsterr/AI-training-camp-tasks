# 员工入离职管理系统 - 自动化测试脚本

## 概述

本目录包含员工入离职管理系统（Employee Onboarding & Resignation Management System）的功能自动化测试脚本。

## 技术栈

- **pytest** 7.0+ - 测试框架
- **requests** 2.28+ - HTTP客户端
- **monkeypatch**（pytest内置）- Mock机制

## 测试架构

```
workspace/code/tests/
├── conftest.py          # 测试夹具、Mock后端（状态机）、API客户端
├── test_onboard.py      # 入职管理功能测试
├── test_resign.py       # 离职管理功能测试
├── test_exception.py    # 异常与边界场景测试
├── requirements.txt     # Python依赖
└── README.md            # 运行说明（本文件）
```

### 设计说明

1. **Mock后端**：`conftest.py` 中的 `MockAPI` 类实现了完整的业务状态机，模拟所有API端点行为，无需真实后端即可运行测试。
2. **API客户端**：`api_client` fixture 通过 `monkeypatch` 注入 mock 的 `requests.post` 和 `requests.get`，测试用例使用标准的 `requests` 库调用。
3. **状态隔离**：每个测试用例执行前自动重置 mock 数据，确保用例间互不干扰。
4. **权限模拟**：内置 admin/hr/dept_manager/leader/employee/viewer 六种角色及对应权限控制。

### API 端点一览

| 模块 | 方法 | 端点 | 说明 |
|------|------|------|------|
| 认证 | POST | /api/auth/login | 用户登录 |
| 入职 | POST | /api/onboard/initiate | 发起入职申请 |
| 入职 | POST | /api/onboard/hr-review | HR初审通过 |
| 入职 | POST | /api/onboard/hr-reject | HR驳回 |
| 入职 | POST | /api/onboard/dept-approve | 部门审批通过 |
| 入职 | POST | /api/onboard/dept-reject | 部门驳回 |
| 入职 | POST | /api/onboard/leader-approve | 领导审批通过 |
| 入职 | POST | /api/onboard/leader-reject | 领导驳回 |
| 入职 | GET | /api/onboard/status/{id} | 查询入职状态 |
| 入职 | POST | /api/onboard/notify | 发送入职通知 |
| 离职 | POST | /api/resign/apply | 提交离职申请 |
| 离职 | POST | /api/resign/handover | 工作交接 |
| 离职 | POST | /api/resign/approve | 审批通过 |
| 离职 | POST | /api/resign/reject | 审批驳回 |
| 离职 | POST | /api/resign/return-assets | 归还资产 |
| 离职 | GET | /api/resign/status/{id} | 查询离职状态 |

### 入职状态机

```
DRAFT → PENDING_HR_REVIEW → PENDING_DEPT_APPROVAL → PENDING_LEADER_APPROVAL → APPROVED
                                        ↓                          ↓
                                     REJECTED                   REJECTED
```

### 离职状态机

```
DRAFT → PENDING_HANDOVER → PENDING_APPROVAL → PENDING_RETURN_ASSETS → COMPLETED
                                                ↓
                                             REJECTED
```

## 环境要求

- Python 3.8+
- pip

## 快速开始

### 1. 安装依赖

```bash
cd workspace/code/tests
pip install -r requirements.txt
```

### 2. 运行所有测试

```bash
# 方式一：运行全部测试
python -m pytest -v

# 方式二：带详细输出
python -m pytest -v --tb=short

# 方式三：生成HTML报告（需安装pytest-html）
python -m pytest -v --html=report.html --self-contained-html
```

### 3. 运行指定测试文件

```bash
# 入职流程
python -m pytest test_onboard.py -v

# 离职流程
python -m pytest test_resign.py -v

# 异常场景
python -m pytest test_exception.py -v
```

### 4. 运行指定测试类或用例

```bash
# 指定测试类
python -m pytest test_onboard.py::TestOnboardApprovalFlow -v

# 指定测试用例
python -m pytest test_onboard.py::TestOnboardApprovalFlow::test_full_approval_flow -v
```

### 5. 生成覆盖率报告

```bash
python -m pytest --cov=. --cov-report=html -v
```

## 连接到真实API

默认使用Mock模式运行测试。如需连接真实后端API，使用以下命令：

```bash
# 连接真实API（需启动后端服务）
python -m pytest --real-api --base-url=http://localhost:8080/api -v
```

## 测试用例清单

### 入职模块（20个用例）

| 用例ID | 类名 | 方法名 | 描述 |
|--------|------|--------|------|
| TC-ONB-001 | TestOnboardInitiate | test_initiate_onboard_success | 正常发起入职申请 |
| TC-ONB-002 | TestOnboardInitiate | test_initiate_missing_required_field | 缺少必填字段 |
| TC-ONB-003 | TestOnboardInitiate | test_initiate_missing_position | 缺少position字段 |
| TC-ONB-004 | TestOnboardInitiate | test_initiate_duplicate_candidate | 重复候选人提交 |
| TC-ONB-005 | TestOnboardInitiate | test_initiate_unauthorized | 无效token发起 |
| TC-ONB-006 | TestOnboardApprovalFlow | test_full_approval_flow | 完整审批流程 |
| TC-ONB-007 | TestOnboardApprovalFlow | test_hr_reject_flow | HR驳回流程 |
| TC-ONB-008 | TestOnboardApprovalFlow | test_dept_reject_flow | 部门驳回流程 |
| TC-ONB-009 | TestOnboardApprovalFlow | test_leader_reject_flow | 领导驳回流程 |
| TC-ONB-010 | TestOnboardApprovalFlow | test_invalid_status_transition_skip_step | 跳过步骤流转 |
| TC-ONB-011 | TestOnboardApprovalFlow | test_approve_completed_onboard | 已完成再次审批 |
| TC-ONB-012 | TestOnboardNotification | test_notify_after_approval | 审批后发送通知 |
| TC-ONB-013 | TestOnboardNotification | test_notify_without_approval | 未审批发送通知 |
| TC-ONB-014 | TestOnboardStatusQuery | test_query_existing_onboard | 查询已存在申请 |
| TC-ONB-015 | TestOnboardStatusQuery | test_query_non_existent_onboard | 查询不存在申请 |
| TC-ONB-016 | TestOnboardStatusQuery | test_query_onboard_status_permission | HR角色查询 |
| TC-ONB-017 | TestOnboardEdgeCases | test_initiate_with_empty_payload | 空JSON体 |
| TC-ONB-018 | TestOnboardEdgeCases | test_initiate_without_auth_header | 无认证头 |
| TC-ONB-019 | TestOnboardEdgeCases | test_onboard_id_format | ID格式验证 |
| TC-ONB-020 | TestOnboardEdgeCases | test_multiple_onboard_requests | 多次发起不同候选人 |

### 离职模块（18个用例）

| 用例ID | 类名 | 方法名 | 描述 |
|--------|------|--------|------|
| TC-RSG-001 | TestResignApply | test_apply_resign_success | 正常提交离职申请 |
| TC-RSG-002 | TestResignApply | test_apply_resign_missing_reason | 缺少离职原因 |
| TC-RSG-003 | TestResignApply | test_apply_resign_duplicate | 重复提交离职 |
| TC-RSG-004 | TestResignApply | test_apply_resign_empty_payload | 空数据提交 |
| TC-RSG-005 | TestResignFullFlow | test_full_resign_flow | 完整离职流程 |
| TC-RSG-006 | TestResignFullFlow | test_resign_rejected_flow | 离职驳回流程 |
| TC-RSG-007 | TestResignFullFlow | test_resign_approve_without_handover | 跳过交接审批 |
| TC-RSG-008 | TestResignFullFlow | test_return_assets_without_approval | 跳过审批归还 |
| TC-RSG-009 | TestResignHandover | test_handover_empty_items | 空交接项 |
| TC-RSG-010 | TestResignHandover | test_handover_wrong_resign_id | 错误离职ID |
| TC-RSG-011 | TestResignReturnAssets | test_return_assets_success | 正常归还资产 |
| TC-RSG-012 | TestResignReturnAssets | test_return_assets_empty_list | 空资产列表 |
| TC-RSG-013 | TestResignReturnAssets | test_return_assets_no_resign_id | 缺少离职ID |
| TC-RSG-014 | TestResignStatusQuery | test_query_resign_status | 查询离职状态 |
| TC-RSG-015 | TestResignStatusQuery | test_query_non_existent_resign | 查询不存在 |
| TC-RSG-016 | TestResignStatusQuery | test_query_completed_resign | 查询已完成 |
| TC-RSG-017 | TestResignEdgeCases | test_resign_without_auth | 无认证提交 |
| TC-RSG-018 | TestResignEdgeCases | test_multiple_resign_after_completed | 完成后再次提交 |

### 异常模块（25个用例）

| 用例ID | 类名 | 方法名 | 描述 |
|--------|------|--------|------|
| TC-EXC-001 | TestInvalidStatusTransition | test_onboard_skip_hr_directly_to_leader | 跳过HR初审 |
| TC-EXC-002 | TestInvalidStatusTransition | test_onboard_skip_dept_directly_to_leader | 跳过部门审批 |
| TC-EXC-003 | TestInvalidStatusTransition | test_onboard_reverse_flow_after_approval | 审批后回退 |
| TC-EXC-004 | TestInvalidStatusTransition | test_resign_skip_handover | 跳过工作交接 |
| TC-EXC-005 | TestInvalidStatusTransition | test_resign_skip_approval_return_assets | 跳过审批归还 |
| TC-EXC-006 | TestInvalidStatusTransition | test_resign_approve_after_completed | 完成后再次审批 |
| TC-EXC-007 | TestDuplicateSubmission | test_duplicate_onboard_same_name | 重复候选人入职 |
| TC-EXC-008 | TestDuplicateSubmission | test_duplicate_onboard_after_rejected | 驳回后重新提交 |
| TC-EXC-009 | TestDuplicateSubmission | test_duplicate_resign_same_employee | 重复离职申请 |
| TC-EXC-010 | TestUnauthorizedAccess | test_access_without_token | 未登录访问 |
| TC-EXC-011 | TestUnauthorizedAccess | test_employee_approve_onboard | 员工审批入职 |
| TC-EXC-012 | TestUnauthorizedAccess | test_hr_approve_dept_step | HR越权部门审批 |
| TC-EXC-013 | TestUnauthorizedAccess | test_viewer_resign_approve | 只读用户审批离职 |
| TC-EXC-014 | TestUnauthorizedAccess | test_employee_approve_own_resign | 员工自审批 |
| TC-EXC-015 | TestParameterValidation | test_empty_json_body | 空JSON体 |
| TC-EXC-016 | TestParameterValidation | test_invalid_data_types | 类型错误 |
| TC-EXC-017 | TestParameterValidation | test_very_long_string_fields | 超长字符串 |
| TC-EXC-018 | TestParameterValidation | test_sql_injection_attempt | SQL注入 |
| TC-EXC-019 | TestParameterValidation | test_xss_attempt | XSS注入 |
| TC-EXC-020 | TestParameterValidation | test_negative_numbers | 特殊数值 |
| TC-EXC-021 | TestConcurrencyAndIdempotency | test_same_operation_twice_idempotent | 重复操作幂等性 |
| TC-EXC-022 | TestConcurrencyAndIdempotency | test_query_during_process | 流程中反复查询 |
| TC-EXC-023 | TestSystemRobustness | test_missing_resign_id_in_path | 路径参数缺失 |
| TC-EXC-024 | TestSystemRobustness | test_invalid_http_method | 错误HTTP方法 |
| TC-EXC-025 | TestSystemRobustness | test_unauthorized_role_for_onboard_notify | 角色发送通知 |

## 测试数据

系统预设以下测试用户：

| 用户名 | 密码 | 角色 | Token |
|--------|------|------|-------|
| admin | 123456 | 系统管理员 | token_admin_001 |
| hr_user | 123456 | HR经理 | token_hr_001 |
| dept_manager | 123456 | 部门经理 | token_dept_001 |
| leader | 123456 | 领导 | token_leader_001 |
| employee | 123456 | 普通员工 | token_emp_001 |
| viewer | 123456 | 只读用户 | token_viewer_001 |

## 常见问题

**Q: 运行测试时提示模块缺失？**
A: 请先执行 `pip install -r requirements.txt`

**Q: 如何添加新的测试用例？**
A: 在对应的测试文件中添加新的测试方法，方法名以 `test_` 开头即可被pytest自动发现。

**Q: MockAPI无法满足复杂业务场景？**
A: 可以通过修改 `conftest.py` 中的 `MockAPI` 类扩展新的API端点或状态流转规则。
