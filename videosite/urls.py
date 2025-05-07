"""
URL configuration for videosite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from users import views as user_views

urlpatterns = [
    # Custom admin dashboard URLs
    path('admin/dashboard/', user_views.admin_dashboard, name='admin-dashboard'),
    path('admin/videos/', user_views.admin_videos, name='admin-videos'),
    path('admin/users/', user_views.admin_users, name='admin-users'),
    path('admin/comments/', user_views.admin_comments, name='admin-comments'),
    path('admin/notifications/', user_views.admin_notifications, name='admin-notifications'),
    path('admin/reports/', user_views.manage_reports, name='manage-reports'),
    path('admin/reports/<int:pk>/handle/', user_views.handle_report, name='handle-report'),
    
    # Django admin URLs
    path('admin/', admin.site.urls),
    
    # Other URLs
    path('', include('videos.urls')),
    path('register/', user_views.register, name='register'),
    path('profile/', user_views.profile, name='profile'),
    path('settings/', user_views.settings, name='settings'),
    path('login/', user_views.CustomLoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
