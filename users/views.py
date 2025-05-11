from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash, login, authenticate
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.utils import timezone
from .forms import UserRegisterForm, UserProfileUpdateForm, CustomPasswordChangeForm, AccountAppealForm, CustomAuthenticationForm
from .models import AccountAppeal
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
    authentication_form = CustomAuthenticationForm
    
    def form_valid(self, form):
        user = form.get_user()
        if not user.is_active:
            # Store user info in session for the appeal process without logging in
            self.request.session['suspended_user_id'] = user.id
            
            # Check if user has a pending appeal
            has_pending_appeal = AccountAppeal.objects.filter(user=user, status='pending').exists()
            if has_pending_appeal:
                messages.warning(self.request, 'Your account has been suspended. You have a pending appeal.')
            else:
                messages.warning(self.request, 'Your account has been suspended. Please submit an appeal to reactivate your account.')
            
            return redirect('submit-appeal')
        
        response = super().form_valid(form)
        if self.request.user.is_staff:
            return redirect('admin-dashboard')
        return response

def submit_appeal(request):
    # Get suspended user from session if available
    suspended_user_id = request.session.get('suspended_user_id')
    suspended_user = None
    
    if suspended_user_id:
        try:
            suspended_user = User.objects.get(id=suspended_user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('login')
    
    # For users who aren't logged in and don't have a session, show a form to identify themselves
    if not suspended_user and not request.user.is_authenticated:
        if request.method == 'POST' and 'username' in request.POST:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None and not user.is_active:
                # Store user in session for the appeal process
                request.session['suspended_user_id'] = user.id
                return redirect('submit-appeal')
            else:
                messages.error(request, 'Invalid username or password, or account is not suspended.')
                
        # Show a form to identify the suspended user
        return render(request, 'users/identify_suspended.html')
    
    # If user is logged in but active, redirect home
    if not suspended_user and request.user.is_authenticated and request.user.is_active:
        return redirect('home')
    
    # Use either the suspended user from session or the authenticated user
    user = suspended_user or request.user
    
    # Get the most recent system-generated appeal (created during suspension)
    recent_suspension = AccountAppeal.objects.filter(
        user=user, 
        reason__startswith="SYSTEM:"
    ).order_by('-created_at').first()
    
    if request.method == 'POST':
        form = AccountAppealForm(request.POST)
        if form.is_valid():
            appeal = form.save(commit=False)
            appeal.user = user
            appeal.save()
            messages.success(request, 'Your appeal has been submitted. We will review it shortly.')
            
            # Clear the session data
            if 'suspended_user_id' in request.session:
                del request.session['suspended_user_id']
                
            return redirect('login')
    else:
        form = AccountAppealForm()
    
    # Get user's previous appeals (user-submitted, not system-generated)
    previous_appeals = AccountAppeal.objects.filter(
        user=user,
        reason__startswith=False
    ).order_by('-created_at')
    
    context = {
        'form': form,
        'previous_appeals': previous_appeals,
        'username': user.username,
        'recent_suspension': recent_suspension
    }
    return render(request, 'users/submit_appeal.html', context)

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
    
    # Add pending appeals and recent appeals
    pending_appeals = AccountAppeal.objects.filter(status='pending').count()
    recent_appeals = AccountAppeal.objects.all().order_by('-created_at')[:5]
    
    context = {
        'total_videos': total_videos,
        'total_users': total_users,
        'pending_reports': pending_reports,
        'total_comments': total_comments,
        'recent_videos': recent_videos,
        'recent_reports': recent_reports,
        'pending_appeals': pending_appeals,
        'recent_appeals': recent_appeals,
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
        elif action == 'suspend':
            # Get the suspension reason and notes
            suspension_reason = request.POST.get('suspension_reason', 'Violation of Community Guidelines')
            suspension_notes = request.POST.get('suspension_notes', '')
            
            # Get the video author
            author = report.video.author
            
            # Suspend the author (deactivate the account)
            author.is_active = False
            author.save()
            
            # Create an appeal record with the suspension reason
            AccountAppeal.objects.create(
                user=author,
                reason="SYSTEM: " + suspension_reason,  # Combine the system indicator with the reason
                status="pending",
                admin_response=f"Your account has been suspended. Reason: {suspension_reason}. Notes: {suspension_notes}"
            )
            
            # Mark the report as action taken
            report.status = 'action_taken'
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save()
            
            # Create a notification for the suspended user - remove the 'type' parameter
            Notification.objects.create(
                recipient=author,
                sender=request.user,
                content=f"Your account has been suspended. Reason: {suspension_reason}"
            )
            
            messages.success(request, f'Author {author.username} has been suspended and report has been processed.')
        
        return redirect('manage-reports')
    
    context = {
        'report': report,
        'active_tab': 'reports'
    }
    return render(request, 'videos/handle_report.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_appeals(request):
    appeals = AccountAppeal.objects.all().order_by('-created_at')
    
    # Calculate counts for the dashboard
    pending_count = AccountAppeal.objects.filter(status='pending').count()
    approved_count = AccountAppeal.objects.filter(status='approved').count()
    rejected_count = AccountAppeal.objects.filter(status='rejected').count()
    
    if request.method == 'POST':
        appeal_id = request.POST.get('appeal_id')
        action = request.POST.get('action')
        admin_response = request.POST.get('admin_response')
        
        if appeal_id and action:
            appeal = get_object_or_404(AccountAppeal, id=appeal_id)
            
            if action == 'approve':
                appeal.status = 'approved'
                appeal.admin_response = admin_response
                appeal.save()
                
                # Reactivate the user's account
                user = appeal.user
                user.is_active = True
                user.save()
                
                # Create a notification for the user - remove the 'type' parameter
                Notification.objects.create(
                    recipient=user,
                    sender=request.user,
                    content=f"Your account appeal has been approved. Your account has been reactivated."
                )
                
                messages.success(request, f'Appeal approved and account reactivated for {user.username}')
            
            elif action == 'reject':
                appeal.status = 'rejected'
                appeal.admin_response = admin_response
                appeal.save()
                
                # Create a notification for the user - remove the 'type' parameter
                Notification.objects.create(
                    recipient=appeal.user,
                    sender=request.user,
                    content=f"Your account appeal has been rejected: {admin_response}"
                )
                
                messages.success(request, f'Appeal rejected for {appeal.user.username}')
            
            return redirect('admin-appeals')
    
    context = {
        'appeals': appeals,
        'active_tab': 'appeals',
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'users/admin_appeals.html', context)
