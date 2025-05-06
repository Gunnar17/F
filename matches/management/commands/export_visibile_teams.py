from django.core.management.base import BaseCommand
import json
import os
from matches.models import Team  # Replace 'yourapp' with your app name


class Command(BaseCommand):
    help = 'Export visible teams to a JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default='visible_teams.json',
            help='Output file path',
        )

    def handle(self, *args, **options):
        # Get visible teams
        visible_teams = []
        for team in Team.objects.all():
            try:
                if team.visibility.visible_to_users:
                    visible_teams.append({
                        'id': team.team_number,
                        'name': team.name,
                        'category': team.category
                    })
            except:
                # Skip teams without visibility settings
                pass

        # Get the project's base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        # Write to file
        output_path = os.path.join(base_dir, 'static', options['output'])
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(visible_teams, f)

        self.stdout.write(
            self.style.SUCCESS(f'Exported {len(visible_teams)} visible teams to {output_path}')
        )