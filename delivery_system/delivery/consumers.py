import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from delivery.models import Tasks
from delivery.views import STATE_CHOICES


class DeliveryConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        await self.channel_layer.group_add("delivery_task", self.channel_name)

        await self.send({
            "type": "websocket.accept",
        })

    async def websocket_disconnect(self, event):
        await self.channel_layer.group_discard(
            "delivery_task", self.channel_name)

    async def websocket_receive(self, event):
        print(event)
        tasks = {}
        text = event.get('text', None)
        if text is not None:
            print(text)
            text = json.loads(text)
            import ipdb; ipdb.set_trace()
            if text['type'] == "get_new_task":
                tasks = await self.get_new_task()
                await self.channel_layer.group_send(
                    "delivery_task",
                        {
                            "type": "task_details",
                            "text": json.dumps(tasks)
                        }
                    )
            if text['type'] == "cancelled_task":
                task_id = text['task_id']

                tasks = await self.fetch_cancelled_task(task_id)
                await self.send({
                        "type": "websocket.send",
                        "text": json.dumps(tasks)
                })

    async def send_alert(self, event):
        await self.send({
            "type": "alert",
            "text": event["text"]
        })

    async def task_details(self, event):
        await self.send({
            "type": "websocket.send",
            "text": event["text"]
        })

    @database_sync_to_async
    def get_new_task(self):
        new_task = Tasks.objects.filter(
            state=STATE_CHOICES['new']
        ).order_by('-priority', 'id').first()
        if not new_task:
            resp = {'message': 'No new task'},
            return resp
        resp = {
            'task_id': new_task.id,
            'title': new_task.title,
            'priority': new_task.get_priority_display(),
            'created_by': new_task.created_by.user.username,
            'created_at': str(new_task.created_at),
        }
        return resp

    @database_sync_to_async
    def fetch_cancelled_task(self, task_id):
        task = Tasks.objects.get(id=task_id)
        resp = {
            'task_id': task.id,
            'title': task.title,
            'state': task.get_state_display(),
        }
        return resp
