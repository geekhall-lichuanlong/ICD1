from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.db import transaction
import json
from .models import UserProfile
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

def index(request):
    return JsonResponse({"code": 200, "msg": "ok"})

def _get_body_data(request):
    """Return dict from form or JSON body."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if request.POST:
            return request.POST
        try:
            return json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            return {}
    return {}

def _get_user_profile(user: User) -> UserProfile:
    """确保用户有对应的 UserProfile。"""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile

def _user_to_dict(user: User):
    """
    前端约定的用户字段：
    username、realName、role（管理员0/普通用户1）、
    phone、createTime、status（禁用0/启用1）、id（主键）
    """
    profile = _get_user_profile(user)
    return {
        "id": user.id,
        "username": user.username,
        "realName": profile.real_name or "",
        "role": profile.role,
        "phone": profile.phone or "",
        "createTime": profile.created_at.isoformat() if profile.created_at else None,
        "status": profile.status,
    }

def me(request):
    if request.user.is_authenticated:
        profile = _get_user_profile(request.user)
        return JsonResponse(
            {
                "code": 200,
                "data": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "role": profile.role,
                },
            }
        )
    return JsonResponse({"code": 401, "msg": "unauthenticated"}, status=401)

# ------------ 千医用户管理接口 ------------

@csrf_exempt
def user_list_create(request):
    """
    GET  用户列表查询接口
        可支持简单分页：page, page_size
    POST 创建用户接口
        字段：username（必填）、realName（必填）、role（必填）、phone、password、confirmPassword
    """
    if request.method == "GET":
        qs = User.objects.all().order_by("id")
        # 简单分页
        try:
            page = int(request.GET.get("page", 1)) # page从1开始
            page_size = int(request.GET.get("page_size", 10))
        except ValueError:
            page, page_size = 1, 10

        start = (page - 1) * page_size
        end = start + page_size
        total = qs.count()
        users = [_user_to_dict(u) for u in qs[start:end]]
        return JsonResponse(
            {
                "code": 200,
                "data": {
                    "userList": users,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
            }
        )

    if request.method == "POST":
        data = _get_body_data(request)
        username = (data.get("username") or "").strip()
        real_name = (data.get("realName") or "").strip()
        phone = (data.get("phone") or "").strip()
        role = data.get("role") # int
        password = data.get("password") or ""
        confirm_password = data.get("confirmPassword") or ""

        if not username or not real_name or role is None:
            return JsonResponse({"code": 400, "msg": "username, realName and role are required"}, status=400)

        try:
            role = int(role)
        except (TypeError, ValueError):
            return JsonResponse({"code": 400, "msg": "role must be 0 or 1"}, status=400)

        if role not in (UserProfile.ROLE_ADMIN, UserProfile.ROLE_USER):
            return JsonResponse({"code": 400, "msg": "role must be 0 or 1"}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({"code": 409, "msg": "username already exists"}, status=409)

        if password or confirm_password:
            if password != confirm_password:
                return JsonResponse({"code": 400, "msg": "passwords do not match"}, status=400)
        else:
            password = "123456"

        # 电话号码必须是数字
        if phone and not phone.isdigit():
            return JsonResponse({"code": 400, "msg": "phone must be digits only"}, status=400)

        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password)
            profile = _get_user_profile(user)
            profile.real_name = real_name
            profile.phone = phone
            profile.role = role
            profile.status = UserProfile.STATUS_ENABLED
            profile.save()

        return JsonResponse({"code": 200, "msg": "User created successfully!", "data": _user_to_dict(user)})

    return JsonResponse({"code": 405, "msg": "Method Not Allowed"}, status=405)


@csrf_exempt
def user_edit(request, pk: int):
    """
    编辑用户接口
        字段：username、realName、role（0/1）、phone、id（主键）
    方法：PUT 或 PATCH
    """
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return JsonResponse({"code": 404, "msg": "User not found."}, status=404)

    if request.method not in ("PUT", "PATCH"):
        return JsonResponse({"code": 405, "msg": "Method Not Allowed"}, status=405)

    data = _get_body_data(request)
    username = (data.get("username") or user.username).strip()
    real_name = data.get("realName")
    phone = (data.get("phone") or "").strip()
    role = data.get("role")

    # username 修改时要校验唯一性
    if username != user.username and User.objects.filter(username=username).exists():
        return JsonResponse({"code": 409, "msg": "username already exists"}, status=409)

    user.username = username
    user.save()

    profile = _get_user_profile(user)
    if real_name is not None:
        profile.real_name = real_name
    if phone is not None:
        profile.phone = phone
    if role is not None:
        try:
            role = int(role)
        except (TypeError, ValueError):
            return JsonResponse({"code": 400, "msg": "role must be 0 or 1"}, status=400)
        if role not in (UserProfile.ROLE_ADMIN, UserProfile.ROLE_USER):
            return JsonResponse({"code": 400, "msg": "role must be 0 or 1"}, status=400)
        profile.role = role
    profile.save()

    return JsonResponse({"code": 200, "msg": "User updated successfully!", "data": _user_to_dict(user)})


@csrf_exempt
def user_status_edit(request, pk: int):
    """
    用户账号状态编辑接口
        字段：id（主键）、status（禁用0/启用1）
    方法：PUT 或 PATCH
    """
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return JsonResponse({"code": 404, "msg": "user not found"}, status=404)

    if request.method not in ("PUT", "PATCH"):
        return JsonResponse({"code": 405, "msg": "Method Not Allowed"}, status=405)

    data = _get_body_data(request)
    status_val = data.get("status") # 0 / 1
    if status_val is None:
        return JsonResponse({"code": 400, "msg": "status is required"}, status=400)

    try:
        status_val = int(status_val)
    except (TypeError, ValueError):
        return JsonResponse({"code": 400, "msg": "status must be 0 or 1"}, status=400)

    if status_val not in (UserProfile.STATUS_DISABLED, UserProfile.STATUS_ENABLED):
        return JsonResponse({"code": 400, "msg": "status must be 0 or 1"}, status=400)

    profile = _get_user_profile(user)
    profile.status = status_val
    profile.save()
    return JsonResponse({"code": 200, "msg": "User status updated successfully!", "data": _user_to_dict(user)})


@csrf_exempt
def user_delete(request, pk: int):
    """
    删除用户接口
        字段：id（主键）
        关键约束：操作不可恢复
    方法：DELETE
    """
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return JsonResponse({"code": 404, "msg": "user not found"}, status=404)

    if request.method != "DELETE":
        return JsonResponse({"code": 405, "msg": "Method Not Allowed"}, status=405)

    # 不可恢复，直接删除
    user.delete()
    return JsonResponse({"code": 200, "msg": "User deleted successfully!"})

@api_view(['POST'])
@permission_classes([IsAuthenticated]) # 关键：只有带了正确 Token 的人才能进
def change_password(request):
    """
    修改密码接口
        字段：id（用户id）、oldPassword（原密码）、newPassword（新密码）、confirmPassword（确认新密码）
    方法：POST
    """
    user = request.user

    old_password = request.data.get("oldPassword")
    new_password = request.data.get("newPassword")
    confirm_password = request.data.get("confirmPassword")

    if not all([old_password, new_password, confirm_password]):
        return JsonResponse({"code": 400, "msg": "oldPassword, newPassword and confirmPassword are required"}, status=400)

    if not user.check_password(old_password):
        return JsonResponse({"code": 400, "msg": "old password is incorrect"}, status=400)

    if new_password != confirm_password:
        return JsonResponse({"code": 400, "msg": "passwords do not match"}, status=400)

    user.set_password(new_password)
    user.save()

    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, user)

    return JsonResponse({"code": 200, "msg": "User password changed successfully!"})