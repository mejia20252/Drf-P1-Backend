from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Creates a default superuser if one does not exist.'

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'ab@g.com', 'angelica2025')
            self.stdout.write(self.style.SUCCESS('Default superuser "admin" created.'))
        else:
            self.stdout.write(self.style.SUCCESS('Superuser "admin" already exists.'))