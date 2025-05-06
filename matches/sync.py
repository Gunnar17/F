# sync.py
import subprocess
from django.utils import timezone
from django.db import transaction
from .models import Team, Player, Tournament, Match, MatchEvent, TournamentStanding
from .services import KSIService


# Get all teams from your database
teams = Team.objects.all()

for team in teams:
    print(f"Syncing player data for team {team.name} (ID: {team.team_number})...")
    # You'll need to create this management command
    #subprocess.run(["python", "manage.py", "sync_team_players", f"--team={team.team_number}"])
    print(f"Completed player sync for {team.name}")


completed_matches = Match.objects.exclude(home_score=None).exclude(away_score=None)

for match in completed_matches:
    print(f"Syncing events for match {match.match_number}...")
    #subprocess.run(["python", "manage.py", "sync_match_events", f"--match={match.match_number}"])
    print(f"Completed event sync for match {match.match_number}")


def debug_response(obj, prefix=''):
    """Safely debug any response object regardless of its structure."""
    print(f"{prefix}Type: {type(obj)}")

    if hasattr(obj, '__dict__'):
        print(f"{prefix}Attributes: {dir(obj)}")

    if hasattr(obj, 'items') and callable(obj.items):
        # If it's dict-like
        print(f"{prefix}Keys: {list(obj.keys()) if hasattr(obj, 'keys') else 'No keys method'}")
        for k, v in obj.items():
            print(f"{prefix}[{k}] = {type(v)}")

    # Try various access methods
    try:
        if hasattr(obj, '__len__'):
            print(f"{prefix}Length: {len(obj)}")

            # Try to access first item if it has length
            if len(obj) > 0:
                try:
                    first = obj[0]
                    print(f"{prefix}First item type: {type(first)}")
                except (IndexError, TypeError, KeyError):
                    try:
                        # Maybe it's a dict-like object with numeric keys
                        first = obj.get(0)
                        print(f"{prefix}First item (via get) type: {type(first)}")
                    except:
                        print(f"{prefix}Cannot access first item")
    except:
        print(f"{prefix}No length or cannot access length")


def sync_tournament_data(tournament_id):
    """
    Sync all data for a specific tournament.
    """
    service = KSIService()

    # Get tournament matches
    response = service.get_tournament_matches(tournament_id)
    if not response:
        print(f"Error fetching tournament matches: No response")
        return

    # Check for errors
    if hasattr(response, 'VillaNumer') and response.VillaNumer != 0:
        print(f"Error from API: {response.Villa}")
        return

    # Process matches if available
    if hasattr(response, 'ArrayMotLeikir') and response.ArrayMotLeikir:
        # Handle the special case where ArrayMotLeikir has a MotLeikur attribute
        if hasattr(response.ArrayMotLeikir, 'MotLeikur'):
            matches = response.ArrayMotLeikir.MotLeikur
            # If MotLeikur is a single object, wrap it in a list
            if not isinstance(matches, list):
                matches = [matches]
            print(f"Found {len(matches)} matches")
        else:
            # Fallback to iterating (though this is likely not needed based on debug)
            matches = list(response.ArrayMotLeikir)
            print(f"Found {len(matches)} matches (via iteration)")

        with transaction.atomic():
            for match_data in matches:
                # Skip if the match_data is just a string
                if isinstance(match_data, str):
                    print(f"Skipping string match: {match_data}")
                    continue

                # Process match data
                try:
                    home_team, created = Team.objects.get_or_create(
                        team_number=match_data.FelagHeimaNumer,
                        defaults={'name': match_data.FelagHeimaNafn}
                    )

                    away_team, created = Team.objects.get_or_create(
                        team_number=match_data.FelagUtiNumer,
                        defaults={'name': match_data.FelagUtiNafn}
                    )

                    tournament, created = Tournament.objects.get_or_create(
                        tournament_number=tournament_id,
                        defaults={
                            'name': match_data.MotNafn if hasattr(match_data,
                                                                  'MotNafn') else f"Tournament {tournament_id}",
                            'start_date': match_data.LeikDagur.date() if hasattr(match_data,
                                                                                 'LeikDagur') else timezone.now().date()
                            # Use match date or today
                        }
                    )

                    # Create or update match
                    match, created = Match.objects.update_or_create(
                        match_number=match_data.LeikurNumer,
                        defaults={
                            'tournament': tournament,
                            'match_date': timezone.make_aware(match_data.LeikDagur) if timezone.is_naive(
                                match_data.LeikDagur) else match_data.LeikDagur,
                            'home_team': home_team,
                            'away_team': away_team,
                            'home_score': match_data.UrslitHeima if hasattr(match_data, 'UrslitHeima') else None,
                            'away_score': match_data.UrslitUti if hasattr(match_data, 'UrslitUti') else None,
                            'stadium_name': match_data.VollurNafn if hasattr(match_data, 'VollurNafn') else "",
                            'stadium_number': match_data.VollurNumer if hasattr(match_data, 'VollurNumer') else 0,
                            'attendance': match_data.Ahorfendur if hasattr(match_data, 'Ahorfendur') else ""
                        }
                    )

                    print(f"Processed match: {match}")

                    # Get match events if the match has been played
                    if match.home_score and match.away_score:
                        try:
                            sync_match_events(match.match_number)
                        except Exception as e:
                            print(f"Error syncing events for match {match.match_number}: {e}")

                except Exception as e:
                    print(f"Error processing match: {e}")
    else:
        print(f"No matches found for tournament {tournament_id}")

    # Similar updates needed for the standings section...


def sync_match_events(match_number):
    """Sync events for a specific match."""
    service = KSIService()

    try:
        match = Match.objects.get(match_number=match_number)
    except Match.DoesNotExist:
        print(f"Match {match_number} not found in database")
        return

    # Get match events
    response = service.get_match_events(match_number)

    if not response:
        print(f"Error fetching match events: No response")
        return

    # Handle the special case for match events
    events = None
    if hasattr(response, 'ArrayLeikurAtburdir'):
        if hasattr(response.ArrayLeikurAtburdir, 'LeikurAtburdir'):
            events = response.ArrayLeikurAtburdir.LeikurAtburdir
            # If not a list, wrap it
            if not isinstance(events, list):
                events = [events]

    if not events:
        print(f"No events found for match {match_number}")
        return

    # Clear existing events
    with transaction.atomic():
        MatchEvent.objects.filter(match=match).delete()

        # Process events
        for event_data in events:
            try:
                # Get team first
                team, team_created = Team.objects.get_or_create(
                    team_number=event_data.FelagNumer,
                    defaults={'name': event_data.FelagNafn}
                )

                # Get or create player
                player, player_created = Player.objects.get_or_create(
                    player_number=event_data.LeikmadurNumer,
                    defaults={
                        'name': event_data.LeikmadurNafn,
                        'team': team,
                        'birth_year': '',
                        'position': 'MID'  # Default position
                    }
                )

                # Create event
                MatchEvent.objects.create(
                    match=match,
                    player=player,
                    minute=event_data.AtburdurMinuta,
                    event_type=event_data.AtburdurNafn,
                    event_number=event_data.AtburdurNumer
                )
                print(f"Added event: {event_data.AtburdurNafn} by {event_data.LeikmadurNafn}")
            except Exception as e:
                print(f"Error processing event: {e}")


def sync_player_data(player_number):
    """
    Sync detailed information for a specific player.
    """
    service = KSIService()

    # Get player info
    response = service.get_player_info(player_number)

    if not response:
        print(f"Error fetching player info: No response")
        return

    # Check for errors
    if hasattr(response, 'VillaNumer') and response.VillaNumer != 0:
        print(f"Error from API: {response.Villa}")
        return

    # Process player data if available
    if hasattr(response, 'ArrayLeikmadur') and response.ArrayLeikmadur:
        with transaction.atomic():
            for player_data in response.ArrayLeikmadur:
                # Get or create team
                team, _ = Team.objects.get_or_create(
                    team_number=player_data.FelagNumer,
                    defaults={'name': player_data.FelagNafn}
                )

                # Update player information
                Player.objects.update_or_create(
                    player_number=player_data.LeikmadurNumer,
                    defaults={
                        'name': player_data.LeikmadurNafn,
                        'team': team,
                        'birth_year': player_data.FaedingarAr if hasattr(player_data, 'FaedingarAr') else '',
                        'first_team_matches': player_data.MeistFlokkurLeikir if hasattr(player_data,
                                                                                        'MeistFlokkurLeikir') else 0,
                        'first_team_goals': player_data.MeistFlokkurMork if hasattr(player_data,
                                                                                    'MeistFlokkurMork') else 0,
                        'national_team_matches': player_data.ALandsleikirLeikir if hasattr(player_data,
                                                                                           'ALandsleikirLeikir') else 0,
                        'national_team_goals': player_data.ALandsleikirMork if hasattr(player_data,
                                                                                       'ALandsleikirMork') else 0
                    }
                )
                print(f"Updated player: {player_data.LeikmadurNafn}")
    else:
        print(f"No data found for player {player_number}")


def sync_team_matches(team_number, start_date, end_date):
    """
    Sync matches for a specific team within a date range.
    """
    service = KSIService()

    # Get team matches
    response = service.get_team_matches(team_number, start_date, end_date)

    if not response:
        print(f"Error fetching team matches: No response")
        return

    # Check for errors
    if hasattr(response, 'VillaNumer') and response.VillaNumer != 0:
        print(f"Error from API: {response.Villa}")
        return

    # Process matches if available
    if hasattr(response, 'ArrayFelogLeikir') and response.ArrayFelogLeikir:
        print(f"Found {len(response.ArrayFelogLeikir)} matches for team {team_number}")

        with transaction.atomic():
            for match_data in response.ArrayFelogLeikir:
                # Get or create teams
                home_team, _ = Team.objects.get_or_create(
                    team_number=match_data.FelagHeimaNumer,
                    defaults={'name': match_data.FelagHeimaNafn}
                )

                away_team, _ = Team.objects.get_or_create(
                    team_number=match_data.FelagUtiNumer,
                    defaults={'name': match_data.FelagUtiNafn}
                )

                # Get or create tournament
                tournament, _ = Tournament.objects.get_or_create(
                    tournament_number=match_data.MotNumer,
                    defaults={'name': match_data.MotNafn}
                )

                # Create or update match
                match, created = Match.objects.update_or_create(
                    match_number=match_data.LeikurNumer,
                    defaults={
                        'tournament': tournament,
                        'match_date': match_data.LeikDagur,
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_score': match_data.UrslitHeima if hasattr(match_data, 'UrslitHeima') else None,
                        'away_score': match_data.UrslitUti if hasattr(match_data, 'UrslitUti') else None,
                        'stadium_name': match_data.VollurNafn if hasattr(match_data, 'VollurNafn') else "",
                        'stadium_number': match_data.VollurNumer if hasattr(match_data, 'VollurNumer') else 0
                    }
                )

                # Get match events if the match has been played
                if match.home_score and match.away_score:
                    try:
                        sync_match_events(match.match_number)
                    except Exception as e:
                        print(f"Error syncing events for match {match.match_number}: {e}")
    else:
        print(f"No matches found for team {team_number} in the specified date range")