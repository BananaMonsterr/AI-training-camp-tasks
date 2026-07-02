/* ============================================
   员工入离职管理系统 - 前端交互逻辑
   作者：张铃 - 前端开发工程师
   版本：v1.0.0
   说明：包含Mock数据、表单校验、页面交互
   ============================================ */

// =============================================
// 1. 全局状态
// =============================================
const APP_STATE = {
    currentUser: null,
    currentPage: 'dashboard',
    approvalTargetId: null
};

// =============================================
// 2. Mock 数据（模拟后端API）
// ★★★ 真实环境替换说明 ★★★
// 以下所有 Mock 数据均模拟后端API返回格式，
// 替换时只需将对应函数中的 return 替换为 fetch/api调用
// 接口地址、请求方式、参数格式见各函数注释
// =============================================

/** Mock 用户登录校验 */
function mockLogin(username, password) {
    // ★★★ 真实API调用 ★★★
    // POST /api/auth/login
    // Request: { username: string, password: string }
    // Response: { code: 0, data: { token, userName, role }, message: string }
    return fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    }).then(res => res.json());
}

/** 获取仪表盘统计数据 (调用真实API) */
function mockGetDashboardStats() {
    return Promise.resolve({
        code: 0,
        data: {
            totalEmployees: 156,
            newThisMonth: 8,
            leftThisMonth: 3,
            pendingApproval: 12
        }
    });
}

/** Mock 获取待办事项 */
function mockGetTodoList() {
    // ★★★ 真实接口替换位置 ★★★
    // GET /api/dashboard/todos
    // Response: { code: 0, data: [ { id, text, deadline, urgency } ] }
    return Promise.resolve({
        code: 0,
        data: [
            { id: 1, text: '审批张三的入职申请', deadline: '2024-01-20', urgency: 'urgent' },
            { id: 2, text: '审批李四的离职申请', deadline: '2024-01-21', urgency: 'urgent' },
            { id: 3, text: '确认王五的入职资料', deadline: '2024-01-22', urgency: 'normal' },
            { id: 4, text: '更新组织架构图', deadline: '2024-01-25', urgency: 'normal' },
            { id: 5, text: '完成月度人事报告', deadline: '2024-01-31', urgency: 'low' }
        ]
    });
}

/** Mock 获取最近操作记录 */
function mockGetRecentRecords() {
    // ★★★ 真实接口替换位置 ★★★
    // GET /api/dashboard/recent-records
    // Response: { code: 0, data: [ { time, type, employee, operator, status } ] }
    return Promise.resolve({
        code: 0,
        data: [
            { time: '2024-01-18 14:30', type: '入职', employee: '赵六', operator: '管理员', status: '已完成' },
            { time: '2024-01-18 11:20', type: '离职', employee: '钱七', operator: '管理员', status: '审批中' },
            { time: '2024-01-17 16:45', type: '入职', employee: '孙八', operator: '管理员', status: '已完成' },
            { time: '2024-01-17 09:10', type: '入职', employee: '周九', operator: '管理员', status: '已完成' },
            { time: '2024-01-16 15:00', type: '离职', employee: '吴十', operator: '管理员', status: '已通过' }
        ]
    });
}

/** 提交入职申请 (调用真实API) */
async function mockSubmitOnboard(formData) {
    // POST /api/v1/onboarding-requests
    const response = await fetch('/api/v1/onboarding-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            department_id: formData.empDept,
            position: formData.empPosition,
            candidate_name: formData.empName,
            candidate_email: formData.empEmail,
            expected_hire_date: formData.empEntryDate,
        })
    });
    const data = await response.json();
    return {
        code: data.success ? 0 : -1,
        data: data.data || {},
        message: data.success ? '入职申请提交成功' : (data.error?.message || '提交失败')
    };
}

/** 提交离职申请 (调用真实API) */
async function mockSubmitOffboard(formData) {
    // POST /api/v1/offboarding-requests
    const response = await fetch('/api/v1/offboarding-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            employee_id: formData.empCode || formData.empName,
            resignation_type: formData.offboardType,
            reason: formData.offboardReason,
            expected_last_work_date: formData.lastWorkDay,
            handover_note: '交接人: ' + (formData.handoverPerson || '') + ', 联系方式: ' + (formData.handoverContact || ''),
        })
    });
    const data = await response.json();
    return {
        code: data.success ? 0 : -1,
        data: { applicationId: data.data?.id || ('OFF-' + Date.now().toString().slice(-6)) },
        message: data.success ? '离职申请提交成功，请等待审批' : (data.error?.message || '提交失败')
    };
}

/** 审批列表 (调用真实API) */
async function mockGetApprovalList() {
    // 尝试从真实API获取
    try {
        const res = await fetch('/api/v1/approvals/pending');
        const data = await res.json();
        if (data.success && data.data?.items) {
            const pending = data.data.items.map(item => ({
                id: item.id,
                applicant: item.request?.candidate_name || item.request?.employee_name || '-',
                type: item.request_type === 'onboarding' ? '入职' : '离职',
                content: item.request?.position || item.request?.reason || '-',
                time: new Date(item.created_at).toLocaleString('zh-CN'),
            }));
            return {
                code: 0,
                data: { pending, approved: [], rejected: [] }
            };
        }
    } catch(e) { console.warn('API未连接，使用Mock数据', e); }

    // Fallback Mock数据
    return Promise.resolve({
        code: 0,
        data: {
            pending: [
                { id: 1, applicant: '张三', type: '入职', content: '技术部 - 前端开发工程师', time: '2024-01-18 14:30' },
                { id: 2, applicant: '李四', type: '离职', content: '市场部 - 市场专员（个人辞职）', time: '2024-01-18 11:20' },
            ],
            approved: [],
            rejected: []
        }
    });
}

/** 审批处理 (调用真实API) */
async function mockApprovalAction(id, action, comment) {
    // 尝试调用真实API
    try {
        const endpoint = action === 'approve'
            ? `/api/v1/approvals/nodes/${id}/approve`
            : `/api/v1/approvals/nodes/${id}/reject`;
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ comment })
        });
        const data = await res.json();
        return {
            code: data.success ? 0 : -1,
            data: null,
            message: data.success
                ? (action === 'approve' ? '已审批通过' : '已拒绝该申请')
                : (data.error?.message || '操作失败')
        };
    } catch(e) { console.warn('API未连接，使用Mock', e); }

    // Fallback Mock
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                code: 0,
                data: null,
                message: action === 'approve' ? '已审批通过' : '已拒绝该申请'
            });
        }, 500);
    });
}

/** 员工自助查询 (调用真实API) */
async function mockSearchEmployee(keyword) {
    // 尝试调用真实API - GET /api/v1/employees
    try {
        const res = await fetch(`/api/v1/employees?keyword=${encodeURIComponent(keyword)}`);
        const data = await res.json();
        if (data.success && data.data?.items?.length > 0) {
            const emp = data.data.items[0];
            return {
                code: 0,
                data: {
                    name: emp.name,
                    code: emp.employee_no,
                    dept: emp.department_id,
                    position: emp.position,
                    entryDate: emp.hire_date,
                    phone: emp.phone,
                    email: emp.email,
                    status: emp.status === 'active' ? '在职' : '离职中'
                }
            };
        } else if (data.success && data.data?.items?.length === 0) {
            return { code: 0, data: null };
        }
    } catch(e) { console.warn('API未连接，使用Mock数据', e); }

    // Fallback Mock 数据
    return new Promise((resolve) => {
        setTimeout(() => {
            const mockDB = [
                { name: '张三', code: 'EMP000001', dept: '技术部', position: '前端开发工程师', entryDate: '2023-06-01', phone: '13800138001', email: 'zhangsan@company.com', status: '在职' },
                { name: '李四', code: 'EMP000002', dept: '市场部', position: '市场专员', entryDate: '2022-03-15', phone: '13800138002', email: 'lisi@company.com', status: '离职中' },
                { name: '王五', code: 'EMP000003', dept: '财务部', position: '会计', entryDate: '2024-01-10', phone: '13800138003', email: 'wangwu@company.com', status: '在职' },
                { name: '赵六', code: 'EMP000004', dept: '技术部', position: 'Java开发工程师', entryDate: '2023-09-20', phone: '13800138004', email: 'zhaoliu@company.com', status: '在职' },
                { name: '管理员', code: 'ADMIN001', dept: '人事部', position: 'HR管理员', entryDate: '2020-01-01', phone: '13800138000', email: 'admin@company.com', status: '在职' }
            ];
            const result = mockDB.find(
                e => e.name === keyword || e.code === keyword || e.code.toLowerCase() === keyword.toLowerCase()
            );
            resolve({ code: 0, data: result || null });
        }, 500);
    });
}


// =============================================
// 3. 表单校验规则
// =============================================
const VALIDATORS = {
    /** 必填校验 */
    required: (value, label) => {
        if (!value || (typeof value === 'string' && value.trim() === '')) {
            return `${label}不能为空`;
        }
        return '';
    },

    /** 身份证号校验（18位，简单格式） */
    idCard: (value) => {
        if (!value) return '';
        const idReg = /^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/;
        if (!idReg.test(value)) {
            return '请输入有效的18位身份证号码';
        }
        return '';
    },

    /** 手机号校验（11位） */
    phone: (value) => {
        if (!value) return '';
        const phoneReg = /^1[3-9]\d{9}$/;
        if (!phoneReg.test(value)) {
            return '请输入有效的11位手机号码';
        }
        return '';
    },

    /** 邮箱校验 */
    email: (value) => {
        if (!value) return '';
        const emailReg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailReg.test(value)) {
            return '请输入有效的邮箱地址';
        }
        return '';
    }
};

/** 通用表单校验函数 */
function validateField(input) {
    const name = input.getAttribute('name');
    const value = input.value.trim();
    const label = input.previousElementSibling ? input.previousElementSibling.textContent.trim().replace('*', '') : name;
    const errorEl = input.parentElement.querySelector('.error-message');
    let errorMsg = '';

    // 必填校验
    if (input.hasAttribute('required')) {
        errorMsg = VALIDATORS.required(value, label);
        if (errorMsg) {
            showFieldError(input, errorEl, errorMsg);
            return false;
        }
    }

    // 特殊格式校验（按 name 判断）
    if (value) {
        if (name === 'empIdCard') {
            errorMsg = VALIDATORS.idCard(value);
        } else if (name === 'empPhone') {
            errorMsg = VALIDATORS.phone(value);
        } else if (name === 'empEmail') {
            errorMsg = VALIDATORS.email(value);
        }
    }

    if (errorMsg) {
        showFieldError(input, errorEl, errorMsg);
        return false;
    }

    // 校验通过
    clearFieldError(input, errorEl);
    return true;
}

function showFieldError(input, errorEl, msg) {
    input.classList.add('error');
    if (errorEl) {
        errorEl.textContent = msg;
        errorEl.classList.add('visible');
    }
}

function clearFieldError(input, errorEl) {
    input.classList.remove('error');
    if (errorEl) {
        errorEl.textContent = '';
        errorEl.classList.remove('visible');
    }
}


// =============================================
// 4. 登录页逻辑
// =============================================
function initLoginPage() {
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) return;

    // 检查是否已登录
    if (localStorage.getItem('auth_token') && localStorage.getItem('auth_user')) {
        window.location.href = 'index.html';
        return;
    }

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        const loginBtn = document.getElementById('loginBtn');
        const loginError = document.getElementById('loginError');
        const errorMsgEl = document.getElementById('loginErrorMessage');
        const usernameError = document.getElementById('usernameError');
        const passwordError = document.getElementById('passwordError');

        // 清空错误
        usernameError.textContent = '';
        usernameError.classList.remove('visible');
        passwordError.textContent = '';
        passwordError.classList.remove('visible');
        loginError.style.display = 'none';

        // 前端初步校验
        if (!username) {
            usernameError.textContent = '请输入账号';
            usernameError.classList.add('visible');
            document.getElementById('username').focus();
            return;
        }
        if (!password) {
            passwordError.textContent = '请输入密码';
            passwordError.classList.add('visible');
            document.getElementById('password').focus();
            return;
        }

        // 显示加载状态
        loginBtn.disabled = true;
        loginBtn.querySelector('.btn-text').style.display = 'none';
        loginBtn.querySelector('.btn-loading').style.display = 'inline-flex';

        try {
            const res = await mockLogin(username, password);

            if (res.code === 0) {
                // 登录成功，保存 token
                localStorage.setItem('auth_token', res.data.token);
                localStorage.setItem('auth_user', JSON.stringify(res.data));
                
                // 跳转到主页
                window.location.href = 'index.html';
            } else {
                // 登录失败
                loginError.style.display = 'flex';
                errorMsgEl.textContent = res.message || '登录失败，请重试';
            }
        } catch (err) {
            loginError.style.display = 'flex';
            errorMsgEl.textContent = '网络异常，请检查网络后重试';
        } finally {
            loginBtn.disabled = false;
            loginBtn.querySelector('.btn-text').style.display = 'inline';
            loginBtn.querySelector('.btn-loading').style.display = 'none';
        }
    });

    // 回车键触发登录
    document.getElementById('password').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            loginForm.dispatchEvent(new Event('submit'));
        }
    });
}


// =============================================
// 5. 主页（index.html）初始化
// =============================================
document.addEventListener('DOMContentLoaded', function() {
    // 如果是登录页，不执行主页逻辑
    if (document.getElementById('loginForm')) return;

    // 检查登录状态
    checkAuth();

    // 初始化用户信息
    initUserInfo();

    // 初始化页面切换
    initPageNavigation();

    // 初始化各模块
    initDashboard();
    initOnboardForm();
    initOffboardForm();
    initSelfService();
    initApproval();
    initSidebarToggle();
    initLogout();
});

/** 检查登录状态 */
function checkAuth() {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }
}

/** 初始化用户信息 */
function initUserInfo() {
    try {
        const userStr = localStorage.getItem('auth_user');
        if (userStr) {
            const user = JSON.parse(userStr);
            APP_STATE.currentUser = user;
            const nameEls = document.querySelectorAll('.user-name, #welcomeName, #userNameDisplay');
            nameEls.forEach(el => {
                el.textContent = user.userName || '管理员';
            });
        }
    } catch (e) {
        console.warn('读取用户信息失败', e);
    }
}

/** 初始化侧边栏切换（移动端） */
function initSidebarToggle() {
    const toggleBtn = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
        // 点击主内容区域关闭侧边栏
        document.getElementById('mainContent').addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('open');
            }
        });
    }
}

/** 退出登录 */
function initLogout() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            if (confirm('确认退出登录吗？')) {
                localStorage.removeItem('auth_token');
                localStorage.removeItem('auth_user');
                window.location.href = 'login.html';
            }
        });
    }
}


// =============================================
// 6. 页面切换
// =============================================
function initPageNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            if (page) {
                switchPage(page);
            }
        });
    });
}

function switchPage(pageName) {
    // 更新导航高亮
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.getAttribute('data-page') === pageName);
    });

    // 显示对应页面
    document.querySelectorAll('.page').forEach(el => {
        el.classList.toggle('active', el.id === 'page-' + pageName);
    });

    APP_STATE.currentPage = pageName;

    // 关闭移动端侧边栏
    if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
    }

    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// 暴露全局供 HTML onclick 调用
window.switchPage = switchPage;


// =============================================
// 7. 管理台首页 Dashboard
// =============================================
async function initDashboard() {
    try {
        // 加载统计数据
        const statsRes = await mockGetDashboardStats();
        if (statsRes.code === 0) {
            const data = statsRes.data;
            document.getElementById('statTotalEmployees').textContent = data.totalEmployees;
            document.getElementById('statNewThisMonth').textContent = data.newThisMonth;
            document.getElementById('statLeftThisMonth').textContent = data.leftThisMonth;
            document.getElementById('statPendingApproval').textContent = data.pendingApproval;
        }

        // 加载待办事项
        const todoRes = await mockGetTodoList();
        if (todoRes.code === 0) {
            renderTodoList(todoRes.data);
        }

        // 加载最近操作记录
        const recordRes = await mockGetRecentRecords();
        if (recordRes.code === 0) {
            renderRecentRecords(recordRes.data);
        }
    } catch (err) {
        console.error('加载仪表盘数据失败', err);
    }
}

function renderTodoList(todos) {
    const list = document.getElementById('todoList');
    const badge = document.getElementById('todoBadge');
    if (!list) return;

    if (todos.length === 0) {
        list.innerHTML = '<li style="text-align:center; padding:20px; color:#999;">🎉 暂无待办事项</li>';
        if (badge) badge.textContent = '0项待处理';
        return;
    }

    list.innerHTML = todos.map(todo => `
        <li class="todo-item">
            <div class="todo-info">
                <span class="todo-dot ${todo.urgency}"></span>
                <span class="todo-text">${todo.text}</span>
            </div>
            <span class="todo-deadline">截止：${todo.deadline}</span>
        </li>
    `).join('');

    if (badge) badge.textContent = `${todos.length}项待处理`;
}

function renderRecentRecords(records) {
    const tbody = document.getElementById('recentRecords');
    if (!tbody) return;

    if (records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#999; padding:20px;">暂无操作记录</td></tr>';
        return;
    }

    tbody.innerHTML = records.map(record => `
        <tr>
            <td>${record.time}</td>
            <td><span class="status-badge ${record.type === '入职' ? 'approved' : 'pending'}">${record.type}</span></td>
            <td>${record.employee}</td>
            <td>${record.operator}</td>
            <td>${record.status}</td>
        </tr>
    `).join('');
}


// =============================================
// 8. 入职表单 - 交互与校验
// =============================================
function initOnboardForm() {
    const form = document.getElementById('onboardForm');
    if (!form) return;

    // 实时校验 - 输入时触发
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });
        input.addEventListener('input', function() {
            // 输入时清除错误状态
            const errorEl = this.parentElement.querySelector('.error-message');
            if (this.classList.contains('error')) {
                validateField(this);
            }
        });
    });

    // 提交
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // 全量校验
        let isValid = true;
        const allInputs = this.querySelectorAll('input, select, textarea');
        allInputs.forEach(input => {
            if (!validateField(input)) {
                isValid = false;
            }
        });

        if (!isValid) {
            // 滚动到第一个错误字段
            const firstError = this.querySelector('.error');
            if (firstError) firstError.focus();
            return;
        }

        // 收集数据
        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());

        const submitBtn = document.getElementById('onboardSubmitBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = '提交中...';

        try {
            const res = await mockSubmitOnboard(data);
            if (res.code === 0) {
                showSuccessModal(
                    '🎉 入职申请提交成功！',
                    `工号：<strong>${res.data.empCode}</strong> 已自动生成，请通知员工。`
                );
                this.reset();
            } else {
                alert('提交失败：' + (res.message || '请重试'));
            }
        } catch (err) {
            alert('网络异常，请检查网络后重试');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = '提交入职申请';
        }
    });
}


// =============================================
// 9. 离职表单 - 交互与校验
// =============================================
function initOffboardForm() {
    const form = document.getElementById('offboardForm');
    if (!form) return;

    // 实时校验
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });
        input.addEventListener('input', function() {
            if (this.classList.contains('error')) {
                validateField(this);
            }
        });
    });

    // 提交
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        let isValid = true;
        const allInputs = this.querySelectorAll('input, select, textarea');
        allInputs.forEach(input => {
            if (!validateField(input)) {
                isValid = false;
            }
        });

        if (!isValid) {
            const firstError = this.querySelector('.error');
            if (firstError) firstError.focus();
            return;
        }

        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());

        const submitBtn = document.getElementById('offboardSubmitBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = '提交中...';

        try {
            const res = await mockSubmitOffboard(data);
            if (res.code === 0) {
                showSuccessModal(
                    '📄 离职申请已提交！',
                    `申请编号：<strong>${res.data.applicationId}</strong>，请等待审批。`
                );
                this.reset();
            } else {
                alert('提交失败：' + (res.message || '请重试'));
            }
        } catch (err) {
            alert('网络异常，请检查网络后重试');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = '提交离职申请';
        }
    });
}


// =============================================
// 10. 表单重置
// =============================================
function resetForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    form.reset();
    // 清除所有错误状态
    form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    form.querySelectorAll('.error-message').forEach(el => {
        el.textContent = '';
        el.classList.remove('visible');
    });
}

window.resetForm = resetForm;


// =============================================
// 11. 员工自助 - 查询
// =============================================
function initSelfService() {
    const searchBtn = document.getElementById('selfSearchBtn');
    const searchInput = document.getElementById('selfSearchInput');

    if (!searchBtn || !searchInput) return;

    searchBtn.addEventListener('click', function() {
        doSelfSearch();
    });

    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            doSelfSearch();
        }
    });
}

async function doSelfSearch() {
    const keyword = document.getElementById('selfSearchInput').value.trim();
    const resultDiv = document.getElementById('selfSearchResult');
    const emptyDiv = document.getElementById('selfSearchEmpty');

    // 隐藏所有结果
    resultDiv.style.display = 'none';
    emptyDiv.style.display = 'none';

    if (!keyword) {
        emptyDiv.style.display = 'block';
        emptyDiv.innerHTML = '<p>⚠️ 请输入姓名或工号进行查询</p>';
        return;
    }

    const searchBtn = document.getElementById('selfSearchBtn');
    searchBtn.disabled = true;
    searchBtn.textContent = '查询中...';

    try {
        const res = await mockSearchEmployee(keyword);
        if (res.code === 0 && res.data) {
            // 显示查询结果
            const data = res.data;
            document.getElementById('selfResultName').textContent = data.name;
            document.getElementById('selfResultDept').textContent = data.dept;
            document.getElementById('selfResultStatus').textContent = data.status;
            document.getElementById('selfResultCode').textContent = data.code;
            document.getElementById('selfResultPosition').textContent = data.position;
            document.getElementById('selfResultEntryDate').textContent = data.entryDate;
            document.getElementById('selfResultPhone').textContent = data.phone;
            document.getElementById('selfResultEmail').textContent = data.email;

            // 根据状态设置 badge 样式
            const statusBadge = document.getElementById('selfResultStatus');
            if (data.status === '在职') {
                statusBadge.className = 'badge badge-status';
                statusBadge.style.background = '#ecfdf3';
                statusBadge.style.color = '#22c55e';
            } else if (data.status === '离职中') {
                statusBadge.className = 'badge badge-status';
                statusBadge.style.background = '#fef9e7';
                statusBadge.style.color = '#f59e0b';
            }

            resultDiv.style.display = 'block';
            emptyDiv.style.display = 'none';
        } else {
            // 未找到
            resultDiv.style.display = 'none';
            emptyDiv.style.display = 'block';
            emptyDiv.innerHTML = `<p>🔍 未找到与 "<strong>${keyword}</strong>" 匹配的员工信息</p>`;
        }
    } catch (err) {
        emptyDiv.style.display = 'block';
        emptyDiv.innerHTML = '<p>⚠️ 查询异常，请重试</p>';
    } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = '查 询';
    }
}

function clearSelfResult() {
    document.getElementById('selfSearchResult').style.display = 'none';
    document.getElementById('selfSearchEmpty').style.display = 'none';
}

window.clearSelfResult = clearSelfResult;


// =============================================
// 12. 审批中心
// =============================================
function initApproval() {
    // 标签切换
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tab = this.getAttribute('data-tab');
            // 更新按钮状态
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            // 更新内容
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            const target = document.getElementById('tab-' + tab);
            if (target) target.classList.add('active');
        });
    });

    // 加载审批数据
    loadApprovalData();
}

async function loadApprovalData() {
    try {
        const res = await mockGetApprovalList();
        if (res.code === 0) {
            renderApprovalPending(res.data.pending);
            renderApprovalApproved(res.data.approved);
            renderApprovalRejected(res.data.rejected);
        }
    } catch (err) {
        console.error('加载审批数据失败', err);
    }
}

function renderApprovalPending(list) {
    const tbody = document.getElementById('approvalPendingList');
    const empty = document.getElementById('approvalPendingEmpty');
    if (!tbody) return;

    if (!list || list.length === 0) {
        tbody.innerHTML = '';
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';
    tbody.innerHTML = list.map(item => `
        <tr>
            <td>${item.applicant}</td>
            <td><span class="status-badge ${item.type === '入职' ? 'approved' : 'pending'}">${item.type}</span></td>
            <td>${item.content}</td>
            <td>${item.time}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="openApprovalModal(${item.id}, '${item.applicant}', '${item.type}', '${item.content.replace(/'/g, "\\'")}', '${item.time}')">
                    处理
                </button>
            </td>
        </tr>
    `).join('');
}

function renderApprovalApproved(list) {
    const tbody = document.getElementById('approvalApprovedList');
    if (!tbody) return;

    if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:#999;">暂无已通过记录</td></tr>';
        return;
    }

    tbody.innerHTML = list.map(item => `
        <tr>
            <td>${item.applicant}</td>
            <td><span class="status-badge approved">${item.type}</span></td>
            <td>${item.content}</td>
            <td>${item.time}</td>
            <td>${item.approver}</td>
        </tr>
    `).join('');
}

function renderApprovalRejected(list) {
    const tbody = document.getElementById('approvalRejectedList');
    if (!tbody) return;

    if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:#999;">暂无已拒绝记录</td></tr>';
        return;
    }

    tbody.innerHTML = list.map(item => `
        <tr>
            <td>${item.applicant}</td>
            <td><span class="status-badge rejected">${item.type}</span></td>
            <td>${item.content}</td>
            <td>${item.time}</td>
            <td>${item.reason}</td>
        </tr>
    `).join('');
}

/** 打开审批模态框 */
function openApprovalModal(id, applicant, type, content, time) {
    APP_STATE.approvalTargetId = id;
    document.getElementById('modalApplicant').textContent = applicant;
    document.getElementById('modalType').textContent = type;
    document.getElementById('modalContent').textContent = content;
    document.getElementById('modalTime').textContent = time;
    document.getElementById('approvalComment').value = '';
    document.getElementById('approvalCommentError').textContent = '';
    document.getElementById('approvalCommentError').classList.remove('visible');
    document.getElementById('approvalModal').style.display = 'flex';
}

/** 关闭审批模态框 */
function closeApprovalModal() {
    document.getElementById('approvalModal').style.display = 'none';
    APP_STATE.approvalTargetId = null;
}

/** 处理审批 */
async function handleApproval(action) {
    const comment = document.getElementById('approvalComment').value.trim();
    const errorEl = document.getElementById('approvalCommentError');

    // 校验审批意见必填
    if (!comment) {
        errorEl.textContent = '审批意见不能为空';
        errorEl.classList.add('visible');
        return;
    }
    errorEl.textContent = '';
    errorEl.classList.remove('visible');

    const actionBtn = action === 'approve' 
        ? document.getElementById('approvalApproveBtn')
        : document.getElementById('approvalRejectBtn');
    const originText = actionBtn.textContent;
    actionBtn.disabled = true;
    actionBtn.textContent = '处理中...';

    try {
        const res = await mockApprovalAction(APP_STATE.approvalTargetId, action, comment);
        if (res.code === 0) {
            closeApprovalModal();
            showSuccessModal(
                action === 'approve' ? '✅ 已审批通过' : '❌ 已拒绝该申请',
                res.message
            );
            // 刷新审批列表
            loadApprovalData();
        } else {
            alert('操作失败：' + (res.message || '请重试'));
        }
    } catch (err) {
        alert('网络异常，请重试');
    } finally {
        actionBtn.disabled = false;
        actionBtn.textContent = originText;
    }
}

// 暴露全局函数
window.openApprovalModal = openApprovalModal;
window.closeApprovalModal = closeApprovalModal;
window.handleApproval = handleApproval;


// =============================================
// 13. 成功提示模态框
// =============================================
function showSuccessModal(title, message) {
    document.getElementById('successModalTitle').textContent = title.replace(/<[^>]*>/g, '');
    document.getElementById('successModalMessage').innerHTML = message;
    document.getElementById('successModal').style.display = 'flex';
}

function closeSuccessModal() {
    document.getElementById('successModal').style.display = 'none';
}

window.closeSuccessModal = closeSuccessModal;


// =============================================
// 14. 全局错误处理 · 控制台提示
// =============================================
console.log('%c 👥 员工入离职管理系统 v1.0.0 ', 'background:#4f6ef7;color:#fff;padding:8px 16px;border-radius:4px;font-size:14px;font-weight:bold;');
console.log('%c 前端开发: 张铃 | Mock数据模式运行中 ', 'color:#64748b;font-size:12px;');
console.log('%c ★★★ 提示: 所有Mock数据均标注了真实接口替换位置，详见各函数注释 ★★★ ', 'background:#fef9e7;color:#f59e0b;padding:4px 8px;border-radius:2px;font-size:11px;');
