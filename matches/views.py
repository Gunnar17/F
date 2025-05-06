from django.shortcuts import render, redirect, get_object_or_404
from datetime import date, datetime, timezone
import calendar
from django.utils.timezone import make_aware
from django.utils import timezone
from .models import Game, Team, GameDay, MatchEvent, GameLineup, Player, Tournament, Match, TournamentStanding, GamedayJob, GamedayStaffAssignment, TeamVisibility
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import UsernameChangeForm, GamedayJobForm, GamedayStaffAssignmentForm
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import json
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.db import models
from django.urls import reverse
#from django.utils.http import urlencode
from django.db.models.signals import post_save
from django.dispatch import receiver


def is_commentator(user):
    return user.groups.filter(name='Commentator').exists()


def is_fan(user):
    return user.groups.filter(name='Fan').exists()


def get_gameday_info(request, game_id):
    """Fetch GameDay settings & current match events."""
    gameday = get_object_or_404(GameDay, game__id=game_id)
    events = MatchEvent.objects.filter(game__id=game_id).order_by('-event_time')

    data = {
        "intro_announcement": gameday.intro_announcement,
        "halftime_announcement": gameday.halftime_announcement,
        "fulltime_announcement": gameday.fulltime_announcement,
        "goal_audio": gameday.goal_audio.url if gameday.goal_audio else None,
        "sponsor_audio": gameday.sponsor_audio.url if gameday.sponsor_audio else None,
        "events": [
            {"type": e.event_type, "player": e.player_name, "team": e.team.name, "time": e.event_time.strftime("%H:%M")}
            for e in events
        ]
    }

    return JsonResponse(data)


@csrf_exempt
def trigger_announcement(request, game_id, announcement_type):
    """Trigger an announcement."""
    if request.method == "POST":
        gameday = get_object_or_404(GameDay, game__id=game_id)

        message = ""
        if announcement_type == "intro":
            message = gameday.intro_announcement
        elif announcement_type == "halftime":
            message = gameday.halftime_announcement
        elif announcement_type == "fulltime":
            message = gameday.fulltime_announcement

        return JsonResponse({"message": message})


@csrf_exempt
def log_match_event(request, game_id):
    """Log a match event (goal, yellow card, red card, substitution)."""

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            game = get_object_or_404(Game, id=game_id)
            team = get_object_or_404(Team, id=data["team_id"])

            event = MatchEvent.objects.create(
                game=game,
                event_type=data["event_type"],
                player_name=data["player_name"],
                team=team
            )

            return JsonResponse({"success": True, "event": event.event_type})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    # 🚀 **Fix: Return an error for GET requests instead of returning None**
    return HttpResponseBadRequest("This endpoint only supports POST requests.")


def home(request):
    today = date.today()
    month = request.GET.get("month", today.month)
    year = request.GET.get("year", today.year)

    try:
        month = int(month)
        year = int(year)
    except ValueError:
        month, year = today.month, today.year

    month = max(1, min(12, month))

    leagues = {
        'men': 'Men\'s Leagues',
        'women': 'Women\'s Leagues'
    }

    # Replace: teams = Team.objects.all().order_by('name')
    teams = get_visible_teams()

    return render(request, "matches/home.html", {
        "month": month,
        "year": year,
        "month_name": calendar.month_name[month],
        "leagues": leagues,
        "teams": teams,
    })


def calculate_league_table(category=None):
    from .models import Team  # Ensure the Team model is imported

    if category in ['men', 'women']:
        teams_qs = Team.objects.filter(category=category)
    else:
        teams_qs = Team.objects.all()

    # Create a dictionary of teams with their stats
    team_stats = {}

    for team in teams_qs:
        team_stats[team.id] = {
            "id": team.id,
            "team": team.name,
            "logo": team.logo.url if team.logo else None,
            "games_played": 0,  # ✅ New
            "wins": 0,  # ✅ New
            "draws": 0,  # ✅ New
            "losses": 0,  # ✅ New
            "scored": 0,
            "conceded": 0,
            "goal_difference": 0,
            "points": 0
        }

    games_qs = Game.objects.filter(played=True)
    if category in ['men', 'women']:
        games_qs = games_qs.filter(category=category)

    for game in games_qs:
        home_team_id = game.home_team.id
        away_team_id = game.away_team.id

        team_stats[home_team_id]["games_played"] += 1
        team_stats[away_team_id]["games_played"] += 1

        team_stats[home_team_id]["scored"] += game.home_goals
        team_stats[away_team_id]["scored"] += game.away_goals
        team_stats[home_team_id]["conceded"] += game.away_goals
        team_stats[away_team_id]["conceded"] += game.home_goals

        team_stats[home_team_id]["goal_difference"] = (
                team_stats[home_team_id]["scored"] - team_stats[home_team_id]["conceded"]
        )
        team_stats[away_team_id]["goal_difference"] = (
                team_stats[away_team_id]["scored"] - team_stats[away_team_id]["conceded"]
        )

        if game.home_goals > game.away_goals:
            team_stats[home_team_id]["wins"] += 1
            team_stats[home_team_id]["points"] += 3
            team_stats[away_team_id]["losses"] += 1
        elif game.away_goals > game.home_goals:
            team_stats[away_team_id]["wins"] += 1
            team_stats[away_team_id]["points"] += 3
            team_stats[home_team_id]["losses"] += 1
        else:
            team_stats[home_team_id]["draws"] += 1
            team_stats[away_team_id]["draws"] += 1
            team_stats[home_team_id]["points"] += 1
            team_stats[away_team_id]["points"] += 1

    leagues_table = sorted(
        [
            {
                "id": team_id,  # ✅ Assign team ID properly
                "team": stats["team"],
                "logo": stats["logo"],
                "scored": stats["scored"],
                "conceded": stats["conceded"],
                "goal_difference": stats["goal_difference"],
                "points": stats["points"],
            }
            for team_id, stats in team_stats.items()  # ✅ Ensuring correct structure
        ],
        key=lambda x: (-x["points"], -x["goal_difference"], -x["scored"], x["team"])
    )

    for index, team in enumerate(leagues_table):
        team["position"] = index + 1

    # ✅ Debugging Output
    print("DEBUGGING LEAGUE TABLE DATA:")
    for team in leagues_table:
        print(f"Team: {team['team']}, ID: {team['id']}")

    return leagues_table


def get_match_results(game):
    """ Placeholder function for fetching real match results """
    return (0, 0)  # Replace with real data retrieval


def team_calendar(request):
    team_id = request.GET.get('team_id')
    month = request.GET.get('month', date.today().month)
    year = request.GET.get('year', date.today().year)
    show_all = request.GET.get('show_all', 'false').lower() == 'true'  # Parameter to override filtering

    try:
        month = int(month)
        year = int(year)

        # Check if team_id exists and is not empty
        if not team_id:
            # Show improved team selector with filtering options
            teams = Team.objects.all().order_by('name')
            return render(request, "matches/improved_team_selector.html", {
                'teams': teams,
                'month': month,
                'year': year,
            })

        # Use team_number field since that's your primary key
        team = Team.objects.get(team_number=team_id)

    except (ValueError, Team.DoesNotExist):
        messages.error(request, "Invalid team or date information")
        return redirect('home')

    # Check if TeamTournamentFilter model exists and if the team has filters
    has_filters = False
    filtered_tournament_ids = []

    # Get filtered tournaments if not showing all
    if not show_all:
        try:
            # Check if the team has tournament_filters related manager
            if hasattr(team, 'tournament_filters'):
                # Get tournaments this team should show
                filter_qs = team.tournament_filters.filter(is_main_tournament=True)
                if filter_qs.exists():
                    has_filters = True
                    filtered_tournament_ids = list(filter_qs.values_list('tournament__tournament_number', flat=True))
        except Exception as e:
            # If anything goes wrong, log it but continue without filtering
            print(f"Error checking tournament filters: {e}")
            pass

    # Get games only for this team in the selected month
    team_games_query = Game.objects.filter(
        models.Q(home_team=team) | models.Q(away_team=team),
        match_date__month=month,
        match_date__year=year
    )

    # Get KSI matches for this team
    team_matches_query = Match.objects.filter(
        models.Q(home_team=team) | models.Q(away_team=team),
        match_date__month=month,
        match_date__year=year
    )

    # Apply tournament filtering if we have filters and aren't showing all
    if has_filters and not show_all and filtered_tournament_ids:
        team_matches_query = team_matches_query.filter(
            tournament__tournament_number__in=filtered_tournament_ids
        )

    # Execute queries
    team_games = team_games_query.order_by('match_date')
    team_matches = team_matches_query.order_by('match_date')

    # Get recently viewed teams (could be stored in session)
    recent_team_ids = request.session.get('recent_teams', [])
    recent_teams = Team.objects.filter(team_number__in=recent_team_ids).order_by('name') if recent_team_ids else []

    # Store this team in recently viewed
    if str(team.team_number) not in recent_team_ids:
        recent_team_ids = [str(team.team_number)] + recent_team_ids
        recent_team_ids = recent_team_ids[:5]  # Keep only 5 most recent
        request.session['recent_teams'] = recent_team_ids

    # Prepare calendar days
    days = []
    first_day_of_month = date(year, month, 1)
    first_weekday = first_day_of_month.weekday()
    last_day_of_month = calendar.monthrange(year, month)[1]

    week = []
    for _ in range(first_weekday):
        week.append(None)

    for day in range(1, last_day_of_month + 1):
        current_date = date(year, month, day)

        # Filter games for this specific day
        day_games = [g for g in team_games if g.match_date.date() == current_date]
        day_matches = [m for m in team_matches if m.match_date.date() == current_date]

        week.append({
            'date': current_date,
            'matches': day_games,
            'ksi_matches': day_matches
        })

        if len(week) == 7:
            days.append(week)
            week = []

    while len(week) < 7:
        week.append(None)
    if week:
        days.append(week)

    # Get all teams for the selector dropdown
    all_teams = get_visible_teams()

    return render(request, "matches/team_calendar.html", {
        'team': team,
        'days': days,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'recent_teams': recent_teams,
        'show_all': show_all,
        'has_filters': has_filters,
        'teams': all_teams,  # Pass all teams for the selector
    })


def search_teams(request):
    """API endpoint to search teams by name"""
    query = request.GET.get('q', '').lower()

    if len(query) < 2:
        return JsonResponse({'teams': []})

    # Search for teams that contain the query string
    teams = get_visible_teams().filter(name__icontains=query)[:10]

    results = []
    for team in teams:
        results.append({
            'team_number': team.team_number,
            'name': team.name,
            'logo': team.logo.url if team.logo else None,
            'category': team.category
        })

    return JsonResponse({'teams': results})


def todays_matches(request):
    """API endpoint to get today's matches"""
    today = timezone.now().date()

    # Get today's games
    games = Game.objects.filter(match_date__date=today)

    # Get today's KSI matches
    matches = Match.objects.filter(match_date__date=today)

    # Combine the data
    match_data = []

    for game in games:
        match_data.append({
            'home_team': game.home_team.name,
            'away_team': game.away_team.name,
            'home_team_logo': game.home_team.logo.url if game.home_team.logo else None,
            'away_team_logo': game.away_team.logo.url if game.away_team.logo else None,
            'time': game.match_date.strftime('%H:%M'),
            'tournament': game.confederation,
            'details_url': reverse('game_details', args=[game.id])
        })

    for match in matches:
        match_data.append({
            'home_team': match.home_team.name,
            'away_team': match.away_team.name,
            'home_team_logo': None,  # Assuming KSI matches don't have logos
            'away_team_logo': None,
            'time': match.match_date.strftime('%H:%M'),
            'tournament': match.tournament.name if match.tournament else 'Match',
            'details_url': reverse('match_detail', args=[match.match_number])
        })

    # Sort by time
    match_data.sort(key=lambda x: x['time'])

    return JsonResponse({'matches': match_data})


def game_calendar(request):
    month = request.GET.get('month', None)
    year = request.GET.get('year', None)
    league = request.GET.get('league', None)  # Add league filter option

    # Default to the current date if no month or year is provided
    if not month or not year:
        today = timezone.now()
        month = today.month
        year = today.year

    month = int(month)
    year = int(year)

    # Prepare calendar structure first
    days = []
    first_day_of_month = timezone.datetime(year, month, 1)
    first_weekday = first_day_of_month.weekday()
    last_day_of_month = calendar.monthrange(year, month)[1]

    week = []
    for _ in range(first_weekday):
        week.append(None)

    for day in range(1, last_day_of_month + 1):
        week.append({'date': date(year, month, day), 'matches': [], 'ksi_matches': []})

        if len(week) == 7:
            days.append(week)
            week = []

    while len(week) < 7:
        week.append(None)
    if week:
        days.append(week)

    # Now fetch the games and add them to the calendar
    # Apply league filter if provided
    game_query = Game.objects.filter(match_date__month=month, match_date__year=year)
    match_query = Match.objects.filter(match_date__month=month, match_date__year=year)

    if league:
        if league == 'men':
            game_query = game_query.filter(category='men')
            # Assuming Match model has a similar category field
            match_query = match_query.filter(tournament__name__icontains='men')
        elif league == 'women':
            game_query = game_query.filter(category='women')
            match_query = match_query.filter(tournament__name__icontains='women')

    # Process games efficiently
    for game in game_query:
        game_date = game.match_date.date()
        if game_date.month == month and game_date.year == year:
            day_index = game_date.day - 1 + first_weekday
            week_index = day_index // 7
            day_pos = day_index % 7

            if 0 <= week_index < len(days) and days[week_index][day_pos]:
                days[week_index][day_pos]['matches'].append(game)

    # Process KSI matches
    for match in match_query:
        match_date = match.match_date.date()
        if match_date.month == month and match_date.year == year:
            day_index = match_date.day - 1 + first_weekday
            week_index = day_index // 7
            day_pos = day_index % 7

            if 0 <= week_index < len(days) and days[week_index][day_pos]:
                days[week_index][day_pos]['ksi_matches'].append(match)

    return render(request, "matches/game_calendar.html", {
        'days': days,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'league': league,
    })


def gameday_text(request):
    texts = GamedayText.objects.all().order_by("time_offset")
    return render(request, "matches/gameday_text.html", {"texts": texts})


# Update the game_details view in views.py to include the goal song

def game_details(request, game_id):
    game = Game.objects.get(id=game_id)

    # Check if home team has a goal song
    goal_song_url = None
    if game.home_team.goal_song:
        goal_song_url = game.home_team.goal_song.url
        print(f"DEBUG: Home team goal song: {goal_song_url}")

    # Use the getter methods explicitly
    home_formation = game.get_home_formation()
    away_formation = game.get_away_formation()

    # Important change: Order by position_number instead of order
    # This ensures players are correctly indexed for the JavaScript positioning
    home_lineup = GameLineup.objects.filter(game=game, team=game.home_team).order_by('position_number')
    away_lineup = GameLineup.objects.filter(game=game, team=game.away_team).order_by('position_number')

    # Debug output to see what's being returned
    print(f"DEBUG: Home lineup count: {home_lineup.count()}")
    print(f"DEBUG: Away lineup count: {away_lineup.count()}")
    for i, player in enumerate(home_lineup):
        player_name = player.player.name if player.player else "Empty"
        print(f"DEBUG: Home player {i + 1}: Pos {player.position_number} - {player_name}")

    # Fetch previous games for both teams
    previous_games = Game.objects.filter(
        match_date__lt=game.match_date,
        home_team__in=[game.home_team, game.away_team],
        away_team__in=[game.home_team, game.away_team]
    ).order_by("-match_date")[:5]

    # Custom gameday text
    gamedays_text = f"Góðan daginn kæru vallargestir. Í dag er {game.match_date.strftime('%d.%m.%Y')} og við erum samankominn á leik {game.home_team} og {game.away_team} hér í hamingjunni. Endilega fáið ykkur hamborgara og bjór og verið tilbúin í þessa veislu hér rétt fram undan."

    # Staff info
    staff_jobs = GamedayJob.objects.filter(game=game)
    staff_vacancies = sum(job.vacancies() for job in staff_jobs)

    total_staff_needed = sum(job.staff_needed for job in staff_jobs)
    total_staff_assigned = total_staff_needed - staff_vacancies
    staffing_percentage = (total_staff_assigned / total_staff_needed * 100) if total_staff_needed > 0 else 0

    return render(request, "matches/game_details.html", {
        "game": game,
        "home_formation": home_formation,
        "away_formation": away_formation,
        "home_lineup": home_lineup,
        "away_lineup": away_lineup,
        "previous_games": previous_games,
        "gameday_text": gamedays_text,
        "goal_song_url": goal_song_url,
        "staff_jobs_count": staff_jobs.count(),
        "staff_vacancies": staff_vacancies,
        "staffing_percentage": staffing_percentage,
    })


def match_details(request, match_id):
    match = Game.objects.get(id=match_id)

    gameday_text = f"Góðan daginn kæru vallargestir. Í dag er {match.match_date.strftime('%d.%m.%Y')} og við erum samankominn á leik {match.home_team} og {match.away_team} hér í hamingjunni. Endilega fáið ykkur hamborgara og bjór og verið tilbúin í þessa veislu hér rétt fram undan."

    return render(request, "matches/match_details.html", {
        "match": match,
        "gameday_text": gameday_text,
    })


@login_required
def change_username(request):
    if request.method == "POST":
        form = UsernameChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your username has been updated successfully!")
            return redirect("home")  # Redirect to homepage after successful change
    else:
        form = UsernameChangeForm(instance=request.user)

    return render(request, "matches/change_username.html", {"form": form})


def league_table(request, category):
    if category not in ['men', 'women']:
        category = 'men'

    # Your existing standings calculation
    standings = calculate_league_table(category)

    # Get KSI tournament standings
    # For example, you could use the first tournament from the database:
    tournament = Tournament.objects.first()
    if tournament:
        ksi_standings = TournamentStanding.objects.filter(tournament=tournament).order_by('-points', '-goal_difference')
    else:
        ksi_standings = []

    return render(request, "matches/league_table.html", {
        "standings": standings,
        "ksi_standings": ksi_standings,
        "category": category,
    })


def teams_overview(request, category):
    # Get all teams for the given category (either 'men' or 'women'), sorted alphabetically by name
    teams = Tournament.objects.filter(tournament_number=tournament_list(request)).order_by('name')

    # Get KSI teams
    # Note: You may need to map/filter KSI teams to the appropriate category since they might use different categories
    # ksi_teams = []
    # for team in Team.objects.all():
    #     if (category == 'men' and team.category != 'women') or (category == 'women' and team.category == 'women'):
    #         ksi_teams.append(team)

    return render(request, "matches/teams_overview.html", {
        'teams': teams,
    })


def team_details(request, team_id):
    team = get_object_or_404(Team, id=team_id)

    # Sort players by position order: GK, DEF, MID, FW
    players = team.players.order_by(
        models.Case(
            models.When(position='GK', then=0),
            models.When(position='DEF', then=1),
            models.When(position='MID', then=2),
            models.When(position='FW', then=3),
            default=4,
            output_field=models.IntegerField()
        )
    )

    return render(request, "matches/team_details.html", {
        'team': team,
        'players': players,
    })


def user_login(request):
    teams = get_visible_teams()

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        selected_team_id = request.POST.get("selected_team", None)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Store the selected team in the session if provided
            if selected_team_id:
                try:
                    team = Team.objects.get(id=selected_team_id)
                    request.session['selected_team_id'] = team.id
                    request.session['selected_team_name'] = team.name
                except Team.DoesNotExist:
                    pass

            # Check for a redirect URL saved in the session
            redirect_url = request.session.get('redirect_after_team_selection')
            if redirect_url:
                # Clear the redirect URL from the session
                del request.session['redirect_after_team_selection']
                return redirect(redirect_url)

            # Otherwise go to home
            return redirect("home")
        else:
            return render(request, "registration/login.html", {
                "error": "Invalid username or password.",
                "teams": teams
            })

    return render(request, "registration/login.html", {
        "teams": teams
    })


def register(request):
    teams = get_visible_teams()

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        selected_team_id = request.POST.get("selected_team", None)

        if User.objects.filter(username=username).exists():
            return render(request, "registration/register.html", {
                "error": "Username already exists!",
                "teams": get_visible_teams()
            })

        user = User.objects.create_user(username=username, password=password)
        login(request, user)  # Automatically log in new users

        # Store the selected team in the session if provided
        if selected_team_id:
            try:
                team = Team.objects.get(id=selected_team_id)
                request.session['selected_team_id'] = team.id
                request.session['selected_team_name'] = team.name
            except Team.DoesNotExist:
                pass

        return redirect(request, "registration/register.html", {
            "error": "Username already exists",
            "teams": teams
        })  # Redirect to homepage

    return render(request, "registration/register.html", {
        "teams": teams
    })


def fantasy_home(request):
    return render(request, "fantasy/fantasy_home.html")


def edit_formation(request, game_id):
    """ View for editing the formation lineup """
    game = get_object_or_404(Game, id=game_id)

    print(f"EDIT FORMATION DEBUG - Before processing:")
    print(f"Game ID: {game.id}")
    print(f"Home formation: {game.home_formation}")
    print(f"Away formation: {game.away_formation}")

    if request.method == "POST":
        # Check if we're updating formations
        home_formation = request.POST.get('home_formation')
        away_formation = request.POST.get('away_formation')

        if home_formation and away_formation:
            print(f"Saving formations: Home={home_formation}, Away={away_formation}")
            game.home_formation = home_formation
            game.away_formation = away_formation
            game.save()
            return redirect('edit_formation', game_id=game_id)

        # Handle form submission for player assignment
        lineup_id = request.POST.get('lineup_id')
        player_number = request.POST.get('player_number')

        if lineup_id and player_number:
            lineup = get_object_or_404(GameLineup, id=lineup_id)
            # Use player_number instead of id
            player = get_object_or_404(Player, player_number=player_number)
            lineup.player = player
            lineup.save()
            return redirect('edit_formation', game_id=game_id)

    # Fetch updated lineups
    home_lineup = GameLineup.objects.filter(game=game, team=game.home_team).order_by("position_number")
    away_lineup = GameLineup.objects.filter(game=game, team=game.away_team).order_by("position_number")

    # Get all players for both teams, including all position fields
    # Update the field names in the values() call
    home_players = list(Player.objects.filter(team=game.home_team).values(
        "player_number", "name", "position", "secondary_position", "third_position"
    ))
    away_players = list(Player.objects.filter(team=game.away_team).values(
        "player_number", "name", "position", "secondary_position", "third_position"
    ))

    return render(request, "admin/edit_formation.html", {
        "game": game,
        "home_lineup": home_lineup,
        "away_lineup": away_lineup,
        "home_players": home_players,
        "away_players": away_players,
        "home_formation": game.home_formation,
        "away_formation": game.away_formation,
        "formation_choices": Team.FORMATION_CHOICES
    })


def start_lineup(request, game_id):
    """ Step 1: Select the game before entering lineup selection """
    game = get_object_or_404(Game, id=game_id)

    if request.method == "POST":
        return redirect(reverse("edit_formation", args=[game.id]))

    return render(request, "admin/start_lineup.html", {
        "game": game,
    })


def update_formations(request, game_id):
    """Dedicated view for updating formations"""
    if request.method == "POST":
        game = get_object_or_404(Game, id=game_id)

        # Get formations from POST data
        home_formation = request.POST.get('home_formation')
        away_formation = request.POST.get('away_formation')

        # Debug output
        print(f"UPDATE FORMATIONS DEBUG:")
        print(f"  Game ID: {game_id}")
        print(f"  Home formation (before): {game.home_formation}")
        print(f"  Away formation (before): {game.away_formation}")
        print(f"  Home formation (new): {home_formation}")
        print(f"  Away formation (new): {away_formation}")

        # Update and save
        if home_formation and away_formation:
            game.home_formation = home_formation
            game.away_formation = away_formation
            game.save()

            # Verify save
            game_refreshed = Game.objects.get(id=game_id)
            print(f"  Home formation (after save): {game_refreshed.home_formation}")
            print(f"  Away formation (after save): {game_refreshed.away_formation}")

            messages.success(request, "Formations updated successfully!")

        return redirect('edit_formation', game_id=game_id)

    # Redirect to edit_formation if accessed directly
    return redirect('edit_formation', game_id=game_id)


def get_home_formation(self):
    # If home_formation exists and isn't empty, return it
    if self.home_formation and self.home_formation != "":
        return self.home_formation
    # Otherwise fall back to the team's default
    return self.home_team.default_formation


def get_away_formation(self):
    # If away_formation exists and isn't empty, return it
    if self.away_formation and self.away_formation != "":
        return self.away_formation
    # Otherwise fall back to the team's default
    return self.away_team.default_formation


# Add to views.py
# In views.py
@login_required
def manage_default_lineup(request, team_id):
    team = get_object_or_404(Team, id=team_id)

    # Get all players for this team
    players = Player.objects.filter(team=team).order_by('position', 'last_name')

    # Create position slots based on the team's default formation
    formation = team.default_formation
    position_slots = []

    # Helper function for position type
    def get_position_type(position_number, formation):
        if position_number == 1:
            return 'GK'

        parts = formation.split('-')
        defender_count = int(parts[0])

        # Calculate midfielder count - handle formations with multiple midfielder rows
        midfielder_count = 0
        for i in range(1, len(parts) - 1):
            midfielder_count += int(parts[i])

        if 2 <= position_number <= defender_count + 1:
            return 'DEF'
        elif position_number <= defender_count + midfielder_count + 1:
            return 'MID'
        else:
            return 'FW'

    # Map positions based on formation
    for position_number in range(1, 12):
        # Get currently assigned player
        player_id = team.default_lineup_data.get(str(position_number))
        assigned_player = None
        if player_id:
            try:
                assigned_player = Player.objects.get(id=player_id)
            except Player.DoesNotExist:
                pass

        # Determine position type (GK, DEF, MID, FW)
        position_type = get_position_type(position_number, formation)

        position_slots.append({
            'position_number': position_number,
            'position_type': position_type,
            'assigned_player': assigned_player
        })

    if request.method == 'POST':
        # Process form submission
        new_lineup = {}
        for position_number in range(1, 12):
            player_id = request.POST.get(f'player_{position_number}')
            if player_id and player_id != 'none':
                new_lineup[str(position_number)] = int(player_id)

        # Save the new lineup
        team.default_lineup_data = new_lineup
        team.save()
        messages.success(request, f"Default lineup saved for {team.name}")
        return redirect('manage_default_lineup', team_id=team_id)

    return render(request, 'admin/manage_default_lineup.html', {
        'team': team,
        'position_slots': position_slots,
        'players': players,
        'formation': formation
    })


def get_position_type_for_number(position_number, formation):
    """Helper function to determine position type based on formation"""
    if position_number == 1:
        return 'GK'

    parts = formation.split('-')
    defender_count = int(parts[0])
    midfielder_count = sum(int(part) for part in parts[1:-1]) if len(parts) > 2 else int(parts[1])

    if 2 <= position_number <= defender_count + 1:
        return 'DEF'
    elif position_number <= defender_count + midfielder_count + 1:
        return 'MID'
    else:
        return 'FW'


# Add this new view function to views.py

def welcome(request):
    """Welcome page with team selection."""
    # Replace: teams = Team.objects.all().order_by('name')
    teams = get_visible_teams()

    # Rest of the function remains the same
    if request.user.is_authenticated:
        query_string = request.META.get('QUERY_STRING', '')
        if query_string:
            return redirect(f'/home/?{query_string}')
        else:
            return redirect('home')

    return render(request, 'matches/welcome.html', {
        'teams': teams,
    })


# Update the user_login view to handle team selection


@login_required
def change_team(request):
    """Allow authenticated users to change their selected team."""
    # Replace: teams = Team.objects.all().order_by('name')
    teams = get_visible_teams()

    # Rest of the function remains the same
    if request.method == "POST":
        selected_team_id = request.POST.get("selected_team")
        if selected_team_id:
            try:
                team = Team.objects.get(team_number=selected_team_id)  # Use team_number as primary key
                request.session['selected_team_id'] = team.team_number
                request.session['selected_team_name'] = team.name
                messages.success(request, f"You are now supporting {team.name}!")
                redirect_url = request.GET.get('next', 'home')
                return redirect(redirect_url)
            except Team.DoesNotExist:
                messages.error(request, "Selected team does not exist.")

    return render(request, 'matches/change_team.html', {
        'teams': teams,
    })



def tournament_list(request):
    tournaments = Tournament.objects.all()
    return render(request, 'matches/tournament_list.html', {'tournaments': tournaments})


def tournament_detail(request, tournament_id):
    tournament = get_object_or_404(Tournament, tournament_number=tournament_id)
    standings = TournamentStanding.objects.filter(tournament=tournament).order_by('-points', '-goal_difference')

    # Get upcoming matches
    upcoming_matches = Match.objects.filter(
        tournament=tournament,
        match_date__gte=timezone.now()
    ).order_by('match_date')[:5]

    # Get recent results
    recent_matches = Match.objects.filter(
        tournament=tournament,
        match_date__lt=timezone.now(),
        home_score__isnull=False,
        away_score__isnull=False
    ).order_by('-match_date')[:5]

    context = {
        'tournament': tournament,
        'standings': standings,
        'upcoming_matches': upcoming_matches,
        'recent_matches': recent_matches
    }
    return render(request, 'matches/tournament_detail.html', context)


def match_detail(request, match_id):
    match = get_object_or_404(Match, match_number=match_id)
    events = MatchEvent.objects.filter(match=match).order_by('minute')
    return render(request, "matches/match_detail.html", {'match': match, 'events': events})


def team_detail(request, team_id):
    team = get_object_or_404(Team, team_number=team_id)

    # Get upcoming matches
    upcoming_matches = Match.objects.filter(
        match_date__gte=timezone.now(),
        home_team=team
    ).order_by('match_date')[:5]

    upcoming_matches = upcoming_matches.union(
        Match.objects.filter(
            match_date__gte=timezone.now(),
            away_team=team
        ).order_by('match_date')[:5]
    )

    # Get recent results
    recent_matches = Match.objects.filter(
        match_date__lt=timezone.now(),
        home_score__isnull=False,
        away_score__isnull=False,
        home_team=team
    ).order_by('-match_date')[:5]

    recent_matches = recent_matches.union(
        Match.objects.filter(
            match_date__lt=timezone.now(),
            home_score__isnull=False,
            away_score__isnull=False,
            away_team=team
        ).order_by('-match_date')[:5]
    )

    # Get team standings in different tournaments
    standings = TournamentStanding.objects.filter(team=team)

    context = {
        'team': team,
        'upcoming_matches': upcoming_matches,
        'recent_matches': recent_matches,
        'standings': standings
    }
    return render(request, 'matches/team_detail.html', context)


def player_detail(request, player_id):
    player = get_object_or_404(Player, player_number=player_id)
    events = MatchEvent.objects.filter(player=player).order_by('-match__match_date')

    context = {
        'player': player,
        'events': events
    }
    return render(request, 'matches/player_detail.html', context)


def tournament_selection(request):
    tournaments = Tournament.objects.all().order_by('name')
    return render(request, "matches/tournament_selection.html", {'tournaments': tournaments})


# Add these imports at the top of views.py if not already present
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Game, GamedayJob, GamedayStaffAssignment
from .forms import GamedayJobForm, GamedayStaffAssignmentForm
import json


@login_required
def gameday_staff(request, game_id):
    """Main view for managing gameday staff"""
    game = get_object_or_404(Game, id=game_id)
    jobs = GamedayJob.objects.filter(game=game).order_by('job_name', 'location')

    # Create job form for adding new jobs
    job_form = GamedayJobForm()

    # Calculate jobs with vacancies for the ticker
    jobs_with_vacancies = [
        {'job': job, 'vacancies': job.vacancies()}
        for job in jobs if job.vacancies() > 0
    ]

    # Get total staffing stats
    total_staff_needed = sum(job.staff_needed for job in jobs)
    total_staff_assigned = sum(job.assigned_staff_count() for job in jobs)
    total_vacancies = total_staff_needed - total_staff_assigned
    staffing_percentage = (total_staff_assigned / total_staff_needed * 100) if total_staff_needed > 0 else 0

    return render(request, 'matches/gameday_staff.html', {
        'game': game,
        'jobs': jobs,
        'jobs_with_vacancies': jobs_with_vacancies,
        'job_form': job_form,
        'total_staff_needed': total_staff_needed,
        'total_staff_assigned': total_staff_assigned,
        'total_vacancies': total_vacancies,
        'staffing_percentage': staffing_percentage,
    })


@login_required
def add_gameday_job(request, game_id):
    """Add a new job for a game"""
    game = get_object_or_404(Game, id=game_id)

    if request.method == 'POST':
        form = GamedayJobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.game = game
            job.save()
            messages.success(request, f"Added job: {job.job_name} at {job.location}")

            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'job_id': job.id,
                    'job_name': job.job_name,
                    'location': job.location,
                    'staff_needed': job.staff_needed,
                    'assigned_staff': 0,
                    'vacancies': job.staff_needed
                })

            return redirect('gameday_staff', game_id=game_id)
        else:
            messages.error(request, "Error adding job. Please check the form.")

    # If GET or invalid form, redirect back to main page
    return redirect('gameday_staff', game_id=game_id)


@login_required
def edit_gameday_job(request, game_id, job_id):
    """Edit an existing job"""
    job = get_object_or_404(GamedayJob, id=job_id, game__id=game_id)

    if request.method == 'POST':
        form = GamedayJobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated job: {job.job_name}")

            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'job_id': job.id,
                    'job_name': job.job_name,
                    'location': job.location,
                    'staff_needed': job.staff_needed,
                    'assigned_staff': job.assigned_staff_count(),
                    'vacancies': job.vacancies()
                })

    return redirect('gameday_staff', game_id=game_id)


@login_required
def edit_gameday_staff(request, game_id, assignment_id):
    """Edit an existing staff assignment"""
    assignment = get_object_or_404(GamedayStaffAssignment, id=assignment_id, job__game__id=game_id)

    if request.method == 'POST':
        form = GamedayStaffAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated assignment for {assignment.person_name}")

            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'job_id': assignment.job.id,
                    'assignment_id': assignment.id,
                    'person_name': assignment.person_name,
                    'contact_info': assignment.contact_info or '',
                    'notes': assignment.notes or '',
                })

    return redirect('gameday_staff', game_id=game_id)


@login_required
def delete_gameday_job(request, game_id, job_id):
    """Delete a job and all its assignments"""
    job = get_object_or_404(GamedayJob, id=job_id, game__id=game_id)
    job_name = job.job_name
    job.delete()
    messages.success(request, f"Deleted job: {job_name}")

    # Return JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True
        })

    return redirect('gameday_staff', game_id=game_id)


@login_required
def assign_gameday_staff(request, game_id, job_id):
    """Assign a person to a job"""
    job = get_object_or_404(GamedayJob, id=job_id, game__id=game_id)

    if request.method == 'POST':
        form = GamedayStaffAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.job = job
            assignment.save()
            messages.success(request, f"Added {assignment.person_name} to {job.job_name}")

            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'job_id': job.id,
                    'vacancies': job.vacancies(),
                    'assignment_id': assignment.id,
                    'person_name': assignment.person_name,
                    'contact_info': assignment.contact_info or '',
                    'assigned_staff': job.assigned_staff_count()
                })

    return redirect('gameday_staff', game_id=game_id)


@login_required
def remove_gameday_staff(request, game_id, assignment_id):
    """Remove a person from a job"""
    assignment = get_object_or_404(GamedayStaffAssignment, id=assignment_id, job__game__id=game_id)
    job = assignment.job
    person_name = assignment.person_name
    assignment.delete()

    messages.success(request, f"Removed {person_name} from {job.job_name}")

    # Return JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'job_id': job.id,
            'vacancies': job.vacancies(),
            'assigned_staff': job.assigned_staff_count()
        })

    return redirect('gameday_staff', game_id=game_id)


@login_required
def gameday_staff_search(request, game_id):
    """Search for staff members by name"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'results': []})

        # Get all staff assignments across all games with matching names
        staff = GamedayStaffAssignment.objects.filter(
            person_name__icontains=query
        ).values('person_name', 'contact_info').distinct()[:10]

        results = list(staff)
        return JsonResponse({'results': results})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def get_job_staff(request, game_id, job_id):
    """API endpoint to get all staff assigned to a specific job"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        job = get_object_or_404(GamedayJob, id=job_id, game__id=game_id)
        staff = job.staff_assignments.all()

        data = [{
            'id': a.id,
            'name': a.person_name,
            'contact_info': a.contact_info or '',
            'notes': a.notes or '',
        } for a in staff]

        return JsonResponse({
            'job_id': job.id,
            'job_name': job.job_name,
            'location': job.location,
            'staff_needed': job.staff_needed,
            'vacancies': job.vacancies(),
            'staff': data
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_visible_teams():
    """
    Helper function to get only teams that should be visible to users,
    ordered by display priority
    """
    # Add a print statement for debugging
    teams = Team.objects.filter(
        visibility__visible_to_users=True
    ).order_by('visibility__display_priority', 'name')

    # Print debug info
    print(f"DEBUG: Filtered visible teams: {teams.count()} teams")
    for team in teams:
        print(f"DEBUG: Visible team: {team.name} (ID: {team.team_number})")

    # If no visible teams are found, print all teams for debugging
    if teams.count() == 0:
        print("DEBUG: No visible teams found. Listing all teams:")
        all_teams = Team.objects.all()
        for team in all_teams:
            try:
                visible = team.visibility.visible_to_users
                print(f"DEBUG: Team {team.name} (ID: {team.team_number}) visibility: {visible}")
            except AttributeError:
                print(f"DEBUG: Team {team.name} (ID: {team.team_number}) has no visibility settings")

    return teams

@receiver(post_save, sender=Team)
def create_team_visibility(sender, instance, created, **kwargs):
    """
    When a new team is created, automatically create a TeamVisibility record
    making it visible by default.
    """
    if created:
        TeamVisibility.objects.create(team=instance)

@receiver(post_save, sender=Team)
def save_team_visibility(sender, instance, **kwargs):
    """
    Make sure TeamVisibility is saved when Team is saved
    """
    if not hasattr(instance, 'visibility'):
        TeamVisibility.objects.create(team=instance)


def start_lineup_match(request, match_number):
    """Step 1: Select the match before entering lineup selection"""
    match = get_object_or_404(Match, match_number=match_number)

    # Create a Game object if it doesn't exist for this match
    game, created = Game.objects.get_or_create(
        home_team=match.home_team,
        away_team=match.away_team,
        match_date=match.match_date,
        defaults={
            'category': 'men' if 'men' in match.tournament.name.lower() else 'women',
            'confederation': match.tournament.name
        }
    )

    if request.method == "POST":
        return redirect(reverse("edit_formation", args=[game.id]))

    return render(request, "admin/start_lineup.html", {
        "match": match,
        "game": game,
    })


@require_POST
@csrf_exempt  # Only use this if you're having CSRF issues - better to fix CSRF properly
def assign_player(request):
    lineup_id = request.POST.get('lineup_id')
    player_number = request.POST.get('player_number')
    position_number = request.POST.get('position_number')

    if not all([lineup_id, player_number, position_number]):
        return JsonResponse({'success': False, 'error': 'Missing required parameters'}, status=400)

    try:
        # Get the lineup slot
        lineup_slot = LineupSlot.objects.get(id=lineup_id)

        # Get the player
        player = Player.objects.get(player_number=player_number, team=lineup_slot.team)

        # Clear this player from any other positions
        LineupSlot.objects.filter(
            lineup__game=lineup_slot.lineup.game,
            player=player
        ).exclude(id=lineup_slot.id).update(player=None)

        # Assign the player to this position
        lineup_slot.player = player
        lineup_slot.save()

        return JsonResponse({
            'success': True,
            'player_name': player.name,
            'player_number': player.player_number
        })

    except LineupSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lineup slot not found'}, status=404)
    except Player.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Player not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
