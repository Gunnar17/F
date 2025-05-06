# matches/management/commands/sync_match_events.py
from django.core.management.base import BaseCommand
from matches.sync import sync_match_events


class Command(BaseCommand):
    help = 'Sync events for a specific match'

    def add_arguments(self, parser):
        parser.add_argument('--match', type=int, required=True, help='Match ID to sync events for')

    def handle(self, *args, **options):
        match_id = options['match']
        self.stdout.write(self.style.SUCCESS(f'Syncing events for match {match_id}...'))
        sync_match_events(match_id)
        self.stdout.write(self.style.SUCCESS('Done!'))