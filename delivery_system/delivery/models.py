from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        (1, 'manager'),
        (2, 'rider'),
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="user"
    )
    store_name = models.CharField(max_length=50)
    user_type = models.IntegerField(choices=USER_TYPE_CHOICES, default=2)
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )


class Tasks(models.Model):
    PRIORITY_CHOICES = (
        (1, 'low'),
        (2, 'medium'),
        (3, 'high'),
    )
    STATE_CHOICES = (
        (1, 'new'),
        (2, 'accepted'),
        (3, 'completed'),
        (4, 'declined'),
        (5, 'cancelled'),
    )

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1)
    state = models.IntegerField(choices=STATE_CHOICES, default=1)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name='manager'
    )
    served_by = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name='rider', null=True
    )

    class meta:
        ordering = ['-priority', 'id']


class TaskStateHistory(models.Model):
    STATE_CHOICES = (
        (1, 'new'),
        (2, 'accepted'),
        (3, 'completed'),
        (4, 'declined'),
        (5, 'cancelled'),
    )

    task_id = models.ForeignKey(Tasks, on_delete=models.CASCADE, related_name='task')
    state = models.IntegerField(
        choices=STATE_CHOICES,
        default=1
    )
    updated_on = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
