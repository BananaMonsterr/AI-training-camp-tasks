# 员工入离职管理系统 - 多Agent协作框架

## 项目概述

本项目是AI训练营小组作业，通过多Agent协同方式解决员工入离职管理系统的研发全流程。
包含 **产品、开发、测试** 三个核心Agent角色组，共 **9个角色**，覆盖完整研发闭环。

## 项目结构

```
AI-training-camp-tasks/
+-- agents/                        # Agent代码（核心）
|   +-- base_agent.py              #   基础Agent构建器（遵循 m1l2_agent.py 风格）
|   +-- orchestrator.py            #   编排器 - 流水线调度
|   +-- __init__.py
|   +-- product/                   #   产品Agent组（3人）
|   |   +-- requirement_analyst.py #     徐意 - 需求分析（主责）
|   |   +-- business_designer.py   #     张梦晴 - 业务流程设计
|   |   +-- solution_designer.py   #     刘紫璇 - 方案设计/PRD
|   +-- development/               #   开发Agent组（3人）
|   |   +-- architect.py           #     李兆贵 - 系统分析/架构（补充完成）
|   |   +-- backend_dev.py         #     龚茂林 - 后端全栈开发
|   |   +-- frontend_dev.py        #     张铃 - 前端开发
|   +-- testing/                   #   测试Agent组（3人）
|       +-- test_analyst.py        #     张桦彬 - 测试分析
|       +-- test_executor.py       #     韩均楠 - 功能测试执行
|       +-- acceptance_tester.py   #     测试工程师C - 验收测试（补充完成）
+-- llm/                          # LLM配置（保留韩均楠原有 CrewAI 集成）
+-- tools/                        # 工具模块
+-- shared/                       # 共享模块
+-- skills/                       # 技能文件
+-- workspace/                    # 工作区
+-- main.py                       # 统一入口点
+-- requirements.txt
+-- .env.example
```

## 9人分工对照表（Excel）

| 序号 | Agent角色 | 岗位角色 | 负责人 | 研发环节 | 状态 |
|------|----------|---------|-------|---------|------|
| 1 | 产品Agent | 产品经理A | 徐意 | 需求分析(主责) | 已实现 |
| 2 | 产品Agent | 产品经理B | 张梦晴 | 业务流程设计 | 已实现 |
| 3 | 产品Agent | 产品经理C | 刘紫璇 | 方案设计/PRD | 已实现 |
| 4 | 开发Agent | 架构师/技术负责人 | 李兆贵 | 系统分析(主责) | **补充完成** |
| 5 | 开发Agent | 后端开发(全栈) | 龚茂林 | 后端全栈开发 | 已实现 |
| 6 | 开发Agent | 前端开发 | 张铃 | 前端&联调 | 已实现 |
| 7 | 测试Agent | 测试工程师A | 张桦彬 | 测试分析 | 已实现 |
| 8 | 测试Agent | 测试工程师B | 韩均楠 | 功能测试执行 | 已实现 |
| 9 | 测试Agent | 测试工程师C | - | 验收测试&报告 | **补充完成** |

## 流水线阶段

```
需求分析 -> 方案设计 -> 系统分析 -> 代码开发 -> 测试分析 -> 测试验收
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入对应的 API Key
```

### 3. 运行模式

**查看帮助：**
```bash
python main.py
```

**运行单Agent：**
```bash
python main.py --agent architect          # 架构师李兆贵
python main.py --agent acceptance_tester  # 验收测试工程师C
```

**运行单阶段：**
```bash
python main.py --stage 需求分析
python main.py --stage 测试验收
```

**运行完整流水线：**
```bash
python main.py --pipeline
```

**QA测试模式（韩均楠原有功能）：**
```bash
python main.py "请测试入职管理模块"
```

## 代码风格参考

遵循 [m1l2_agent.py](https://github.com/kid0317/crewai_mas_demo/blob/main/m1l2/m1l2_agent.py) 的 CrewAI 风格：
- Agent：Role / Goal / Backstory 三要素人设工程
- Task：description / expected_output 任务定义
- Crew：Agent + Task 的编排执行

## 角色边界说明

各角色的 **边界定义（NEVER清单）** 严格遵循 Excel「Agent任务分配总表」：
- 产品Agent：不参与技术方案和代码实现
- 开发Agent：不参与需求分析和测试执行
- 测试Agent：不参与代码开发和缺陷修复

详细边界见各Agent文件的 `BACKSTORY` 中的 `边界说明（NEVER 清单）` 章节。

## 团队个人贡献

| 成员 | 负责模块 | 说明 |
|------|---------|------|
| 徐意 | 需求分析(主责) | agents/product/requirement_analyst.py |
| 张梦晴 | 业务流程设计 | agents/product/business_designer.py |
| 刘紫璇 | 方案设计/PRD | agents/product/solution_designer.py |
| 李兆贵 | 系统分析/架构 | agents/development/architect.py（补充完成） |
| 龚茂林 | 后端全栈开发 | agents/development/backend_dev.py |
| 张铃 | 前端开发 | agents/development/frontend_dev.py |
| 张桦彬 | 测试分析 | agents/testing/test_analyst.py |
| 韩均楠 | 功能测试执行 | agents/testing/test_executor.py |
| 测试工程师C | 验收测试&报告 | agents/testing/acceptance_tester.py（补充完成） |
