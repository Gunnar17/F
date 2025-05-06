# management/commands/sync_ksi_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from ...sync import sync_tournament_data

class Command(BaseCommand):
    help = 'Sync data from KSI web services'

    def add_arguments(self, parser):
        parser.add_argument('--tournament', type=int, help='Sync data for a specific tournament ID')
        parser.add_argument('--start', type=int, help='Starting tournament ID for a range')
        parser.add_argument('--end', type=int, help='Ending tournament ID for a range')
        parser.add_argument('--all', action='store_true', help='Sync data for all active tournaments')

    def handle(self, *args, **options):
        if options['tournament']:
            self.stdout.write(self.style.SUCCESS(f'Syncing data for tournament {options["tournament"]}...'))
            sync_tournament_data(options['tournament'])
            self.stdout.write(self.style.SUCCESS('Done!'))
        elif options['start'] and options['end']:
            start_id = options['start']
            end_id = options['end']
            for tournament_id in range(start_id, end_id + 1):
                self.stdout.write(self.style.SUCCESS(f'Syncing data for tournament {tournament_id}...'))
                sync_tournament_data(tournament_id)
            self.stdout.write(self.style.SUCCESS('All tournaments synced!'))
        elif options['all']:
            # Here you would implement logic to determine which tournaments are "active"
            # For example, you might have a list of tournament IDs in your settings
            from django.conf import settings
            active_tournaments = getattr(settings, 'ACTIVE_TOURNAMENTS', [])
            for tournament_id in active_tournaments:
                self.stdout.write(self.style.SUCCESS(f'Syncing data for tournament {tournament_id}...'))
                sync_tournament_data(tournament_id)
            self.stdout.write(self.style.SUCCESS('All tournaments synced!'))
        else:
            self.stdout.write(self.style.ERROR('Please specify --tournament, --start/--end, or --all'))