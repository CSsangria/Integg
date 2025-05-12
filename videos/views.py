from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Video, Comment, Subscription, Notification, VideoReport, WatchHistory, SavedVideo
from users.models import AccountAppeal
from .forms import VideoForm, CommentForm, VideoReportForm
from django.http import JsonResponse
from django.db.models import F, Sum, Q, Count
import json
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
import datetime

def home(request):
    # Get latest landscape videos only
    latest_videos = Video.objects.filter(orientation='landscape').order_by('-date_posted')[:8]
    
    # Get popular landscape videos only (based on views)
    popular_videos = Video.objects.filter(orientation='landscape').order_by('-views')[:8]
    
    # Get featured landscape video (most viewed video)
    featured_video = Video.objects.filter(orientation='landscape').order_by('-views').first()
    
    # If user is authenticated, get recently watched, liked and saved videos
    watch_history = []
    liked_videos = []
    saved_videos = []
    
    if request.user.is_authenticated:
        watch_history = WatchHistory.objects.filter(user=request.user).select_related('video')[:5]
        liked_videos = Video.objects.filter(likes=request.user)[:5]
        saved_videos = SavedVideo.objects.filter(user=request.user).select_related('video')[:5]
    
    context = {
        'latest_videos': latest_videos,
        'popular_videos': popular_videos,
        'featured_video': featured_video,
        'watch_history': watch_history,
        'liked_videos': liked_videos,
        'saved_videos': saved_videos,
    }
    return render(request, 'videos/home.html', context)

class VideoDetailView(DetailView):
    model = Video

    def get_object(self):
        # Get the video object
        video = super().get_object()
        # Increment the view count using F() to avoid race conditions
        Video.objects.filter(pk=video.pk).update(views=F('views') + 1)
        # Refresh the video object to get the updated view count
        video.refresh_from_db()
        
        # Add to watch history if user is authenticated
        if self.request.user.is_authenticated:
            WatchHistory.objects.update_or_create(
                user=self.request.user,
                video=video,
                defaults={'watched_at': timezone.now()}
            )
            
        return video

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        
        # Add whether the video is saved by the current user
        if self.request.user.is_authenticated:
            context['is_saved'] = SavedVideo.objects.filter(
                user=self.request.user, 
                video=self.object
            ).exists()
        else:
            context['is_saved'] = False
            
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.video = self.object
            comment.author = request.user
            comment.save()

            # Create notification for video owner if it's not their own comment
            if self.object.author != request.user:
                try:
                    notification = Notification.objects.create(
                        recipient=self.object.author,
                        sender=request.user,
                        notification_type='comment',
                        content=f"{request.user.username} commented on your video: {self.object.title}",
                        video=self.object,
                        comment=comment
                    )
                    print(f"Notification created successfully: {notification.id}")
                    print(f"Notification type: {notification.notification_type}")
                    print(f"Recipient: {notification.recipient.username}")
                except Exception as e:
                    print(f"Error creating notification: {str(e)}")

            return redirect('video-detail', pk=self.object.pk)
        return self.get(request, *args, **kwargs)

class VideoCreateView(LoginRequiredMixin, CreateView):
    model = Video
    form_class = VideoForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

class VideoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Video
    form_class = VideoForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        video = self.get_object()
        return self.request.user == video.author

class VideoDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Video
    success_url = reverse_lazy('home')

    def test_func(self):
        video = self.get_object()
        return self.request.user == video.author

@login_required
def like_video(request, pk):
    video = get_object_or_404(Video, pk=pk)
    if request.user in video.likes.all():
        video.likes.remove(request.user)
        liked = False
    else:
        video.likes.add(request.user)
        liked = True
    return JsonResponse({'liked': liked, 'total_likes': video.total_likes()})

def get_video_comments(request, pk):
    video = get_object_or_404(Video, pk=pk)
    comments = video.comments.filter(is_reply=False).order_by('-date_posted')
    comments_data = []
    
    for comment in comments:
        # Get replies for this comment
        replies = comment.replies.all().order_by('date_posted')
        replies_data = []
        
        for reply in replies:
            reply_data = {
                'id': reply.id,
                'content': reply.content,
                'author': reply.author.username,
                'author_profile_picture': reply.author.userprofile.profile_picture.url if hasattr(reply.author, 'userprofile') else None,
                'date_posted': reply.date_posted.isoformat(),
                'likes_count': reply.total_likes(),
                'is_liked': request.user in reply.likes.all() if request.user.is_authenticated else False,
            }
            replies_data.append(reply_data)
        
        comment_data = {
            'id': comment.id,
            'content': comment.content,
            'author': comment.author.username,
            'author_profile_picture': comment.author.userprofile.profile_picture.url if hasattr(comment.author, 'userprofile') else None,
            'date_posted': comment.date_posted.isoformat(),
            'likes_count': comment.total_likes(),
            'is_liked': request.user in comment.likes.all() if request.user.is_authenticated else False,
            'replies': replies_data
        }
        comments_data.append(comment_data)
    
    return JsonResponse({'comments': comments_data})

@login_required
def like_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        if request.user in comment.dislikes.all():
            comment.dislikes.remove(request.user)
        liked = True
    return JsonResponse({
        'liked': liked,
        'total_likes': comment.total_likes(),
        'total_dislikes': comment.total_dislikes()
    })

@login_required
def dislike_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user in comment.dislikes.all():
        comment.dislikes.remove(request.user)
        disliked = False
    else:
        comment.dislikes.add(request.user)
        if request.user in comment.likes.all():
            comment.likes.remove(request.user)
        disliked = True
    return JsonResponse({
        'disliked': disliked,
        'total_likes': comment.total_likes(),
        'total_dislikes': comment.total_dislikes()
    })

@login_required
def subscribe(request, username):
    user_to_subscribe = get_object_or_404(User, username=username)
    
    if request.user != user_to_subscribe:
        subscription, created = Subscription.objects.get_or_create(
            subscriber=request.user,
            subscribed_to=user_to_subscribe
        )
        
        if not created:
            # If subscription existed, delete it (unsubscribe)
            subscription.delete()
            subscribed = False
        else:
            subscribed = True
            # Create notification for new subscriber
            Notification.objects.create(
                recipient=user_to_subscribe,
                sender=request.user,
                notification_type='subscriber',
                content=f"{request.user.username} subscribed to your channel"
            )
            
        return JsonResponse({
            'subscribed': subscribed,
            'subscriber_count': user_to_subscribe.subscribers.count()
        })
    return JsonResponse({'error': 'Cannot subscribe to yourself'}, status=400)

def user_dashboard(request, username):
    profile_user = get_object_or_404(User, username=username)
    videos = Video.objects.filter(author=profile_user).order_by('-date_posted')
    
    # Check if the current user is subscribed to the profile user
    is_subscribed = False
    if request.user.is_authenticated:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user,
            subscribed_to=profile_user
        ).exists()
    
    context = {
        'profile_user': profile_user,
        'videos': videos,
        'is_subscribed': is_subscribed,
    }
    return render(request, 'videos/user_dashboard.html', context)

def shorts(request):
    # Check if a specific video is requested
    video_id = request.GET.get('video')
    
    # Get portrait videos ordered by date
    portrait_videos = Video.objects.filter(orientation='portrait').order_by('-date_posted')
    
    # If a specific video is requested, ensure it's at the beginning of the list
    if video_id:
        try:
            # Try to get the requested video
            requested_video = Video.objects.get(pk=video_id)
            
            # If it's not a portrait video, redirect to video detail
            if requested_video.orientation != 'portrait':
                return redirect('video-detail', pk=video_id)
                
            # Check if video is already in the portrait_videos queryset
            if requested_video in portrait_videos:
                # Remove it from its current position and add it at the beginning
                portrait_videos = [requested_video] + [v for v in portrait_videos if v.pk != requested_video.pk]
            else:
                # Add it at the beginning (this might happen if it's not a portrait video)
                portrait_videos = [requested_video] + list(portrait_videos)
        except Video.DoesNotExist:
            # Video not found, ignore the parameter
            pass
    
    context = {
        'videos': portrait_videos,
        'page_title': 'Shorts'
    }
    return render(request, 'videos/shorts.html', context)

@login_required
def add_comment(request, pk):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            content = data.get('content')
            if content:
                video = get_object_or_404(Video, pk=pk)
                comment = Comment.objects.create(
                    content=content,
                    video=video,
                    author=request.user,
                    is_reply=False
                )

                # Debug logging
                print(f"Video author: {video.author.username}")
                print(f"Comment author: {request.user.username}")
                print(f"Creating notification for video {video.id}")

                # Create notification for video owner if it's not their own comment
                if video.author != request.user:
                    try:
                        notification = Notification.objects.create(
                            recipient=video.author,
                            sender=request.user,
                            notification_type='comment',
                            content=f"{request.user.username} commented on your video: {video.title}",
                            video=video,
                            comment=comment
                        )
                        print(f"Notification created successfully: {notification.id}")
                        print(f"Notification type: {notification.notification_type}")
                        print(f"Recipient: {notification.recipient.username}")
                    except Exception as e:
                        print(f"Error creating notification: {str(e)}")

                return JsonResponse({
                    'success': True,
                    'comment': {
                        'id': comment.id,
                        'content': comment.content,
                        'author': comment.author.username,
                        'author_profile_picture': comment.author.userprofile.profile_picture.url if hasattr(comment.author, 'userprofile') else None,
                        'date_posted': comment.date_posted.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                        'likes_count': 0,
                        'is_liked': False
                    }
                })
            return JsonResponse({'success': False, 'error': 'Content is required'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@login_required
def reply_comment(request, pk):
    parent_comment = get_object_or_404(Comment, pk=pk)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            content = data.get('content')
            if content:
                reply = Comment.objects.create(
                    content=content,
                    video=parent_comment.video,
                    author=request.user,
                    parent=parent_comment,
                    is_reply=True
                )
                
                # Create notification for the parent comment author if it's not their own reply
                if parent_comment.author != request.user:
                    Notification.objects.create(
                        recipient=parent_comment.author,
                        sender=request.user,
                        notification_type='reply',
                        content=f"{request.user.username} replied to your comment",
                        video=parent_comment.video,
                        comment=reply
                    )
                
                return JsonResponse({
                    'success': True,
                    'reply': {
                        'id': reply.id,
                        'content': reply.content,
                        'author': reply.author.username,
                        'author_profile_picture': reply.author.userprofile.profile_picture.url,
                        'date_posted': reply.date_posted.strftime('%B %d, %Y'),
                        'likes': 0,
                        'dislikes': 0
                    }
                })
            return JsonResponse({'success': False, 'error': 'Content is required'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@login_required
def get_notifications(request):
    notifications = request.user.notifications.all()[:20]  # Get last 20 notifications
    notifications_data = []
    
    print(f"Found {notifications.count()} notifications for user {request.user.username}")
    
    for notification in notifications:
        print(f"Processing notification: {notification.id}, type: {notification.notification_type}")
        notification_data = {
            'id': notification.id,
            'type': notification.notification_type,
            'content': notification.content,
            'sender': {
                'username': notification.sender.username,
                'profile_picture': notification.sender.userprofile.profile_picture.url if hasattr(notification.sender, 'userprofile') else None
            },
            'video_id': notification.video.id if notification.video else None,
            'comment_id': notification.comment.id if notification.comment else None,
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%B %d, %Y %H:%M')
        }
        notifications_data.append(notification_data)
    
    print(f"Returning {len(notifications_data)} notifications")
    return JsonResponse({'notifications': notifications_data})

@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})

@login_required
def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})

@login_required
def report_video(request, pk):
    video = get_object_or_404(Video, pk=pk)
    
    # Check if user has already reported this video
    if VideoReport.objects.filter(video=video, reporter=request.user).exists():
        messages.warning(request, 'You have already reported this video.')
        return redirect('video-detail', pk=pk)
    
    if request.method == 'POST':
        form = VideoReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.video = video
            report.reporter = request.user
            report.save()
            messages.success(request, 'Your report has been submitted successfully.')
            return redirect('video-detail', pk=pk)
    else:
        form = VideoReportForm()
    
    context = {
        'form': form,
        'video': video,
    }
    return render(request, 'videos/report_video.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def manage_reports(request):
    reports = VideoReport.objects.filter(status='pending').order_by('-created_at')
    context = {
        'reports': reports,
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
    }
    return render(request, 'videos/handle_report.html', context)

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
    
    # For Content Distribution Chart
    landscape_videos_count = Video.objects.filter(orientation='landscape').count()
    portrait_videos_count = Video.objects.filter(orientation='portrait').count()
    
    # Additional stats for the enhanced UI
    active_users = User.objects.filter(is_active=True).count()
    
    # Get new users this week
    today = timezone.now().date()
    week_start = today - datetime.timedelta(days=today.weekday())
    new_users_this_week = User.objects.filter(date_joined__date__gte=week_start).count()
    
    # Get comments this week
    comments_this_week = Comment.objects.filter(date_posted__date__gte=week_start).count()
    
    # For User Growth Chart (last 7 days)
    dates = [(today - datetime.timedelta(days=i)) for i in range(6, -1, -1)]
    date_strings = [date.strftime('%b %d') for date in dates]
    
    # Get user counts for each date
    user_counts = []
    for date in dates:
        next_day = date + datetime.timedelta(days=1)
        count = User.objects.filter(
            date_joined__date__gte=date,
            date_joined__date__lt=next_day
        ).count()
        user_counts.append(count)
    
    context = {
        'total_videos': total_videos,
        'total_users': total_users,
        'pending_reports': pending_reports,
        'total_comments': total_comments,
        'recent_videos': recent_videos,
        'recent_reports': recent_reports,
        'pending_appeals': pending_appeals,
        'recent_appeals': recent_appeals,
        'active_tab': 'dashboard',
        'now': timezone.now(),
        
        # Additional stats for enhanced UI
        'active_users': active_users,
        'new_users_this_week': new_users_this_week,
        'comments_this_week': comments_this_week,
        
        # Chart data
        'landscape_videos_count': landscape_videos_count,
        'portrait_videos_count': portrait_videos_count,
        
        'user_growth_labels': json.dumps(date_strings),
        'user_growth_data': json.dumps(user_counts),
    }
    return render(request, 'videos/admin_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_videos(request):
    videos = Video.objects.all()
    
    # Handle sorting parameters
    sort = request.GET.get('sort')
    if sort == 'date':
        videos = videos.order_by('-date_posted')
    elif sort == 'views':
        videos = videos.order_by('-views')
    elif sort == 'likes':
        videos = videos.annotate(like_count=Sum('likes')).order_by('-like_count')
    else:
        videos = videos.order_by('-date_posted')  # Default sort
    
    # Handle orientation filter
    orientation = request.GET.get('orientation')
    if orientation in ['landscape', 'portrait']:
        videos = videos.filter(orientation=orientation)
    
    context = {
        'videos': videos,
        'active_tab': 'videos'
    }
    return render(request, 'videos/admin_videos.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_users(request):
    # Start with all users
    users = User.objects.all()
    
    # Handle search query
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Handle status filter
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Handle sorting parameters
    sort = request.GET.get('sort')
    if sort == 'username':
        users = users.order_by('username')
    else:  # default to date sorting
        users = users.order_by('-date_joined')
    
    context = {
        'users': users,
        'active_tab': 'users',
        'current_sort': sort or 'date',
        'search_query': search_query,
        'status_filter': status_filter
    }
    return render(request, 'videos/admin_users.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_comments(request):
    comments = Comment.objects.all().order_by('-date_posted')
    context = {
        'comments': comments,
        'active_tab': 'comments'
    }
    return render(request, 'videos/admin_comments.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_notifications(request):
    notifications = Notification.objects.all().order_by('-created_at')
    context = {
        'notifications': notifications,
        'active_tab': 'notifications'
    }
    return render(request, 'videos/admin_notifications.html', context)

def search_videos(request):
    query = request.GET.get('q', '')
    
    if query:
        # Search in title and description
        search_results = Video.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        ).order_by('-date_posted')
    else:
        search_results = Video.objects.none()
    
    context = {
        'videos': search_results,
        'query': query,
        'page_title': f'Search results for "{query}"'
    }
    
    return render(request, 'videos/search_results.html', context)

@login_required
def save_video(request, pk):
    video = get_object_or_404(Video, pk=pk)
    saved, created = SavedVideo.objects.get_or_create(user=request.user, video=video)
    
    if not created:
        # Video was already saved, so unsave it
        saved.delete()
        is_saved = False
    else:
        is_saved = True
        
    return JsonResponse({'saved': is_saved})

@login_required
def get_watch_history(request):
    history = WatchHistory.objects.filter(user=request.user).select_related('video')
    return render(request, 'videos/watch_history.html', {'history': history})

@login_required
def clear_watch_history(request):
    if request.method == 'POST':
        WatchHistory.objects.filter(user=request.user).delete()
        messages.success(request, 'Watch history cleared successfully!')
    return redirect('watch_history')

@login_required
def get_saved_videos(request):
    saved_videos = SavedVideo.objects.filter(user=request.user).select_related('video')
    return render(request, 'videos/saved_videos.html', {'saved_videos': saved_videos})

@login_required
def get_liked_videos(request):
    videos = Video.objects.filter(likes=request.user)
    return render(request, 'videos/liked_videos.html', {'videos': videos})

@login_required
def your_videos(request):
    """Display the videos uploaded by the current user."""
    videos = Video.objects.filter(author=request.user).order_by('-date_posted')
    
    context = {
        'videos': videos,
        'title': 'Your Videos'
    }
    return render(request, 'videos/your_videos.html', context)
