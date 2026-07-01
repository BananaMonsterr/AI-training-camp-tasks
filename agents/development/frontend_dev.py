"""
前端开发 Agent - 张铃

所属Agent角色: 开发Agent
岗位角色: 前端开发
负责研发环节: 代码开发-前端页面&联调
核心职责: 前端页面开发（HR管理台/员工自助页/审批页）、表单交互与校验、前后端联调、部署脚本
核心交付物: 前端页面代码、部署脚本、联调测试记录
边界: 不参与后端逻辑开发，不参与数据库设计，不参与测试分析

参考: Excel「Agent任务分配总表」R7
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.base_agent import AgentConfig, create_agent, create_task, run_agent


ROLE = "前端开发工程师（张铃）"

GOAL = (
    "根据需求完成员工入离职管理系统前端页面开发、表单交互与校验、前后端联调说明和部署脚本，"
    "确保前端体验完整、交互流畅、可独立运行。"
)

BACKSTORY = """# 身份
你是一位资深前端开发工程师（张铃），在开发Agent团队中负责代码开发-前端页面&联调。
你的核心工作是将设计转化为可运行的交互页面，并完成后端API联调。

# Prompt 设计方向（核心职责）
1. 前端页面开发：HR管理台/员工自助页/审批页
2. 表单交互与校验：必填校验、格式校验、错误提示
3. 前后端联调：接口字段映射、请求方式、mock数据
4. 部署脚本：提供可执行的部署脚本

# 工作方法论
1. **澄清需求**：明确需求边界，拆分页面、组件、交互
2. **页面开发**：独立登录页、HR管理台、员工自助页、审批页
3. **表单校验**：必填项、手机号/邮箱格式、审批意见等
4. **mock数据**：模拟后端API，标注真实接口替换位置
5. **部署脚本**：提供PowerShell部署脚本，UTF-8防乱码

# 核心交付物
1. 前端页面代码：login.html、index.html、styles.css、app.js
2. 部署脚本：Windows PowerShell可执行
3. 联调测试记录：接口假设、联调步骤、验证结果

# 边界说明（NEVER 清单）
- 不参与后端逻辑开发（由后端龚茂林负责）
- 不参与数据库设计（由架构师李兆贵负责）
- 不参与测试分析（由测试分析师张桦彬负责）

**语言要求**：所有输出使用中文。"""

CONFIG = AgentConfig(
    role=ROLE,
    goal=GOAL,
    backstory=BACKSTORY,
    max_iter=50,
)


def build_agent():
    return create_agent(CONFIG)


def build_tasks(agent):
    task = create_task(
        description="""\
请完成员工入离职管理系统前端开发交付。

## 需要完成的工作
1. **独立登录页 login.html**：
   - 独立登录页面，不含后台管理内容
   - 账号、密码输入、登录按钮、错误提示
   - 登录成功后跳转到index.html

2. **主页 index.html（HR管理台）**：
   - 登录后的主页面，含HR管理台、员工自助页、审批页入口
   - 包含统计卡片、待办事项、快捷操作

3. **表单交互与校验**：
   - 入职表单：姓名、身份证、手机、邮箱、部门、岗位、入职日期
   - 离职表单：离职原因、最后工作日、交接人
   - 校验规则：必填、身份证18位、手机11位、邮箱格式

4. **前后端联调**：
   - 使用mock数据模拟后端API
   - 标注真实接口替换位置
   - 记录联调测试记录

5. **部署脚本 deploy.ps1**：
   - 包含UTF-8编码设置
   - 静态资源检查、输出目录检查

## 输出要求
- 使用FileWriterTool将所有文件保存到 workspace/code/frontend/""",
        expected_output="""\
前端交付物（workspace/code/frontend/）：
1. login.html - 独立登录页
2. index.html - HR管理台主页
3. styles.css - 样式文件
4. app.js - 交互逻辑
5. deploy.ps1 - 部署脚本
6. integration-test-record.md - 联调记录""",
        agent=agent,
    )
    return [task]


def run():
    agent = build_agent()
    tasks = build_tasks(agent)
    return run_agent([agent], tasks)


if __name__ == "__main__":
    result = run()
    print(result)
