# tasks.py
from django_background_tasks import background
from datetime import timedelta
from .sync import sync_tournament_data
from django.conf import settings


@background(schedule=timedelta(hours=3))
def schedule_tournament_sync(tournament_id):
    """Schedule a background task to sync tournament data."""
    sync_tournament_data(tournament_id)


def schedule_all_tournament_syncs():
    """Schedule background tasks for all active tournaments."""
    active_tournaments = getattr(settings, 'ACTIVE_TOURNAMENTS', [])
    for tournament_id in active_tournaments:
        schedule_tournament_sync(tournament_id)