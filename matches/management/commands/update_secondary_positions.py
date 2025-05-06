from django.core.management.base import BaseCommand
from matches.models import Player


class Command(BaseCommand):
    help = 'Updates secondary positions for all players based on their primary position'

    def handle(self, *args, **options):
        # Get all players
        players = Player.objects.all()

        # Initialize counters
        updated = 0

        # Process each player
        for player in players:
            # Skip goalkeepers - they don't get a secondary position
            if player.position == 'GK':
                continue

            # Assign secondary position based on primary position
            if player.position == 'FW':
                player.secondary_position = 'MID'
            elif player.position == 'MID':
                # Alternating between FW and DEF for midfielders
                if player.id % 2 == 0:  # Even-numbered players
                    player.secondary_position = 'FW'
                else:  # Odd-numbered players
                    player.secondary_position = 'DEF'
            elif player.position == 'DEF':
                player.secondary_position = 'MID'

            # Save the player
            player.save()
            updated += 1

            # Print progress information
            self.stdout.write(
                f"Updated {player.first_name} {player.last_name}: {player.position} → {player.secondary_position}")

        # Print summary
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated} players"))