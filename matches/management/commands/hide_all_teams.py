from django.core.management.base import BaseCommand
from matches.models import TeamVisibility  # Replace 'yourapp' with your app name


class Command(BaseCommand):
    help = 'Hide all teams from user selection'

    def handle(self, *args, **options):
        updated = TeamVisibility.objects.update(visible_to_users=False)
        self.stdout.write(
            self.style.SUCCESS(f'Successfully hid {updated} teams')
        )