"""业务服务单元测试"""
import pytest
from datetime import date
from ..models import db
from ..models.employee import Employee, Department
from ..models.onboarding import OnboardingRequest, OnboardingStatus
from ..models.offboarding import OffboardingRequest, OffboardingStatus
from ..services.employee_service import EmployeeService, EmployeeServiceError
from ..services.onboarding_service import OnboardingService, OnboardingServiceError
from ..services.offboarding_service import OffboardingService, OffboardingServiceError
from ..services.hr_service import HRService, HRServiceError, HRMockClient


class TestEmployeeService:
    """员工管理服务测试"""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        with app.app_context():
            dept = Department(name='服务测试部', code='DEPT_SVC')
            db.session.add(dept)
            db.session.flush()
            self.dept_id = dept.id
            self.service = EmployeeService()

    def test_create_employee(self, app):
        with app.app_context():
            emp = self.service.create_employee({
                'employee_no': 'EMP_SVC_001',
                'name': '服务测试用户',
                'email': 'svc@test.com',
                'department_id': self.dept_id,
                'position': '测试工程师',
            }, operator_id=1)

            assert emp.id is not None
            assert emp.name == '服务测试用户'
            assert emp.email == 'svc@test.com'

    def test_create_duplicate_email(self, app):
        with app.app_context():
            self.service.create_employee({
                'employee_no': 'EMP_SVC_002',
                'name': '用户A',
                'email': 'dup@test.com',
                'department_id': self.dept_id,
            }, operator_id=1)

            with pytest.raises(EmployeeServiceError) as exc:
                self.service.create_employee({
                    'employee_no': 'EMP_SVC_003',
                    'name': '用户B',
                    'email': 'dup@test.com',
                    'department_id': self.dept_id,
                }, operator_id=1)
            assert '邮箱已存在' in str(exc.value)

    def test_get_employee(self, app):
        with app.app_context():
            emp = self.service.create_employee({
                'employee_no': 'EMP_SVC_004',
                'name': '查询测试',
                'email': 'query@test.com',
                'department_id': self.dept_id,
            }, operator_id=1)

            found = self.service.get_employee(emp.id)
            assert found is not None
            assert found.name == '查询测试'

    def test_get_nonexistent_employee(self, app):
        with app.app_context():
            found = self.service.get_employee(99999)
            assert found is None

    def test_update_employee(self, app):
        with app.app_context():
            emp = self.service.create_employee({
                'employee_no': 'EMP_SVC_005',
                'name': '更新测试',
                'email': 'update@test.com',
                'department_id': self.dept_id,
            }, operator_id=1)

            updated = self.service.update_employee(emp.id, {
                'name': '已更新',
                'phone': '13800000000',
            }, operator_id=1)

            assert updated.name == '已更新'
            assert updated.phone == '13800000000'

    def test_delete_employee(self, app):
        with app.app_context():
            emp = self.service.create_employee({
                'employee_no': 'EMP_SVC_006',
                'name': '删除测试',
                'email': 'delete@test.com',
                'department_id': self.dept_id,
            }, operator_id=1)

            self.service.delete_employee(emp.id, operator_id=1)
            assert emp.is_deleted is True

    def test_list_employees_with_keyword(self, app):
        with app.app_context():
            self.service.create_employee({
                'employee_no': 'EMP_SVC_007',
                'name': '张三丰',
                'email': 'zhang@test.com',
                'department_id': self.dept_id,
            }, operator_id=1)
            self.service.create_employee({
                'employee_no': 'EMP_SVC_008',
                'name': '李四',
                'email': 'li@test.com',
                'department_id': self.dept_id,
            }, operator_id=1)

            result = self.service.list_employees(keyword='张三')
            assert result['pagination']['total'] == 1
            assert result['items'][0]['name'] == '张三丰'

    def test_list_employees_pagination(self, app):
        with app.app_context():
            for i in range(5):
                self.service.create_employee({
                    'employee_no': f'EMP_PAGE_{i:03d}',
                    'name': f'分页测试{i}',
                    'email': f'page{i}@test.com',
                    'department_id': self.dept_id,
                }, operator_id=1)

            result = self.service.list_employees(page=1, page_size=2)
            assert result['pagination']['total'] >= 5
            assert len(result['items']) == 2

    def test_employee_approval_records_empty(self, app):
        with app.app_context():
            result = self.service.get_employee_approval_records(999)
            assert result['pagination']['total'] == 0


class TestOnboardingService:
    """入职服务测试"""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        with app.app_context():
            dept = Department(name='入职服务部', code='DEPT_ON_SVC')
            db.session.add(dept)
            db.session.flush()
            self.dept_id = dept.id
            self.service = OnboardingService()
            self.user_id = 1

    def test_create_draft(self, app):
        with app.app_context():
            req = self.service.create_request({
                'department_id': self.dept_id,
                'position': 'Java开发',
                'candidate_name': '小王',
                'candidate_email': 'wang@test.com',
                'expected_hire_date': date(2024, 8, 1),
            }, applicant_id=self.user_id)

            assert req.status == 'DRAFT'
            assert req.candidate_name == '小王'

    def test_create_and_submit(self, app):
        with app.app_context():
            req = self.service.create_request({
                'department_id': self.dept_id,
                'position': '测试',
                'candidate_name': '小李',
                'candidate_email': 'li@test.com',
                'expected_hire_date': date(2024, 8, 1),
            }, applicant_id=self.user_id)

            req = self.service.submit_request(req.id, self.user_id)
            assert req.status == 'PENDING_APPROVAL'

    def test_update_draft(self, app):
        with app.app_context():
            req = self.service.create_request({
                'department_id': self.dept_id,
                'position': '原职位',
                'candidate_name': '更新测试',
                'candidate_email': 'update@test.com',
                'expected_hire_date': date(2024, 8, 1),
            }, applicant_id=self.user_id)

            updated = self.service.update_request(req.id, {
                'position': '新职位',
                'remark': '更新备注',
            }, self.user_id)

            assert updated.position == '新职位'
            assert updated.remark == '更新备注'

    def test_cancel_draft(self, app):
        with app.app_context():
            req = self.service.create_request({
                'department_id': self.dept_id,
                'position': '取消测试',
                'candidate_name': '取消',
                'candidate_email': 'cancel@test.com',
                'expected_hire_date': date(2024, 8, 1),
            }, applicant_id=self.user_id)

            result = self.service.cancel_request(req.id, self.user_id)
            assert result['status'] == 'CANCELLED'

    def test_submit_nonexistent(self, app):
        with app.app_context():
            with pytest.raises(OnboardingServiceError) as exc:
                self.service.submit_request(99999, self.user_id)
            assert '不存在' in str(exc.value)

    def test_list_requests(self, app):
        with app.app_context():
            for i in range(3):
                self.service.create_request({
                    'department_id': self.dept_id,
                    'position': f'职位{i}',
                    'candidate_name': f'候选{i}',
                    'candidate_email': f'c{i}@test.com',
                    'expected_hire_date': date(2024, 8, 1),
                }, applicant_id=self.user_id)

            result = self.service.list_requests(self.user_id)
            assert result['pagination']['total'] >= 3


class TestOffboardingService:
    """离职服务测试"""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        with app.app_context():
            dept = Department(name='离职服务部', code='DEPT_OFF_SVC')
            db.session.add(dept)
            db.session.flush()

            emp = Employee(
                employee_no='EMP_OFF_SVC',
                name='离职员工',
                email='off_svc@test.com',
                department_id=dept.id,
            )
            db.session.add(emp)
            db.session.commit()

            self.dept_id = dept.id
            self.employee_id = emp.id
            self.service = OffboardingService()

    def test_create_draft(self, app):
        with app.app_context():
            req = self.service.create_request({
                'expected_last_date': date(2024, 7, 31),
                'reason': '个人发展',
            }, employee_id=self.employee_id)

            assert req.status == 'DRAFT'
            assert req.employee_name == '离职员工'

    def test_create_and_submit(self, app):
        with app.app_context():
            req = self.service.create_request({
                'expected_last_date': date(2024, 7, 31),
            }, employee_id=self.employee_id)

            req = self.service.submit_request(req.id, self.employee_id)
            assert req.status == 'PENDING_APPROVAL'

    def test_withdraw_request(self, app):
        with app.app_context():
            req = self.service.create_request({
                'expected_last_date': date(2024, 7, 31),
            }, employee_id=self.employee_id)
            req = self.service.submit_request(req.id, self.employee_id)

            result = self.service.withdraw_request(req.id, self.employee_id)
            assert result['status'] == 'WITHDRAWN'


class TestHRService:
    """HR系统对接服务测试"""

    def setup_method(self):
        self.service = HRService()

    def test_sync_employee_found(self):
        result = self.service.sync_employee('EMP000001')
        assert result is not None
        assert result['name'] == '张三'
        assert result['department_code'] == 'DEPT_TECH'

    def test_sync_employee_not_found(self):
        with pytest.raises(HRServiceError) as exc:
            self.service.sync_employee('NONEXISTENT')
        assert '未找到' in str(exc.value)

    def test_query_department_found(self):
        result = self.service.query_department('DEPT_TECH')
        assert result is not None
        assert result['name'] == '技术部'

    def test_query_department_not_found(self):
        with pytest.raises(HRServiceError) as exc:
            self.service.query_department('NONEXISTENT')
        assert '未找到' in str(exc.value)

    def test_sync_offboarding(self):
        result = self.service.sync_offboarding(
            employee_no='EMP000001',
            termination_date=date(2024, 6, 30),
            offboarding_type='RESIGNATION',
            reason='个人原因',
        )
        assert result is True

    def test_mock_client(self):
        client = HRMockClient()
        assert len(client.list_departments()) == 6

        emp = client.sync_employee_by_email('zhangsan@company.com')
        assert emp is not None
        assert emp['name'] == '张三'

        emp = client.sync_employee_by_email('notexist@company.com')
        assert emp is None
