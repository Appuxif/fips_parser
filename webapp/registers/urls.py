from django.urls import path

from . import views


app_name = 'registers'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    # path('list/', views.TasksListView.as_view(), name='list'),
    # path('create/', views.CreateTaskView2.as_view(), name='create'),
    # path('delete/<int:pk>/', views.DeleteTaskView.as_view(), name='delete'),
    # path('complete/<int:pk>/', views.CompleteView.as_view(), name='complete'),
    # path('details/<int:pk>/', views.TaskDetailsView.as_view(), name='details'),
    # path('edit/<int:pk>/', views.TaskEditView.as_view(), name='edit'),
    # path('export/', views.TaskExportView.as_view(), name='export'),
    # path('list/tag/<slug:slug>', views.TasksListView.as_view(), name='tagged_list'),
]
