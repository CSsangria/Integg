from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash, login
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.utils import timezone
from .forms import UserRegisterForm, UserProfileUpdateForm, CustomPasswordChangeForm
from videos.models import Video, Comment, Notification, VideoReport

# Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'users/profile.html')

@login_required
def settings(request):
    profile_form = UserProfileUpdateForm(instance=request.user.userprofile)
    password_form = CustomPasswordChangeForm(request.user)
    
    if request.method == 'POST':
        if 'profile_submit' in request.POST:
            profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user.userprofile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile has been updated!')
                return redirect('settings')
        
        elif 'password_submit' in request.POST:
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Important to keep the user logged in
                messages.success(request, 'Your password was successfully updated!')
                return redirect('settings')
            else:
                messages.error(request, 'Please correct the error below.')
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'profile': request.user.userprofile
    }
    return render(request, 'users/settings.html', context)

class CustomLoginView(LoginView):
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.user.is_staff:
            return redirect('admin-dashboard')
        return response

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    # Get statistics for the dashboard
    total_videos = Video.objects.count()
    total_users = User.objects.count()
    pending_reports = VideoReport.objects.filter(status='pending').count()
    total_comments = Comment.objects.count()
    
    # Get recent videos and reports
    recent_videos = Video.objects.all().order_by('-date_posted')[:5]
    recent_reports = VideoReport.objects.filter(status='pending').order_by('-created_at')[:5]
    
    context = {
        'total_videos': total_videos,
        'total_users': total_users,
        'pending_reports': pending_reports,
        'total_comments': total_comments,
        'recent_videos': recent_videos,
        'recent_reports': recent_reports,
        'active_tab': 'dashboard'
    }
    return render(request, 'videos/admin_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_videos(request):
    videos = Video.objects.all().order_by('-date_posted')
    context = {
        'videos': videos,
        'active_tab': 'videos'
    }
    return render(request, 'videos/admin_videos.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_users(request):
    users = User.objects.all().order_by('-date_joined')
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                if action == 'deactivate':
                    user.is_active = False
                    user.save()
                    messages.success(request, f'User {user.username} deactivated.')
                elif action == 'activate':
                    user.is_active = True
                    user.save()
                    messages.success(request, f'User {user.username} activated.')
                elif action == 'delete':
                    user.delete()
                    messages.success(request, f'User deleted.')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
        return redirect('admin-users')
    context = {
        'users': users,
        'active_tab': 'users'
    }
    return render(request, 'videos/admin_users.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_comments(request):
    comments = Comment.objects.all().order_by('-date_posted')
    if request.method == 'POST':
        action = request.POST.get('action')
        comment_id = request.POST.get('comment_id')
        if comment_id:
            try:
                comment = Comment.objects.get(id=comment_id)
                if action == 'delete':
                    comment.delete()
                    messages.success(request, 'Comment deleted.')
            except Comment.DoesNotExist:
                messages.error(request, 'Comment not found.')
        return redirect('admin-comments')
    context = {
        'comments': comments,
        'active_tab': 'comments'
    }
    return render(request, 'videos/admin_comments.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_notifications(request):
    notifications = Notification.objects.all().order_by('-created_at')
    if request.method == 'POST':
        action = request.POST.get('action')
        notification_id = request.POST.get('notification_id')
        if notification_id:
            try:
                notification = Notification.objects.get(id=notification_id)
                if action == 'mark_read':
                    notification.is_read = True
                    notification.save()
                    messages.success(request, 'Notification marked as read.')
                elif action == 'delete':
                    notification.delete()
                    messages.success(request, 'Notification deleted.')
            except Notification.DoesNotExist:
                messages.error(request, 'Notification not found.')
        return redirect('admin-notifications')
    context = {
        'notifications': notifications,
        'active_tab': 'notifications'
    }
    return render(request, 'videos/admin_notifications.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def manage_reports(request):
    reports = VideoReport.objects.filter(status='pending').order_by('-created_at')
    context = {
        'reports': reports,
        'active_tab': 'reports'
    }
    return render(request, 'videos/manage_reports.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def handle_report(request, pk):
    report = get_object_or_404(VideoReport, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'dismiss':
            report.status = 'reviewed'
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save()
            messages.success(request, 'Report has been dismissed.')
        elif action == 'delete':
            report.video.delete()
            report.status = 'action_taken'
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save()
            messages.success(request, 'Video has been deleted.')
        
        return redirect('manage-reports')
    
    context = {
        'report': report,
        'active_tab': 'reports'
    }
    return render(request, 'videos/handle_report.html', context)
