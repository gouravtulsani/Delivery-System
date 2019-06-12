from django.urls import path

from . import views

urlpatterns = [
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),

    path('add_task', views.add_task, name='add_task'),
    path('update_task', views.update_task, name='update_task'),
    path('view_tasks', views.view_tasks_list, name='view_task_list'),
    path('get_new_task', views.fetch_new_task, name='fetch_new_task'),
]
