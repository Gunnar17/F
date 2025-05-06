from django.core.management.base import BaseCommand
from matches.models import Player


class Command(BaseCommand):
    help = 'Updates secondary and third positions for all players based on their primary position'

    def handle(self, *args, **options):
        # Get all players
        players = Player.objects.all()

        # Initialize counters
        updated = 0

        # Process each player
        for player in players:
            # Skip goalkeepers - they don't get additional positions
            if player.position == 'GK':
                continue

            # Assign positions based on primary position
            if player.position == 'FW':
                player.secondary_position = 'MID'
                player.third_position = None  # FWs only have secondary position

            elif player.position == 'MID':
                # For midfielders: secondary = FW, third = DEF
                player.secondary_position = 'FW'
                player.third_position = 'DEF'

            elif player.position == 'DEF':
                player.secondary_position = 'MID'
                player.third_position = None  # DEFs only have secondary position

            # Save the player
            player.save()
            updated += 1

            # Print progress information
            self.stdout.write(f"Updated {player.first_name} {player.last_name}: {player.position} → "
                              f"{player.secondary_position} → {player.third_position or 'None'}")

        # Print summary
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated} players"))