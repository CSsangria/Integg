from django.contrib import admin
from .models import Video, Comment, Subscription, Notification, VideoReport

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'date_posted', 'views')
    list_filter = ('date_posted', 'author')
    search_fields = ('title', 'description')
    date_hierarchy = 'date_posted'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'video', 'content', 'date_posted')
    list_filter = ('date_posted', 'author')
    search_fields = ('content',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'subscribed_to', 'date_subscribed')
    list_filter = ('date_subscribed',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'sender', 'notification_type', 'content', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('content', 'recipient__username', 'sender__username')
    raw_id_fields = ('recipient', 'sender', 'video', 'comment')

@admin.register(VideoReport)
class VideoReportAdmin(admin.ModelAdmin):
    list_display = ('video', 'reporter', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('video__title', 'reporter__username', 'description')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'reviewed_at')
    actions = ['delete_reported_videos']

    def delete_reported_videos(self, request, queryset):
        count = 0
        for report in queryset:
            if report.video:
                report.video.delete()
                count += 1
        self.message_user(request, f"{count} reported videos have been deleted.")
    delete_reported_videos.short_description = "Delete the video(s) under selected report(s)"

    def has_add_permission(self, request):
        return False  # Prevent manual creation of reports through admin
