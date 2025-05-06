from django.core.management.base import BaseCommand
from matches.models import Team, TeamVisibility  # Replace 'yourapp' with your actual app name

class Command(BaseCommand):
    help = 'Sets up team visibility settings for all teams'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hide-all',
            action='store_true',
            help='Hide all teams from user selection',
        )
        parser.add_argument(
            '--show-all',
            action='store_true',
            help='Make all teams visible to users',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all team visibility to default (visible)',
        )

    def handle(self, *args, **options):
        # Create visibility settings for teams that don't have them
        teams_without_visibility = []
        for team in Team.objects.all():
            try:
                # Check if visibility exists
                team.visibility
            except TeamVisibility.DoesNotExist:
                teams_without_visibility.append(team)

        # Create visibility objects for teams that don't have them
        for team in teams_without_visibility:
            TeamVisibility.objects.create(team=team)
            self.stdout.write(f"Created visibility settings for: {team.name}")

        if options['hide_all']:
            # Hide all teams
            count = TeamVisibility.objects.update(visible_to_users=False)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully hid all {count} teams')
            )
        elif options['show_all']:
            # Show all teams
            count = TeamVisibility.objects.update(visible_to_users=True)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully made all {count} teams visible')
            )
        elif options['reset']:
            # Reset to default (visible)
            count = TeamVisibility.objects.update(visible_to_users=True, display_priority=100)
            self.stdout.write(
                self.style.SUCCESS(f'Reset visibility settings for {count} teams')
            )
        else:
            # Just print stats
            total = TeamVisibility.objects.count()
            visible = TeamVisibility.objects.filter(visible_to_users=True).count()
            hidden = total - visible

            self.stdout.write(f"Team visibility status:")
            self.stdout.write(f"- Total teams: {total}")
            self.stdout.write(f"- Visible teams: {visible}")
            self.stdout.write(f"- Hidden teams: {hidden}")

            if teams_without_visibility:
                self.stdout.write(
                    self.style.SUCCESS(f'Created visibility settings for {len(teams_without_visibility)} teams')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('All teams already have visibility settings')
                )