"""入职申请API - 后端已通版本"""
from flask import request, jsonify, g
from . import api_bp
from services.onboarding_service import OnboardingService
from auth.permission_checker import require_permission
from utils.exceptions import AppException


onboarding_service = OnboardingService()


@api_bp.route('/onboarding-requests', methods=['POST'])
@require_permission('onboarding:create')
def create_onboarding_request():
    """POST /api/v1/onboarding-requests - 创建入职申请"""
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': {'code': 'INVALID_PARAMS', 'message': '请求体不能为空'}
        }), 400

    try:
        req = onboarding_service.create_draft(
            data, applicant_id=str(getattr(g, 'current_user_id', 0)),
            operator_role='admin'
        )
        return jsonify({'success': True, 'data': req}), 201
    except AppException as e:
        return jsonify({
            'success': False,
            'error': {'code': 'BUSINESS_ERROR', 'message': str(e)}
        }), 400


@api_bp.route('/onboarding-requests', methods=['GET'])
@require_permission('onboarding:read')
def list_onboarding_requests():
    """GET /api/v1/onboarding-requests - 查询入职申请列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    status = request.args.get('status')

    result = onboarding_service.list_requests(
        page=page, page_size=page_size, status=status,
        operator_role='admin',
    )
    return jsonify({'success': True, 'data': result})


@api_bp.route('/onboarding-requests/<int:request_id>', methods=['GET'])
@require_permission('onboarding:read')
def get_onboarding_request(request_id):
    """GET /api/v1/onboarding-requests/:id - 入职申请详情"""
    req = onboarding_service.get_request(
        str(request_id),
        operator_id=str(getattr(g, 'current_user_id', 0)),
        operator_role='admin',
    )
    if not req:
        return jsonify({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': '入职申请不存在'}
        }), 404
    return jsonify({'success': True, 'data': req})


@api_bp.route('/onboarding-requests/<int:request_id>/submit', methods=['POST'])
@require_permission('onboarding:create')
def submit_onboarding_request(request_id):
    """POST /api/v1/onboarding-requests/:id/submit - 提交审批"""
    try:
        req = onboarding_service.submit(
            str(request_id),
            operator_id=str(getattr(g, 'current_user_id', 0)),
            operator_role='admin',
        )
        return jsonify({'success': True, 'data': req})
    except AppException as e:
        return jsonify({
            'success': False,
            'error': {'code': 'BUSINESS_ERROR', 'message': str(e)}
        }), 400


@api_bp.route('/onboarding-requests/<int:request_id>/cancel', methods=['POST'])
@require_permission('onboarding:cancel')
def cancel_onboarding_request(request_id):
    """POST /api/v1/onboarding-requests/:id/cancel - 取消申请"""
    try:
        result = onboarding_service.cancel(
            str(request_id),
            operator_id=str(getattr(g, 'current_user_id', 0)),
            operator_role='admin',
        )
        return jsonify({'success': True, 'data': result})
    except AppException as e:
        return jsonify({
            'success': False,
            'error': {'code': 'BUSINESS_ERROR', 'message': str(e)}
        }), 400
