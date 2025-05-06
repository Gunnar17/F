# matches/management/commands/sync_team_players.py
from django.core.management.base import BaseCommand
from matches.sync import sync_player_data


class Command(BaseCommand):
    help = 'Sync player data for a specific team'

    def add_arguments(self, parser):
        parser.add_argument('--team', type=int, required=True, help='Team ID to sync players for')

    def handle(self, *args, **options):
        team_id = options['team']
        self.stdout.write(self.style.SUCCESS(f'Syncing players for team {team_id}...'))
        sync_player_data(team_id)
        self.stdout.write(self.style.SUCCESS('Done!'))