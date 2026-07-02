"""员工管理API - 后端已通版本"""
from flask import request, jsonify, g
from . import api_bp
from services.employee_service import EmployeeService
from auth.permission_checker import require_permission
from utils.exceptions import AppException


employee_service = EmployeeService()


@api_bp.route('/employees', methods=['GET'])
@require_permission('employee:list')
def list_employees():
    """GET /api/v1/employees - 员工列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    department_id = request.args.get('department_id', type=str)
    status = request.args.get('status')
    keyword = request.args.get('keyword')

    result = employee_service.list_employees(
        page=page, page_size=page_size,
        department_id=department_id,
        status=status,
        keyword=keyword,
        operator_role='admin',
    )
    return jsonify({'success': True, 'data': result})


@api_bp.route('/employees', methods=['POST'])
@require_permission('employee:create')
def create_employee():
    """POST /api/v1/employees - 创建员工"""
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': {'code': 'INVALID_PARAMS', 'message': '请求体不能为空'}
        }), 400

    try:
        required_fields = ['employee_no', 'name', 'email', 'department_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': {'code': 'INVALID_PARAMS', 'message': f'缺少必填字段: {field}'}
                }), 400

        employee = employee_service.create_employee(
            data, operator_role='admin'
        )
        return jsonify({'success': True, 'data': employee}), 201
    except AppException as e:
        return jsonify({
            'success': False,
            'error': {'code': 'BUSINESS_ERROR', 'message': str(e)}
        }), 400


@api_bp.route('/employees/<int:employee_id>', methods=['GET'])
@require_permission('employee:read')
def get_employee(employee_id):
    """GET /api/v1/employees/:id - 员工详情"""
    try:
        employee = employee_service.get_employee(
            str(employee_id),
            operator_role='admin',
            operator_id=str(getattr(g, 'current_user_id', 0)),
            operator_dept_id='',
        )
        return jsonify({'success': True, 'data': employee})
    except AppException as e:
        return jsonify({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': str(e)}
        }), 404
