from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from moviepy.video.io.VideoFileClip import VideoFileClip
import os

class Video(models.Model):
    ORIENTATION_CHOICES = [
        ('landscape', 'Landscape'),
        ('portrait', 'Portrait'),
        ('square', 'Square'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    video_file = models.FileField(upload_to='videos/')
    thumbnail = models.ImageField(upload_to='thumbnails/', default='default.jpg')
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    views = models.IntegerField(default=0)
    likes = models.ManyToManyField(User, related_name='video_likes', blank=True)
    orientation = models.CharField(max_length=10, choices=ORIENTATION_CHOICES, default='landscape')
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    duration = models.FloatField(default=0)  # Duration in seconds

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.likes.count()

    def format_duration(self):
        """Format duration into MM:SS or HH:MM:SS"""
        total_seconds = int(self.duration)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def detect_video_properties(self):
        """Detect video properties (orientation and duration) and update the model"""
        try:
            # Get the absolute path of the video file
            video_path = self.video_file.path
            
            # Check if file exists
            if not os.path.exists(video_path):
                return False

            # Load the video file
            with VideoFileClip(video_path) as video:
                # Get video dimensions
                width = video.size[0]
                height = video.size[1]
                
                # Update dimensions
                self.width = width
                self.height = height
                
                # Get duration
                self.duration = video.duration
                
                # Determine orientation
                if width > height:
                    self.orientation = 'landscape'
                elif height > width:
                    self.orientation = 'portrait'
                else:
                    self.orientation = 'square'
                
                # Save the changes
                self.save()
                return True
        except Exception as e:
            print(f"Error detecting video properties: {str(e)}")
            return False

    def save(self, *args, **kwargs):
        # If this is a new video or the video file has changed
        if not self.pk or 'video_file' in self.get_dirty_fields():
            super().save(*args, **kwargs)  # Save first to get the file path
            self.detect_video_properties()  # Then detect properties
        else:
            super().save(*args, **kwargs)

    def get_dirty_fields(self):
        """Helper method to detect changed fields"""
        dirty_fields = {}
        if self.pk:
            original = Video.objects.get(pk=self.pk)
            for field in self._meta.fields:
                original_value = getattr(original, field.name)
                current_value = getattr(self, field.name)
                if original_value != current_value:
                    dirty_fields[field.name] = original_value
        return dirty_fields

class Comment(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    likes = models.ManyToManyField(User, related_name='comment_likes', blank=True)
    dislikes = models.ManyToManyField(User, related_name='comment_dislikes', blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    is_reply = models.BooleanField(default=False)

    def __str__(self):
        return f'Comment by {self.author.username} on {self.video.title}'

    def total_likes(self):
        return self.likes.count()

    def total_dislikes(self):
        return self.dislikes.count()

    def get_replies(self):
        return Comment.objects.filter(parent=self).order_by('date_posted')

class Subscription(models.Model):
    subscriber = models.ForeignKey(User, related_name='subscriptions', on_delete=models.CASCADE)
    subscribed_to = models.ForeignKey(User, related_name='subscribers', on_delete=models.CASCADE)
    date_subscribed = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('subscriber', 'subscribed_to')

    def __str__(self):
        return f'{self.subscriber.username} -> {self.subscribed_to.username}'

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('subscriber', 'New Subscriber'),
        ('reply', 'Reply to Comment'),
        ('comment', 'New Comment'),
    )
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    content = models.TextField()
    video = models.ForeignKey(Video, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.username} - {self.get_notification_type_display()}"

class VideoReport(models.Model):
    REPORT_REASONS = [
        ('inappropriate', 'Inappropriate Content'),
        ('spam', 'Spam or Misleading'),
        ('copyright', 'Copyright Infringement'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('action_taken', 'Action Taken'),
    ]

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_reports')
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reports')

    class Meta:
        ordering = ['-created_at']
        unique_together = ['video', 'reporter']

    def __str__(self):
        return f"Report on {self.video.title} by {self.reporter.username}"
