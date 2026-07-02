"""HR系统对接API"""
from flask import request, jsonify
from . import api_bp
from services.hr_service import HRService, HRServiceError
from auth.permission_checker import require_permission


hr_service = HRService()


@api_bp.route('/hr/employees/sync', methods=['POST'])
@require_permission('hr:sync')
def sync_employee():
    """POST /api/v1/hr/employees/sync - 从HR系统同步员工"""
    data = request.get_json()
    if not data or 'employee_no' not in data:
        return jsonify({
            'success': False,
            'error': {'code': 'INVALID_PARAMS', 'message': '缺少 employee_no'}
        }), 400

    try:
        result = hr_service.sync_employee(data['employee_no'])
        return jsonify({'success': True, 'data': result})
    except HRServiceError as e:
        return jsonify({
            'success': False,
            'error': {'code': 'HR_SYNC_ERROR', 'message': str(e)}
        }), 400


@api_bp.route('/hr/departments', methods=['GET'])
@require_permission('hr:department')
def list_departments():
    """GET /api/v1/hr/departments - 查询HR系统部门列表"""
    code = request.args.get('code')
    try:
        if code:
            result = hr_service.query_department(code)
        else:
            from services.hr_service import HRMockClient
            client = HRMockClient()
            result = client.list_departments()
        return jsonify({'success': True, 'data': result})
    except HRServiceError as e:
        return jsonify({
            'success': False,
            'error': {'code': 'HR_QUERY_ERROR', 'message': str(e)}
        }), 400


@api_bp.route('/hr/offboarding/sync', methods=['POST'])
@require_permission('hr:sync')
def sync_offboarding():
    """POST /api/v1/hr/offboarding/sync - 同步离职数据到HR系统"""
    data = request.get_json()
    if not data or 'employee_no' not in data or 'termination_date' not in data:
        return jsonify({
            'success': False,
            'error': {'code': 'INVALID_PARAMS', 'message': '缺少 employee_no 或 termination_date'}
        }), 400

    from datetime import date
    termination_date = date.fromisoformat(data['termination_date'])

    try:
        result = hr_service.sync_offboarding(
            employee_no=data['employee_no'],
            termination_date=termination_date,
            offboarding_type=data.get('offboarding_type', 'RESIGNATION'),
            reason=data.get('reason'),
        )
        return jsonify({'success': True, 'data': {'synced': result}})
    except HRServiceError as e:
        return jsonify({
            'success': False,
            'error': {'code': 'HR_SYNC_ERROR', 'message': str(e)}
        }), 400
