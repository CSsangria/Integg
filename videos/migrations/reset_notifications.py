from django.db import migrations

def reset_notifications(apps, schema_editor):
    Notification = apps.get_model('videos', 'Notification')
    Notification.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('videos', '0006_alter_notification_notification_type'),
    ]

    operations = [
        migrations.RunPython(reset_notifications),
    ] 