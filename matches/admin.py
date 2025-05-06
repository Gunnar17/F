from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.contrib.auth.models import Group
from .models import Team, Game, Player, GameLineup, Match, GamedayJob, GamedayStaffAssignment, TeamTournamentFilter, Tournament, TournamentStanding, TeamVisibility


class MatchTeamFilter(admin.SimpleListFilter):
    title = 'Any Team'
    parameter_name = 'team'

    def lookups(self, request, model_admin):
        teams = Team.objects.all().order_by('name')
        return [(team.team_number, team.name) for team in teams]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                models.Q(home_team__team_number=self.value()) |
                models.Q(away_team__team_number=self.value())
            )
        return queryset


class TeamFilter(admin.SimpleListFilter):
    title = 'Any Team'
    parameter_name = 'team'

    def lookups(self, request, model_admin):
        teams = Team.objects.all().order_by('name')
        return [(team.team_number, team.name) for team in teams]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                models.Q(home_team__team_number=self.value()) |
                models.Q(away_team__team_number=self.value())
            )
        return queryset


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('home_team', 'away_team', 'match_date', 'tournament', 'start_lineup_button')
    list_filter = (MatchTeamFilter, 'tournament', 'home_team', 'away_team')
    search_fields = ('home_team__name', 'away_team__name', 'tournament__name')
    date_hierarchy = 'match_date'

    def start_lineup_button(self, obj):
        """Button to start lineup selection"""
        return format_html(
            '<a class="button" href="{}">Select Lineup</a>',
            reverse('start_lineup_match', args=[obj.match_number])
        )

    start_lineup_button.short_description = "Select Lineup"


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'secondary_position', 'third_position', 'team', 'shirt_number')
    list_filter = ('team','position', 'secondary_position', 'third_position')


class GameLineupInline(admin.TabularInline):
    model = GameLineup
    extra = 0  # Don't auto-generate extra slots


class TeamTournamentFilterInline(admin.TabularInline):
    model = TeamTournamentFilter
    extra = 1


# Update the TeamAdmin class in admin.py

class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'default_formation', 'manage_default_lineup_link', 'has_goal_song', 'is_visible_to_users')
    list_filter = ('category', 'visibility__visible_to_users')
    inlines = [TeamTournamentFilterInline]
    actions = ['make_visible_to_users', 'hide_from_users']

    def manage_default_lineup_link(self, obj):
        url = reverse('manage_default_lineup', args=[obj.pk])
        return format_html('<a href="{}" class="button">Manage Default Lineup</a>', url)

    def has_goal_song(self, obj):
        if obj.goal_song:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')

    def is_visible_to_users(self, obj):
        """Display if this team is visible in user selection menus"""
        try:
            if obj.visibility.visible_to_users:
                return format_html('<span style="color: green;">✓</span>')
            return format_html('<span style="color: red;">✗</span>')
        except AttributeError:
            return format_html('<span style="color: orange;">?</span>')

    def make_visible_to_users(self, request, queryset):
        """Bulk action to make teams visible to users"""
        for team in queryset:
            visibility, created = TeamVisibility.objects.get_or_create(team=team)
            visibility.visible_to_users = True
            visibility.save()

        self.message_user(request, f"{queryset.count()} teams are now visible to users in selection menus.")

    make_visible_to_users.short_description = "Make teams visible to users"

    def hide_from_users(self, request, queryset):
        """Bulk action to hide teams from users"""
        for team in queryset:
            visibility, created = TeamVisibility.objects.get_or_create(team=team)
            visibility.visible_to_users = False
            visibility.save()

        self.message_user(request, f"{queryset.count()} teams are now hidden from users in selection menus.")

    hide_from_users.short_description = "Hide teams from users"

    has_goal_song.short_description = 'Goal Song'
    manage_default_lineup_link.short_description = 'Default Lineup'
    is_visible_to_users.short_description = 'Visible to Users'

    fieldsets = (
        ("Team Info", {"fields": ("name", "category", "logo", "default_formation")}),
        ("Media", {"fields": ("goal_song",)}),
    )


admin.site.register(Team, TeamAdmin)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'tournament_number', 'start_date')
    search_fields = ('name',)


@admin.register(TournamentStanding)
class TournamentStandingAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'team', 'matches_played', 'matches_won', 'matches_drawn',
                    'matches_lost', 'goals_scored', 'goals_conceded', 'points')
    list_filter = ('tournament',)
    search_fields = ('team__name', 'tournament__name')


class TeamFilter(admin.SimpleListFilter):
    title = 'Any Team'
    parameter_name = 'team'

    def lookups(self, request, model_admin):
        teams = Team.objects.all().order_by('name')
        return [(team.team_number, team.name) for team in teams]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                models.Q(home_team__team_number=self.value()) |
                models.Q(away_team__team_number=self.value())
            )
        return queryset


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("home_team", "away_team", "match_date", "confederation", "category", "played", "start_lineup_button")
    list_filter = (TeamFilter, "category", "played", "confederation", "home_team", "away_team")
    search_fields = ("home_team__name", "away_team__name", "confederation")
    date_hierarchy = "match_date"

    fieldsets = (
        ("Game Info", {"fields": ("home_team", "away_team", "match_date", "category", "confederation")}),
        ("Match Results", {"fields": ("played", "home_goals", "away_goals")}),
        ("Cards", {"fields": ("home_yellow_cards", "away_yellow_cards", "home_red_cards", "away_red_cards")}),
    )

    def start_lineup_button(self, obj):
        """ ✅ Button to start lineup selection ✅ """
        return format_html(
            '<a class="button" href="{}">Select Lineup</a>',
            reverse('start_lineup', args=[obj.id])
        )

    start_lineup_button.short_description = "Start Lineup Selection"
    readonly_fields = ["start_lineup_button"]


class GameLineupForm(forms.ModelForm):
    """ Custom form to filter players based on the selected game, team, and position. """

    class Meta:
        model = GameLineup
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fetch team and position from the form
        team = self.initial.get("team") or self.data.get("team")
        position = self.initial.get("position") or self.data.get("position")

        print(f"DEBUG: Selected Team: {team}, Selected Position: {position}")  # ✅ Debugging Output

        # Convert team ID to an integer
        try:
            team = int(team) if team else None
        except ValueError:
            team = None

        # Only filter players when team and position are selected
        if team and position:
            self.fields["player"].queryset = Player.objects.filter(team_id=team, position=position)
        else:
            self.fields["player"].queryset = Player.objects.none()  # Empty dropdown initially


class GameLineupAdmin(admin.ModelAdmin):
    form = GameLineupForm
    list_display = ("game", "team", "position", "player")
    list_filter = ("game", "team", "position")

    class Media:
        js = ("admin/js/game_lineup_filter.js",)  # ✅ Attach JavaScript file to reload players dynamically


admin.site.register(GameLineup, GameLineupAdmin)


class GamedayStaffAssignmentInline(admin.TabularInline):
    model = GamedayStaffAssignment
    extra = 0


@admin.register(GamedayJob)
class GamedayJobAdmin(admin.ModelAdmin):
    list_display = ('job_name', 'location', 'game', 'staff_needed', 'assigned_staff_count', 'vacancies')
    list_filter = ('game__match_date', 'job_name')
    search_fields = ('job_name', 'location', 'game__home_team__name', 'game__away_team__name')
    inlines = [GamedayStaffAssignmentInline]

    def assigned_staff_count(self, obj):
        return obj.assigned_staff_count()

    def vacancies(self, obj):
        return obj.vacancies()


@admin.register(TeamTournamentFilter)
class TeamTournamentFilterAdmin(admin.ModelAdmin):
    list_display = ('team', 'tournament', 'is_main_tournament')
    list_filter = ('is_main_tournament', 'tournament', 'team')
    search_fields = ('team__name', 'tournament__name')


# Add to admin.py

@admin.register(TeamVisibility)
class TeamVisibilityAdmin(admin.ModelAdmin):
    list_display = ('team', 'visible_to_users', 'display_priority')
    list_filter = ('visible_to_users',)
    search_fields = ('team__name',)
    list_editable = ('visible_to_users', 'display_priority')

    actions = ['make_visible', 'make_hidden', 'export_visible_teams']

    def make_visible(self, request, queryset):
        queryset.update(visible_to_users=True)
        self.message_user(request, f"{queryset.count()} teams are now visible to users.")

    make_visible.short_description = "Make selected teams visible to users"

    def make_hidden(self, request, queryset):
        queryset.update(visible_to_users=False)
        self.message_user(request, f"{queryset.count()} teams are now hidden from users.")

    def export_visible_teams(self, request, queryset):
        """Export visible teams to JSON file for templates"""
        from django.core.management import call_command

        call_command('export_visible_teams')

        self.message_user(
            request,
            "Visible teams exported to JSON file. Changes are now live on the site."
        )
    export_visible_teams.short_description = "Export visible teams (apply changes to site)"

    make_hidden.short_description = "Hide selected teams from users"



    
