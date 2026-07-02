# 员工入离职管理系统 - 前后端联调测试记录

> **文档版本**：v1.0.0  
> **前端开发**：张铃  
> **后端开发**：龚茂林  
> **测试分析师**：张桦彬  
> **联调日期**：2024-01-19  

---

## 目录

1. [联调环境说明](#1-联调环境说明)
2. [接口清单与Mock映射](#2-接口清单与mock映射)
3. [联调步骤与结果](#3-联调步骤与结果)
4. [替换Mock为真实接口操作指南](#4-替换mock为真实接口操作指南)
5. [常见问题与排查](#5-常见问题与排查)

---

## 1. 联调环境说明

| 项目 | 说明 |
|------|------|
| **前端地址** | `http://localhost:8080` （或部署到 IIS/nginx 后的地址） |
| **后端接口基准地址** | `http://localhost:8088/api` |
| **Mock模式** | 前端独立运行，所有数据由 `app.js` 中 `mock*` 系列函数模拟 |
| **联调模式** | 将 `app.js` 中的 Mock 函数替换为真实 `fetch` / `axios` 调用 |
| **字符编码** | 全系统强制 UTF-8 |
| **认证方式** | Token 认证（登录后写入 `localStorage`） |

---

## 2. 接口清单与Mock映射

### 2.1 登录认证

| 项目 | 内容 |
|------|------|
| **接口地址** | `POST /api/auth/login` |
| **Mock函数** | `mockLogin(username, password)` (app.js:43) |
| **请求体** | `{ "username": "admin", "password": "123456" }` |
| **成功响应** | `{ "code": 0, "data": { "token": "...", "userName": "管理员", "role": "HR_ADMIN" }, "message": "登录成功" }` |
| **失败响应** | `{ "code": 1001, "data": null, "message": "账号或密码错误" }` |
| **联调状态** | ⬜ 待联调 |

### 2.2 仪表盘数据

| 项目 | 内容 |
|------|------|
| **接口地址** | `GET /api/dashboard/stats` |
| **Mock函数** | `mockGetDashboardStats()` (app.js:59) |
| **请求头** | `Authorization: Bearer {token}` |
| **成功响应** | `{ "code": 0, "data": { "totalEmployees": 156, "newThisMonth": 8, "leftThisMonth": 3, "pendingApproval": 12 } }` |
| **联调状态** | ⬜ 待联调 |

### 2.3 待办事项

| 项目 | 内容 |
|------|------|
| **接口地址** | `GET /api/dashboard/todos` |
| **Mock函数** | `mockGetTodoList()` (app.js:72) |
| **请求头** | `Authorization: Bearer {token}` |
| **成功响应** | `{ "code": 0, "data": [ { "id": 1, "text": "...", "deadline": "2024-01-20", "urgency": "urgent" } ] }` |
| **联调状态** | ⬜ 待联调 |

### 2.4 最近操作记录

| 项目 | 内容 |
|------|------|
| **接口地址** | `GET /api/dashboard/recent-records` |
| **Mock函数** | `mockGetRecentRecords()` (app.js:88) |
| **请求头** | `Authorization: Bearer {token}` |
| **联调状态** | ⬜ 待联调 |

### 2.5 提交入职申请

| 项目 | 内容 |
|------|------|
| **接口地址** | `POST /api/onboard/submit` |
| **Mock函数** | `mockSubmitOnboard(formData)` (app.js:103) |
| **请求体** | `{ "empName": "张三", "empIdCard": "110101199001011234", "empPhone": "13800138000", "empEmail": "test@company.com", "empDept": "技术部", "empPosition": "前端开发工程师", "empEntryDate": "2024-02-01" }` |
| **成功响应** | `{ "code": 0, "data": { "empCode": "EMP123456" }, "message": "入职申请提交成功" }` |
| **联调状态** | ⬜ 待联调 |

### 2.6 提交离职申请

| 项目 | 内容 |
|------|------|
| **接口地址** | `POST /api/offboard/submit` |
| **Mock函数** | `mockSubmitOffboard(formData)` (app.js:118) |
| **请求体** | `{ "empName": "李四", "empCode": "EMP000001", "lastWorkDay": "2024-02-15", "offboardType": "个人辞职", "offboardReason": "个人发展原因", "handoverPerson": "王五", "handoverContact": "13800138001" }` |
| **联调状态** | ⬜ 待联调 |

### 2.7 审批列表

| 项目 | 内容 |
|------|------|
| **接口地址** | `GET /api/approval/list?status=pending` |
| **Mock函数** | `mockGetApprovalList()` (app.js:133) |
| **请求头** | `Authorization: Bearer {token}` |
| **成功响应** | `{ "code": 0, "data": { "pending": [...], "approved": [...], "rejected": [...] } }` |
| **联调状态** | ⬜ 待联调 |

### 2.8 审批处理

| 项目 | 内容 |
|------|------|
| **接口地址** | `POST /api/approval/process` |
| **Mock函数** | `mockApprovalAction(id, action, comment)` (app.js:149) |
| **请求体** | `{ "id": 1, "action": "approve", "comment": "同意入职" }` |
| **联调状态** | ⬜ 待联调 |

### 2.9 员工信息查询

| 项目 | 内容 |
|------|------|
| **接口地址** | `GET /api/employee/search?keyword=张三` |
| **Mock函数** | `mockSearchEmployee(keyword)` (app.js:163) |
| **请求头** | `Authorization: Bearer {token}` |
| **成功响应** | `{ "code": 0, "data": { "name": "张三", "code": "EMP000001", ... } }` |
| **未找到响应** | `{ "code": 0, "data": null }` |
| **联调状态** | ⬜ 待联调 |

---

## 3. 联调步骤与结果

### 3.1 联调前准备

- [x] 前端所有文件已部署到 Web 服务器（或本地开发服务器）
- [x] 后端接口已启动并可访问
- [x] 前后端已约定接口格式（见上述接口清单）
- [ ] 跨域问题已处理（后端配置 CORS 或前端使用代理）

### 3.2 联调测试用例

#### TC-001 登录功能

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| 1 | 访问 login.html | 显示登录页面 | - | ⬜ |
| 2 | 输入空账号密码，点击登录 | 前端提示"请输入账号" | - | ⬜ |
| 3 | 输入错误密码 admin / wrong | 后端返回错误提示 | - | ⬜ |
| 4 | 输入正确账号 admin / 123456 | 跳转到 index.html | - | ⬜ |
| 5 | 检查 localStorage | token 和用户信息已保存 | - | ⬜ |

#### TC-002 仪表盘统计

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| 1 | 登录后查看管理台首页 | 4个统计卡片显示数据 | - | ⬜ |
| 2 | 查看待办事项列表 | 显示5条待办事项 | - | ⬜ |
| 3 | 查看最近操作记录 | 5条记录展示正确 | - | ⬜ |

#### TC-003 入职表单

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| 1 | 点击"员工入职" | 显示入职表单 | - | ⬜ |
| 2 | 不填任何字段直接提交 | 所有必填字段显示错误 | - | ⬜ |
| 3 | 输入非法身份证号（17位） | 提示"有效的18位身份证号码" | - | ⬜ |
| 4 | 输入非法手机号（10位） | 提示"有效的11位手机号码" | - | ⬜ |
| 5 | 输入非法邮箱（无@） | 提示"有效的邮箱地址" | - | ⬜ |
| 6 | 填写完整合法数据提交 | 弹出成功提示，显示工号 | - | ⬜ |

#### TC-004 离职表单

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| 1 | 点击"员工离职" | 显示离职表单 | - | ⬜ |
| 2 | 仅填写必填项提交 | 校验通过提交成功 | - | ⬜ |
| 3 | 不填离职原因提交 | 提示"离职原因不能为空" | - | ⬜ |

#### TC-005 员工自助查询

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| 1 | 点击"员工自助" | 显示查询页面 | - | ⬜ |
| 2 | 输入"张三"点击查询 | 显示张三的详细信息 | - | ⬜ |
| 3 | 输入不存在的姓名 | 显示"未找到"提示 | - | ⬜ |
| 4 | 清空输入再次查询 | 提示输入关键词 | - | ⬜ |

#### TC-006 审批中心

| 步骤 | 操作 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| 1 | 点击"审批中心" | 显示待审批列表3条 | - | ⬜ |
| 2 | 切换到"已通过"标签 | 显示已通过列表 | - | ⬜ |
| 3 | 点击某条待审批的"处理"按钮 | 弹出审批模态框 | - | ⬜ |
| 4 | 不填审批意见直接点击同意 | 提示"审批意见不能为空" | - | ⬜ |
| 5 | 填写审批意见后点击同意 | 提示成功，列表刷新 | - | ⬜ |

### 3.3 联调结果汇总

| 模块 | 测试用例数 | 通过 | 失败 | 阻塞 | 通过率 | 备注 |
|------|-----------|------|------|------|--------|------|
| 登录 | 5 | - | - | - | -% | 待联调 |
| 仪表盘 | 3 | - | - | - | -% | 待联调 |
| 入职表单 | 6 | - | - | - | -% | 待联调 |
| 离职表单 | 3 | - | - | - | -% | 待联调 |
| 员工自助 | 4 | - | - | - | -% | 待联调 |
| 审批中心 | 5 | - | - | - | -% | 待联调 |
| **合计** | **26** | **-** | **-** | **-** | **-%** | 待联调 |

> **状态标识**：✅ 已通过 | ❌ 未通过 | ⬜ 待测试 | 🔄 修复中

---

## 4. 替换Mock为真实接口操作指南

### 4.1 标准替换模板

以登录接口为例，将 `app.js` 中的 `mockLogin` 函数替换为真实调用：

#### 替换前（Mock 代码）
```javascript
function mockLogin(username, password) {
    return new Promise((resolve) => {
        setTimeout(() => {
            // ... mock 逻辑
        }, 800);
    });
}
```

#### 替换后（真实接口调用）
```javascript
function mockLogin(username, password) {
    // ★★★ 真实接口替换示例 ★★★
    const BASE_URL = 'http://localhost:8088/api';  // 替换为实际后端地址
    
    return fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({ username, password })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络请求失败');
        }
        return response.json();
    })
    .then(data => {
        return data;  // 后端返回格式需与mock一致
    })
    .catch(error => {
        return {
            code: 9999,
            data: null,
            message: '网络异常: ' + error.message
        };
    });
}
```

### 4.2 替换清单

| Mock函数 | 替换方式 | 注意事项 |
|----------|---------|---------|
| `mockLogin` | fetch POST | 需存储 token 到 localStorage |
| `mockGetDashboardStats` | fetch GET | 需携带 Authorization 头 |
| `mockGetTodoList` | fetch GET | 同上 |
| `mockGetRecentRecords` | fetch GET | 同上 |
| `mockSubmitOnboard` | fetch POST | 表单数据转为 JSON |
| `mockSubmitOffboard` | fetch POST | 同上 |
| `mockGetApprovalList` | fetch GET | 需传 status 查询参数 |
| `mockApprovalAction` | fetch POST | 传 id, action, comment |
| `mockSearchEmployee` | fetch GET | 传 keyword 查询参数 |

### 4.3 统一请求封装建议

推荐封装一个 `api.js` 通用请求模块，统一处理 Token 注入和错误处理：

```javascript
// ===== api.js（建议新建文件）=====
const API_BASE = 'http://localhost:8088/api';

async function request(url, options = {}) {
    const token = localStorage.getItem('auth_token');
    
    const defaultHeaders = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };

    try {
        const response = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers: { ...defaultHeaders, ...options.headers }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API请求失败:', url, error);
        return { code: 9999, data: null, message: error.message };
    }
}

// 使用示例
export const api = {
    login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
    getDashboardStats: () => request('/dashboard/stats'),
    getTodos: () => request('/dashboard/todos'),
    submitOnboard: (data) => request('/onboard/submit', { method: 'POST', body: JSON.stringify(data) }),
    submitOffboard: (data) => request('/offboard/submit', { method: 'POST', body: JSON.stringify(data) }),
    getApprovalList: (status) => request(`/approval/list?status=${status}`),
    processApproval: (data) => request('/approval/process', { method: 'POST', body: JSON.stringify(data) }),
    searchEmployee: (keyword) => request(`/employee/search?keyword=${encodeURIComponent(keyword)}`)
};
```

---

## 5. 常见问题与排查

### 5.1 跨域问题 (CORS)

**现象**：浏览器控制台报错 `Access-Control-Allow-Origin`  
**解决方案**：
- 后端配置 CORS（推荐）
- 前端开发时使用代理（如 webpack-dev-server proxy）
- 浏览器安装 CORS 插件（仅开发调试用）

### 5.2 Token 过期

**现象**：接口返回 401 状态码  
**解决方案**：
- 前端拦截 401 响应，清除 token 并跳转到登录页
- 后端提供刷新 token 接口

### 5.3 字段映射不一致

**现象**：表单提交后后端报字段缺失  
**排查步骤**：
1. 查看前端 `FormData` 实际发送的字段名
2. 与后端 `@RequestBody` 接收的字段名对比
3. 统一字段命名规范（推荐使用 camelCase）

### 5.4 编码乱码

**现象**：中文显示为 `???` 或乱码  
**解决方案**：
- 确保所有文件保存为 UTF-8 编码
- HTML 中 `<meta charset="UTF-8">`
- 后端设置 `Content-Type: application/json;charset=UTF-8`

### 5.5 日期格式

**现象**：日期字段后端解析失败  
**解决方案**：
- 前端使用 `input[type=date]` 自动输出 `YYYY-MM-DD` 格式
- 后端使用 `@DateTimeFormat(pattern = "yyyy-MM-dd")` 注解

---

## 附录：部署验证清单

- [ ] 所有 `.html` 文件可正常访问
- [ ] `login.html` 登录后可跳转到 `index.html`
- [ ] 表单校验在前端正常工作
- [ ] Mock 数据能够正常展示
- [ ] 页面在 Chrome/Firefox/Edge 上显示正常
- [ ] 移动端响应式布局正常
- [ ] 所有按钮点击有反馈
- [ ] 退出登录清除 token 并跳转

---

*记录人：张铃（前端开发工程师）*  
*最后更新：2024-01-19*
