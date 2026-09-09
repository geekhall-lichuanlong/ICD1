from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import ChatSessions, ChatMessages
import json

def _chat_history_to_dict(history):
    return {
        "id": str(history.uuid),  # 关键修改：前端看到的 "id" 实际上是后端的 uuid
        # 如果前端内部逻辑还需要真实ID（例如排序），可以保留一个 internal_id 字段，但不展示给 url
        # "internal_id": history.id, 
        "title": history.title,
        "chat_type": history.chat_type,
        "data": history.data,
        "created_at": history.created_at.isoformat() if history.created_at else None,
        "updated_at": history.updated_at.isoformat() if history.updated_at else None,
    }

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def chat_history_list_create(request):
    """
    GET: 获取当前用户的聊天记录列表 (支持按 chat_type 过滤)
    POST: 创建新的聊天记录
    """
    user = request.user

    if request.method == 'GET':
        chat_type = request.GET.get('chat_type')
        
        # 基础查询：仅限当前用户
        qs = ChatHistory.objects.filter(user=user).order_by('-updated_at')
        
        # 过滤类型
        if chat_type:
            qs = qs.filter(chat_type=chat_type)
            
        # 这里可以加分页逻辑，如果你想保持与 user_list_create 一致
        # 但考虑到聊天记录通常前端一次性加载或无限滚动，这里先返回全量列表
        # 格式遵循项目的统一包装: {"code": 200, "data": [...]}
        data_list = [_chat_history_to_dict(item) for item in qs]
        
        return JsonResponse({
            "code": 200,
            "data": data_list,
            "msg": "ok"
        })

    elif request.method == 'POST':
        # @api_view 已经帮我们解析了 request.data
        data = request.data
        chat_type = data.get('chat_type')
        title = data.get('title', '')
        chat_data = data.get('data', {})

        if not chat_type:
             return JsonResponse({"code": 400, "msg": "chat_type is required"}, status=400)

        # 创建记录
        chat_history = ChatHistory.objects.create(
            user=user,
            chat_type=chat_type,
            title=title,
            data=chat_data
        )

        return JsonResponse({
            "code": 200, 
            "msg": "Created successfully", 
            "data": _chat_history_to_dict(chat_history)
        })

@api_view(['PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def chat_history_detail(request, pk):
    """
    pk: 这里接收的是 UUID 字符串
    PUT/PATCH: 更新聊天记录 (标题或内容)
    DELETE: 删除聊天记录
    """
    try:
        # 尝试通过 uuid 查找
        history = ChatHistory.objects.get(uuid=pk, user=request.user)
    except (ChatHistory.DoesNotExist, ValueError):
        return JsonResponse({"code": 404, "msg": "History not found"}, status=404)


    if request.method in ['PUT', 'PATCH']:
        data = request.data
        
        # 更新字段
        if 'title' in data:
            history.title = data['title']
        if 'data' in data:
            history.data = data['data']
            
        history.save()
        
        return JsonResponse({
            "code": 200, 
            "msg": "Updated successfully", 
            "data": _chat_history_to_dict(history)
        })

    elif request.method == 'DELETE':
        history.delete()
        return JsonResponse({
            "code": 200, 
            "msg": "Deleted successfully"
        })