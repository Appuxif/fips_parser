from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
    # Удалено на шаге 68
    # path('login/', views.LoginView.as_view(), name='login'),

    # Добавлено на шаге 68
    # path('login/', auth_views.LoginView.as_view(), name='login'),
    # path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # # Добавлено на 81 шаге
    # path('register/', views.register, name='register'),
    # # Добавлено на 92 шаге
    # path('edit/', views.edit, name='edit'),
    # # Добавлено на 94 шаге
    # path('password-change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    # path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    # # Добавлено на 98 шаге
    # path('pass-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    # path('pass-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    # path('pass-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    # path('pass-reset/complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
