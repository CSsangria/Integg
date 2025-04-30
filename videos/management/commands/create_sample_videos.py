from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from videos.models import Video
from django.core.files import File
import os
from datetime import datetime, timedelta
import random
import requests
from PIL import Image
import io

class Command(BaseCommand):
    help = 'Creates sample videos for testing'

    def handle(self, *args, **kwargs):
        # Create or get the sample user
        user, created = User.objects.get_or_create(
            username='sampleuser',
            defaults={
                'email': 'sample@example.com',
                'password': 'samplepass123'
            }
        )
        if created:
            user.set_password('samplepass123')
            user.save()
            self.stdout.write(self.style.SUCCESS('Created sample user'))

        # Sample video data with thumbnail URLs
        sample_videos = [
            {
                'title': 'Introduction to Python Programming',
                'description': 'Learn the basics of Python programming language in this comprehensive tutorial.',
                'views': random.randint(1000, 10000),
                'date_posted': datetime.now() - timedelta(days=random.randint(1, 30)),
                'thumbnail_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png'
            },
            {
                'title': 'Web Development with Django',
                'description': 'Build your first web application using Django framework.',
                'views': random.randint(1000, 10000),
                'date_posted': datetime.now() - timedelta(days=random.randint(1, 30)),
                'thumbnail_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Django_logo.svg/1200px-Django_logo.svg.png'
            },
            {
                'title': 'Machine Learning Basics',
                'description': 'An introduction to machine learning concepts and algorithms.',
                'views': random.randint(1000, 10000),
                'date_posted': datetime.now() - timedelta(days=random.randint(1, 30)),
                'thumbnail_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Scikit_learn_logo_small.svg/1200px-Scikit_learn_logo_small.svg.png'
            },
            {
                'title': 'Data Science Tutorial',
                'description': 'Learn how to analyze and visualize data using Python.',
                'views': random.randint(1000, 10000),
                'date_posted': datetime.now() - timedelta(days=random.randint(1, 30)),
                'thumbnail_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ed/Pandas_logo.svg/1200px-Pandas_logo.svg.png'
            },
            {
                'title': 'Building REST APIs',
                'description': 'Create powerful REST APIs using Django REST framework.',
                'views': random.randint(1000, 10000),
                'date_posted': datetime.now() - timedelta(days=random.randint(1, 30)),
                'thumbnail_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/JavaScript-logo.png/1200px-JavaScript-logo.png'
            }
        ]

        # Create sample videos
        for video_data in sample_videos:
            video = Video.objects.create(
                title=video_data['title'],
                description=video_data['description'],
                author=user,
                views=video_data['views'],
                date_posted=video_data['date_posted']
            )
            
            # Create a dummy video file
            video_path = os.path.join('media', 'videos', f'{video.id}.mp4')
            os.makedirs(os.path.dirname(video_path), exist_ok=True)
            with open(video_path, 'w') as f:
                f.write('This is a dummy video file')
            
            # Download and save thumbnail
            try:
                response = requests.get(video_data['thumbnail_url'])
                if response.status_code == 200:
                    # Convert to JPEG if needed
                    img = Image.open(io.BytesIO(response.content))
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        img = img.convert('RGB')
                    
                    # Save the image
                    thumbnail_path = os.path.join('media', 'thumbnails', f'{video.id}.jpg')
                    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                    img.save(thumbnail_path, 'JPEG')
                    
                    # Save to video object
                    with open(thumbnail_path, 'rb') as f:
                        video.thumbnail.save(f'{video.id}.jpg', File(f))
                else:
                    self.stdout.write(self.style.WARNING(f'Failed to download thumbnail for {video.title}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error processing thumbnail for {video.title}: {str(e)}'))
            
            # Save the video file
            with open(video_path, 'rb') as f:
                video.video_file.save(f'{video.id}.mp4', File(f))
            
            self.stdout.write(self.style.SUCCESS(f'Created video: {video.title}'))

        self.stdout.write(self.style.SUCCESS('Successfully created sample videos')) 