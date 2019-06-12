from django.shortcuts import render
import asyncio
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny
)
from rest_framework.decorators import (
    api_view,
    permission_classes
)
from .models import (
    UserProfile,
    Tasks,
    TaskStateHistory,
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async
import json


PRIORITY_CHOICES = {
    'low': 1,
    'medium': 2,
    'high': 3,
}
STATE_CHOICES = {
    'new': 1,
    'accepted': 2,
    'completed': 3,
    'declined': 4,
    'cancelled': 5,
}
USER_TYPE_CHOICES = {
    'manager': 1,
    'rider': 2,
}
# Create your views here.
def _update_state(data, user, task):
    err_resp = {"error": 'Invalid state Transaction'}
    if data['state'] == 'accepted' and \
       task.state != STATE_CHOICES['new']:
        return Response(err_resp, status=status.HTTP_400_BAD_REQUEST)

    if data['state'] == 'completed' and \
       task.state != STATE_CHOICES['accepted']:
        return Response(err_resp, status=status.HTTP_400_BAD_REQUEST)

    if data['state'] == 'declined' and \
       task.state != STATE_CHOICES['accepted']:
        return Response(err_resp, status=status.HTTP_400_BAD_REQUEST)

    if data['state'] == 'cancelled' and \
       task.state != STATE_CHOICES['new']:
        return Response(err_resp, status=status.HTTP_400_BAD_REQUEST)

    if data['state'] == 'accepted':
        pending_tasks = Tasks.objects.filter(served_by=user).count()
        if pending_tasks > MAX_PENDING_TASKS:
            return Response(
                {'error': f'cannot except more than {MAX_PENDING_TASKS}.'},
                status = status.HTTP_400_BAD_REQUEST,
            )

    task.state = STATE_CHOICES[data['state']]
    if data['state'] == 'accepted':
        task.served_by = user

        channel_layer = get_channel_layer()
        sync_to_async(channel_layer.group_send)("delivery_task", {
            "type": "websocket.send",
            "text": json.dumps(_fetch_new_task())
        })

    task.save()
    TaskStateHistory.objects.create(
        task_id = task,
        state = task.state,
    )
    return Response({'status': 'success'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def add_task(request):
    user = UserProfile.objects.get(user=request.user)
    if user.user_type != USER_TYPE_CHOICES['manager']:
        return Response(
            {'error': 'not allowed'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if hasattr(request.data, 'dict'):
        data = request.data.dict()
    else:
        data = request.data

    if not 'title' in data:
        return Response(
            {'error': 'Title not supplied'},
            status = status.HTTP_400_BAD_REQUEST,
        )
    if 'priority' not in data:
        data['priority'] = 'low'
    elif data['priority'] not in PRIORITY_CHOICES.keys():
        return Response(
            {'error': 'priority: invalid choice'},
            status = status.HTTP_400_BAD_REQUEST,
        )

    task = Tasks.objects.create(
        created_by=user,
        title=data['title'],
        priority=PRIORITY_CHOICES[data['priority']],
        state=1
    )

    channel_layer = get_channel_layer()
    sync_to_async(channel_layer.group_send)(
        "delivery_task", {
            "type": "taks_details",
            "text": json.dumps(_fetch_new_task()),
        }
    )

    return Response({'status': 'Added.!'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def update_task(request):
    if hasattr(request.data, 'dict'):
        data = request.data.dict()
    else:
        data = request.data
    if "task_id" not in data:
        return Response(
            {'error': 'task_id: required field'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if 'state' not in data:
        return Response(
            {'error': 'state: field not defined'},
            status=status.HTTP_400_BAD_REQUEST
        )
    elif data['state'] not in STATE_CHOICES.keys() or data['state'] == 'new':
        return Response(
            {'error': 'state: Invalid choice'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = Tasks.objects.get(id=data['task_id'])
    except DoesNotExist:
        resp = {'error': f"task_id: {data['task_id']} not found"}
        return Response(resp, status=status.HTTP_404_NOT_FOUND)

    err_resp = {'error': 'Not allowed'}

    user = UserProfile.objects.get(user=request.user)
    if data['state'] in ['accepted', 'completed', 'declined']:
        if user.user_type == USER_TYPE_CHOICES['manager']:
            return Response(
                err_resp,
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return _update_state(data, user, task)

    if data['state'] == ['declined', 'cancelled']:
        if user.user_type == USER_TYPE_CHOICES['manager']:
            return Response(
                err_resp,
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return _update_state(data, user, task)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def view_tasks_list(request):
    resp = {'result': []}
    user = UserProfile.objects.get(user=request.user)
    data = Tasks.objects.filter(Q(created_by=user)|Q(served_by=user))
    for row in data:
        resp['result'].append({
            'task_id': row.id,
            'title': row.title,
            'priority': row.get_priority_display(),
            'state': row.get_state_display(),
            'created_at': row.created_at,
            'created_by': row.created_by.user.username
        })
    return Response(resp, status=status.HTTP_200_OK)

def _fetch_new_task():
    new_task = Tasks.objects.filter(
        state=STATE_CHOICES['new']
    ).order_by('-priority', 'id').first()
    if not new_task:
        return {"message": "No new task"}
    return {
        "task_id": new_task.id,
        "title": new_task.title,
        "priority": new_task.priority,
        "created_by": new_task.created_by.user.username,
        "created_at": str(new_task.created_at),
    }

@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def fetch_new_task(request):
    user = UserProfile.objects.get(user=request.user)
    if user.user_type == USER_TYPE_CHOICES['manager']:
        return Response(
            {'error': 'Not allowed'},
            status=status.HTTP_400_BAD_REQUEST
        )

    new_task = _fetch_new_task()
    return Response(new_task, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes((AllowAny,))
def login(request):
    resp={}
    username = request.data.get('username', None)
    password = request.data.get('password', None)
    user = authenticate(request, username=username, password=password)
    if user is None:
        resp["status"] = 'Unauthorized user'
        return Response(resp, status=status.HTTP_401_UNAUTHORIZED)

    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)

    resp['status'] = 'login successfully'
    resp['token'] = token.key
    resp['username'] = token.user.username

    return render(request, 'login.html', resp)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def logout(request):
    user=request.user

    if Token.objects.filter(user=user).exists():
        Token.objects.filter(user=user).delete()

    resp = {'status': 'logout'}

    return Response(resp, status=status.HTTP_200_OK)

