"""通知模块API"""
from flask import request, jsonify, g
from . import api_bp
from notifications.notification_manager import NotificationManager
from auth.permission_checker import require_permission
from utils.exceptions import AppException


notification_manager = NotificationManager()


@api_bp.route('/notifications', methods=['GET'])
@require_permission('notification:list')
def list_notifications():
    """GET /api/v1/notifications - 获取通知列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    result = notification_manager.get_notifications(
        recipient_id=str(getattr(g, 'current_user_id', 0)),
        page=page, page_size=page_size,
        is_read=False if unread_only else None,
    )
    return jsonify({'success': True, 'data': result})


@api_bp.route('/notifications/unread-count', methods=['GET'])
@require_permission('notification:list')
def get_unread_count():
    """GET /api/v1/notifications/unread-count - 未读数"""
    count = notification_manager.get_unread_count(
        recipient_id=str(getattr(g, 'current_user_id', 0))
    )
    return jsonify({'success': True, 'data': count})


@api_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@require_permission('notification:read')
def mark_as_read(notification_id):
    """POST /api/v1/notifications/:id/read - 标记已读"""
    try:
        notif = notification_manager.mark_as_read(
            notification_id, recipient_id=str(getattr(g, 'current_user_id', 0))
        )
        if notif:
            return jsonify({'success': True, 'data': notif})
        return jsonify({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': '通知不存在或无权操作'}
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {'code': 'BUSINESS_ERROR', 'message': str(e)}
        }), 400


@api_bp.route('/notifications/batch-read', methods=['POST'])
@require_permission('notification:read')
def batch_mark_read():
    """POST /api/v1/notifications/batch-read - 批量标记已读"""
    data = request.get_json()
    if not data or 'notification_ids' not in data:
        return jsonify({
            'success': False,
            'error': {'code': 'INVALID_PARAMS', 'message': '缺少 notification_ids'}
        }), 400

    count = notification_manager.batch_mark_as_read(
        data['notification_ids'],
        recipient_id=str(getattr(g, 'current_user_id', 0)),
    )
    return jsonify({'success': True, 'data': {'marked_count': count}})
