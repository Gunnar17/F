from django.db import models
from django.db.models.signals import post_save
from django.utils.timezone import now
from django.dispatch import receiver


CATEGORY_CHOICES = [
    ("men", "Men"),
    ("women", "Women"),
]

FORMATION_CHOICES = [
    # 3 at the back
    ("3-4-1-2", "3-4-1-2"),
    ("3-1-4-2", "3-1-4-2"),
    ("3-4-2-1", "3-4-2-1"),
    ("3-4-3", "3-4-3"),
    ("3-5-1-1", "3-5-1-1"),
    ("3-5-2", "3-5-2"),

    # 4 at the back
    ("4-1-2-1-2", "4-1-2-1-2"),
    ("4-1-2-3", "4-1-2-3"),
    ("4-1-3-2", "4-1-3-2"),
    ("4-1-4-1", "4-1-4-1"),
    ("4-2-1-3", "4-2-1-3"),
    ("4-2-2-2", "4-2-2-2"),
    ("4-2-3-1", "4-2-3-1"),
    ("4-2-4", "4-2-4"),
    ("4-3-1-2", "4-3-1-2"),
    ("4-3-2-1", "4-3-2-1"),
    ("4-3-3", "4-3-3"),
    ("4-4-1-1", "4-4-1-1"),
    ("4-4-2", "4-4-2"),
    ("4-5-1", "4-5-1"),

    # 5 at the back
    ("5-2-1-2", "5-2-1-2"),
    ("5-2-2-1", "5-2-2-1"),
    ("5-2-3", "5-2-3"),
    ("5-3-2", "5-3-2"),
    ("5-4-1", "5-4-1"),
]


# class Lineup(models.Model):
#     game = models.ForeignKey('Game', on_delete=models.CASCADE)
#     team = models.ForeignKey('Team', on_delete=models.CASCADE)
#     formation = models.CharField(max_length=10)
#
#     class Meta:
#         unique_together = ('game', 'team')
#
#
#
# class LineupSlot(models.Model):
#     lineup = models.ForeignKey(Lineup, on_delete=models.CASCADE)
#     position_number = models.IntegerField()
#     position = models.CharField(max_length=3, choices=[
#         ('GK', 'Goalkeeper'),
#         ('DEF', 'Defender'),
#         ('MID', 'Midfielder'),
#         ('FW', 'Forward')
#     ])
#     player = models.ForeignKey('Player', null=True, blank=True, on_delete=models.SET_NULL)
#
#     class Meta:
#         unique_together = ('lineup', 'position_number')



class GameDay(models.Model):
    game = models.OneToOneField('Game', on_delete=models.CASCADE, related_name="gameday")
    intro_announcement = models.TextField(default="Welcome to today's match!")
    halftime_announcement = models.TextField(default="It's halftime. Get your snacks!")
    fulltime_announcement = models.TextField(default="Full-time. Thank you for coming!")
    goal_audio = models.FileField(upload_to='audio/', blank=True, null=True)  # Goal song file
    sponsor_audio = models.FileField(upload_to='audio/', blank=True, null=True)  # Sponsor ads
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GameDay Settings for {self.game}"


# class MatchEvent(models.Model):
#     EVENT_TYPES = [
#         ('goal', 'Goal'),
#         ('yellow_card', 'Yellow Card'),
#         ('red_card', 'Red Card'),
#         ('substitution', 'Substitution'),
#     ]
#
#     game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name="events")
#     event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
#     player_name = models.CharField(max_length=100)
#     team = models.ForeignKey('Team', on_delete=models.CASCADE)
#     event_time = models.DateTimeField(default=now)
#
#     def __str__(self):
#         return f"{self.event_type} - {self.player_name} at {self.event_time.strftime('%H:%M')}"


class Team(models.Model):
    FORMATION_CHOICES = [
        # 3 at the back
        ("3-4-1-2", "3-4-1-2"),
        ("3-1-4-2", "3-1-4-2"),
        ("3-4-2-1", "3-4-2-1"),
        ("3-4-3", "3-4-3"),
        ("3-5-1-1", "3-5-1-1"),
        ("3-5-2", "3-5-2"),

        # 4 at the back
        ("4-1-2-1-2", "4-1-2-1-2"),
        ("4-1-2-3", "4-1-2-3"),
        ("4-1-3-2", "4-1-3-2"),
        ("4-1-4-1", "4-1-4-1"),
        ("4-2-1-3", "4-2-1-3"),
        ("4-2-2-2", "4-2-2-2"),
        ("4-2-3-1", "4-2-3-1"),
        ("4-2-4", "4-2-4"),
        ("4-3-1-2", "4-3-1-2"),
        ("4-3-2-1", "4-3-2-1"),
        ("4-3-3", "4-3-3"),
        ("4-4-1-1", "4-4-1-1"),
        ("4-4-2", "4-4-2"),
        ("4-5-1", "4-5-1"),

        # 5 at the back
        ("5-2-1-2", "5-2-1-2"),
        ("5-2-2-1", "5-2-2-1"),
        ("5-2-3", "5-2-3"),
        ("5-3-2", "5-3-2"),
        ("5-4-1", "5-4-1"),
    ]
    team_number = models.IntegerField(primary_key=True, default='123')
    name = models.CharField(max_length=255, default='debug needed')  # Remove the unique=True here
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="men")
    logo = models.ImageField(upload_to='team_logos/', blank=True, null=True)
    default_formation = models.CharField(max_length=10, choices=FORMATION_CHOICES, default='4-4-2')
    goal_song = models.FileField(upload_to='goal_songs/', blank=True, null=True)


    # Add this new field for default lineup
    default_lineup_data = models.JSONField(default=dict, blank=True)

    # def __str__(self):
    #     return f"{self.name} ({self.default_formation})"

    def __str__(self):
        return self.name

    def get_default_player_for_position(self, position_number):
        """Get the player ID for a specific position number in the default lineup"""
        position_key = str(position_number)  # Convert to string for JSON keys
        player_id = self.default_lineup_data.get(position_key)
        if player_id:
            try:
                return Player.objects.get(id=player_id)
            except Player.DoesNotExist:
                return None
        return None


class Game(models.Model):
    home_team = models.ForeignKey(Team, related_name="home_games", on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name="away_games", on_delete=models.CASCADE)
    match_date = models.DateTimeField()
    CATEGORY_CHOICES = [('men', 'Men'), ('women', 'Women')]
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    confederation = models.CharField(
        max_length=20,
        default='Besta deildin',
        choices=[
            ('league_men', 'Besta deild karl'),
            ('league_women', 'Besta deild kvenna'),
            ('cup_men', 'Mjólkurbikar karla'),
            ('cup_women', 'Mjólkurbikar kvenna'),
            ('europe_men', 'Evrópa karla'),
            ('europe_women', 'Evrópa kvenna'),
            ('friendly_men', 'Vináttuleikur karla'),
            ('friendly_women', 'Vináttuleikur kvenna')
        ]
    )
    played = models.BooleanField(default=False)
    home_goals = models.IntegerField(default=0)
    away_goals = models.IntegerField(default=0)

    home_formation = models.CharField(max_length=10, choices=FORMATION_CHOICES, default="4-4-2")
    away_formation = models.CharField(max_length=10, choices=FORMATION_CHOICES, default="4-4-2")

    def get_home_formation(self):
        return self.home_formation or self.home_team.default_formation  # Use custom formation or default

    def get_away_formation(self):
        return self.away_formation or self.away_team.default_formation

    # Card Tracking (Make sure these exist if referenced in Admin)
    home_yellow_cards = models.IntegerField(default=0)
    away_yellow_cards = models.IntegerField(default=0)
    home_red_cards = models.IntegerField(default=0)
    away_red_cards = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} on {self.match_date}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # Set formations from team defaults if needed
        if is_new or not self.home_formation:
            self.home_formation = self.home_team.default_formation
        if is_new or not self.away_formation:
            self.away_formation = self.away_team.default_formation

        super().save(*args, **kwargs)

        # Only create lineup slots for new games
        if is_new:
            # Create lineup slots for both teams with position numbers 1-11
            for team in [self.home_team, self.away_team]:
                for position_number in range(1, 12):
                    # Determine position type based on number and formation
                    formation = self.home_formation if team == self.home_team else self.away_formation

                    # Determine position type (GK, DEF, MID, FW)
                    if position_number == 1:
                        position_type = 'GK'  # Goalkeeper is always position 1
                    elif position_number <= 5:  # Adjust these ranges based on your typical formation
                        position_type = 'DEF'
                    elif position_number <= 9:
                        position_type = 'MID'
                    else:
                        position_type = 'FW'

                    # Get default player if available
                    player = None
                    if team.default_lineup_data:
                        player_id = team.default_lineup_data.get(str(position_number))
                        if player_id:
                            try:
                                player = Player.objects.get(id=player_id)
                            except Player.DoesNotExist:
                                pass

                    GameLineup.objects.create(
                        game=self,
                        team=team,
                        position=position_type,  # Position type (GK, DEF, MID, FW)
                        position_number=position_number,  # Numerical position (1-11)
                        player=player  # Use default player or None
                    )

    def get_goal_song(self):
        """Return the home team's goal song if available"""
        if self.home_team and self.home_team.goal_song:
            return self.home_team.goal_song.url
        return None


class Player(models.Model):
    POSITION_CHOICES = [
        ('GK', 'Markmaður'),
        ('DEF', 'Varnarmaður'),
        ('MID', 'Miðjumaður'),
        ('FW', 'Sóknarmaður'),
    ]

    ORDER_CHOICES = [
        ('1', 'GK'),
        ('2', 'RB'),
        ('3', 'LB'),
        ('4', 'LCB'),
        ('5', 'RCB'),
        ('6', 'CB'),
        ('7', 'LWB'),
        ('8', 'RWB'),
        ('9', 'CM'),
        ('10', 'LCM'),
        ('11', 'RCM'),
        ('12', 'LDM'),
        ('13', 'RDM'),
        ('14', 'AM'),
        ('15', 'RAM'),
        ('16', 'LAM'),
        ('17', 'LM'),
        ('18', 'RM'),
        ('19', 'LW'),
        ('20', 'RW'),
        ('21', 'CF'),
        ('22', 'LST'),
        ('23', 'RST'),
        ('24', 'ST'),
    ]

    player_number = models.IntegerField(primary_key=True, default='123') #LeikmadurNumer
    name = models.CharField(max_length=255, default="debug needed")
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    birth_year = models.CharField(max_length=4, default='0123')  # FaedingarAr
    first_team_matches = models.IntegerField(default=0)  # MeistFlokkurLeikir
    first_team_goals = models.IntegerField(default=0)  # MeistFlokkurMork
    national_team_matches = models.IntegerField(default=0)  # ALandsleikirLeikir
    national_team_goals = models.IntegerField(default=0)  # ALandsleikirMork

    # Main position
    position = models.CharField(max_length=3, choices=POSITION_CHOICES)
    # Second position
    secondary_position = models.CharField(max_length=3, choices=POSITION_CHOICES, blank=True, null=True)
    # Third position
    third_position = models.CharField(max_length=3, choices=POSITION_CHOICES, blank=True, null=True)
    shirt_number = models.IntegerField(null=True, blank=True)  # Add shirt number for display

    # def __str__(self):
    #     secondary = f" / {self.get_secondary_position_display()}" if self.secondary_position else ""
    #     third = f" / {self.get_third_position_display()}" if self.third_position else ""
    #     return f"{self.name} ({self.get_position_display()}{secondary}{third})"

    def __str__(self):
        return self.name

    def get_positions(self):
        """Return a list of all positions this player can play"""
        positions = [self.position]
        if self.secondary_position:
            positions.append(self.secondary_position)
        if self.third_position:
            positions.append(self.third_position)
        return positions


class GameLineup(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="lineups")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="lineups")
    position = models.CharField(max_length=3, choices=Player.POSITION_CHOICES)  # GK, DEF, MID, FW
    position_number = models.IntegerField(default=0)  # Store numerical position (1-11)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, null=True, blank=True)
    order = models.CharField(max_length=24, choices=Player.ORDER_CHOICES, blank=True, null=True)

    class Meta:
        ordering = ['position_number']  # Order by position number for consistent retrieval

    def __str__(self):
        player_info = self.player.last_name if self.player else "EMPTY"
        return f"#{self.position_number} - {player_info} - {self.position} - {self.team.name} in {self.game}"


class Tournament(models.Model):
    tournament_number = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, default='debug need')
    start_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name


class Match(models.Model):
    match_number = models.IntegerField(primary_key=True)  # LeikurNumer
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    match_date = models.DateTimeField()  # LeikDagur
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    home_score = models.CharField(max_length=10, null=True, blank=True)  # UrslitHeima
    away_score = models.CharField(max_length=10, null=True, blank=True)  # UrslitUti
    stadium_name = models.CharField(max_length=255)  # VollurNafn
    stadium_number = models.IntegerField()  # VollurNumer
    attendance = models.CharField(max_length=10, null=True, blank=True)  # Ahorfendur

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} - {self.match_date}"


class MatchEvent(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='events', default='debug needed')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, default="debug needed")
    minute = models.IntegerField(default="0")  # AtburdurMinuta
    event_type = models.CharField(max_length=255)  # AtburdurNafn
    event_number = models.IntegerField(default=1)  # AtburdurNumer

    def __str__(self):
        return f"{self.event_type} - {self.player} ({self.minute}')"


class TournamentStanding(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    matches_played = models.IntegerField()  # LeikirAlls
    matches_won = models.IntegerField()  # LeikirUnnir
    matches_drawn = models.IntegerField()  # LeikirJafnt
    matches_lost = models.IntegerField()  # LeikirTap
    goals_scored = models.IntegerField()  # MorkSkorud
    goals_conceded = models.IntegerField()  # MorkFenginASig
    goal_difference = models.IntegerField()  # MorkMisMunur
    points = models.IntegerField()  # Stig

    class Meta:
        unique_together = ('tournament', 'team')

    def __str__(self):
        return f"{self.team} - {self.tournament}"


# Add to models.py
class GamedayJob(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='gameday_jobs')
    job_name = models.CharField(max_length=100)  # e.g., "Bar", "Security", "Ticket sales"
    location = models.CharField(max_length=100)  # e.g., "Bar #1", "Main entrance"
    staff_needed = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job_name} at {self.location}"

    def assigned_staff_count(self):
        return self.staff_assignments.count()

    def vacancies(self):
        return max(0, self.staff_needed - self.assigned_staff_count())


class GamedayStaffAssignment(models.Model):
    job = models.ForeignKey(GamedayJob, on_delete=models.CASCADE, related_name='staff_assignments')
    person_name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=100, blank=True, null=True)  # Optional phone or email
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.person_name} - {self.job}"


class TeamTournamentFilter(models.Model):
    """Model to store which tournaments should be shown for a team in calendars and listings"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tournament_filters')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    is_main_tournament = models.BooleanField(default=False, help_text="Is this a main tournament for this team?")

    class Meta:
        unique_together = ('team', 'tournament')
        verbose_name = "Team Tournament Filter"
        verbose_name_plural = "Team Tournament Filters"

    def __str__(self):
        return f"{self.team.name} - {self.tournament.name}"


class TeamVisibility(models.Model):
    """Control which teams are shown in the team selector for users"""
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name='visibility')
    visible_to_users = models.BooleanField(default=True,
                                           help_text="If checked, this team will be shown in team selection dropdowns")
    display_priority = models.PositiveIntegerField(default=100,
                                                   help_text="Lower numbers appear first in selection lists")

    class Meta:
        verbose_name = "Team Visibility Setting"
        verbose_name_plural = "Team Visibility Settings"
        ordering = ['display_priority', 'team__name']

    def __str__(self):
        visibility = "Visible" if self.visible_to_users else "Hidden"
        return f"{self.team.name} ({visibility})"


# ---------- Add at the bottom of models.py ----------

@receiver(post_save, sender=Team)
def create_team_visibility(sender, instance, created, **kwargs):
    """When a new team is created, automatically create a TeamVisibility record."""
    if created:
        TeamVisibility.objects.create(team=instance)


@receiver(post_save, sender=Team)
def save_team_visibility(sender, instance, **kwargs):
    """Make sure TeamVisibility exists when Team is saved."""
    if not hasattr(instance, 'visibility'):
        TeamVisibility.objects.create(team=instance)
