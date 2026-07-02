"""审批操作API"""
from flask import request, jsonify, g
from . import api_bp
from auth.permission_checker import require_permission
from utils.exceptions import AppException

# 注意: approval_engine 依赖完整 SQLAlchemy 数据库层，当前 Demo 模式使用内存 Mock


@api_bp.route('/approvals/pending', methods=['GET'])
@require_permission('approval:list')
def get_pending_approvals():
    """GET /api/v1/approvals/pending - 我的待审批列表"""
    return jsonify({
        'success': True,
        'data': {
            'items': [],
            'total': 0,
            'page': 1,
            'page_size': 20,
            'total_pages': 0,
        }
    })


@api_bp.route('/approvals/processed', methods=['GET'])
@require_permission('approval:list')
def get_processed_approvals():
    """GET /api/v1/approvals/processed - 我的已办列表"""
    return jsonify({
        'success': True,
        'data': {
            'items': [],
            'total': 0,
            'page': 1,
            'page_size': 20,
            'total_pages': 0,
        }
    })


@api_bp.route('/approvals/nodes/<int:node_id>/approve', methods=['POST'])
@require_permission('approval:operate')
def approve_node(node_id):
    """POST /api/v1/approvals/nodes/:node_id/approve - 同意审批"""
    data = request.get_json() or {}
    comment = data.get('comment', '')
    return jsonify({
        'success': True,
        'data': {
            'node_id': node_id,
            'action': 'approve',
            'comment': comment,
            'request_status': 'approved',
        }
    })


@api_bp.route('/approvals/nodes/<int:node_id>/reject', methods=['POST'])
@require_permission('approval:operate')
def reject_node(node_id):
    """POST /api/v1/approvals/nodes/:node_id/reject - 驳回审批"""
    data = request.get_json() or {}
    comment = data.get('comment', '')
    return jsonify({
        'success': True,
        'data': {
            'node_id': node_id,
            'action': 'reject',
            'comment': comment,
            'request_status': 'rejected',
        }
    })


@api_bp.route('/approvals/batch', methods=['POST'])
@require_permission('approval:batch')
def batch_approve():
    """POST /api/v1/approvals/batch - 批量审批"""
    data = request.get_json()
    if not data or 'node_ids' not in data or 'action' not in data:
        return jsonify({
            'success': False,
            'error': {'code': 'INVALID_PARAMS', 'message': '缺少 node_ids 或 action'}
        }), 400

    return jsonify({'success': True, 'data': {
        'results': [{'node_id': nid, 'status': 'success'} for nid in data['node_ids']]
    }})


@api_bp.route('/onboarding-requests/<int:request_id>/complete', methods=['POST'])
@require_permission('onboarding:update')
def complete_onboarding(request_id):
    """POST /api/v1/onboarding-requests/:id/complete - 完成入职"""
    return jsonify({
        'success': True,
        'data': {'id': request_id, 'status': 'completed', 'message': '入职流程已完成'}
    })
