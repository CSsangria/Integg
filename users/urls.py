from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('submit-appeal/', views.submit_appeal, name='submit-appeal'),
    path('appeal-submitted/', views.appeal_submitted, name='appeal-submitted'),
    path('admin/appeals/', views.admin_appeals, name='admin-appeals'),
] 