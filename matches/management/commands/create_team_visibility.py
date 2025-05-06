# Save this in a new file: yourapp/management/commands/create_team_visibility.py

from django.core.management.base import BaseCommand
from django.db.models import Count
from matches.models import Team, TeamVisibility  # Replace 'yourapp' with your actual app name


class Command(BaseCommand):
    help = 'Creates TeamVisibility records for all teams that do not have them yet'

    def handle(self, *args, **options):
        # Get all teams without TeamVisibility records
        teams_without_visibility = Team.objects.annotate(
            visibility_count=Count('visibility')
        ).filter(visibility_count=0)

        if not teams_without_visibility:
            self.stdout.write(self.style.SUCCESS('All teams already have visibility settings'))
            return

        # Create default visibility settings
        created_count = 0
        for team in teams_without_visibility:
            TeamVisibility.objects.create(team=team)
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Created visibility settings for {created_count} teams')
        )

        # Create directory structure if it doesn't exist
        # management/commands/__init__.py files are needed for Django to discover the command