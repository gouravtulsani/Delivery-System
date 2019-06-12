from django.contrib import admin

# Register your models here.

from .models import Tasks, UserProfile


admin.site.register(Tasks)
admin.site.register(UserProfile)
