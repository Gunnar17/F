# Update the URLs in urls.py

from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include
from GameDay import settings
from . import views

urlpatterns = [
                  # Update the home route to point to the welcome page
                  path("", views.welcome, name='welcome'),
                  path("home/", views.home, name='home'),

                  # Keep all your existing URLs
                  path('admin/start_lineup/<int:game_id>/', views.start_lineup, name="start_lineup"),
                  path('admin/edit_formation/<int:game_id>/', views.edit_formation, name="edit_formation"),
                  path('admin/teams/<int:team_id>/default-lineup/', views.manage_default_lineup,
                       name='manage_default_lineup'),

                  # GAMEDAY
                  path('gameday-text/', views.gameday_text, name='gameday_text'),
                  path("gameday/<int:game_id>/", views.get_gameday_info, name="gameday_info"),
                  path("gameday/<int:game_id>/announcement/<str:announcement_type>/", views.trigger_announcement,
                       name="trigger_announcement"),
                  path("gameday/<int:game_id>/log_event/", views.log_match_event, name="log_match_event"),

                  # MATCH
                  path('matches/<int:match_id>/', views.match_detail, name='match_detail'),
                  # CALENDAR
                  path('calendar/', views.game_calendar, name='game_calendar'),

                  # GAME
                  path('game/<int:game_id>/', views.game_details, name='game_details'),
                  path('games/<int:game_id>/update-formations/', views.update_formations, name='update_formations'),
                path('game/<int:game_id>/gameday-staff/', views.gameday_staff, name='gameday_staff'),
                path('game/<int:game_id>/add-job/', views.add_gameday_job, name='add_gameday_job'),
                path('game/<int:game_id>/edit-job/<int:job_id>/', views.edit_gameday_job, name='edit_gameday_job'),
                path('game/<int:game_id>/delete-job/<int:job_id>/', views.delete_gameday_job, name='delete_gameday_job'),
                path('game/<int:game_id>/assign-staff/<int:job_id>/', views.assign_gameday_staff, name='assign_gameday_staff'),
                path('game/<int:game_id>/remove-staff/<int:assignment_id>/', views.remove_gameday_staff, name='remove_gameday_staff'),

                  # LEAGUE TABLE
                  path("league/<str:category>/", views.league_table, name="league_table"),

                  # TEAM
                  path('teams/<str:category>/', views.teams_overview, name='teams'),
                  path('team/<int:team_id>/', views.team_details, name='team_details'),

                  # API
                  path('api/games/<int:game_id>/update-formation/', views.update_formations, name='update_formation'),

                  # SECURITY
                  path("login/", views.user_login, name='login'),                  path("logout/", auth_views.LogoutView.as_view(), name="logout"),
                  path("change-password/", auth_views.PasswordChangeView.as_view(), name="change_password"),
                  path("change-username/", views.change_username, name="change_username"),
                  path("change_team/", views.change_team, name="change_team"),
                  path('register/', views.register, name='register'),
                  path("accounts/", include('django.contrib.auth.urls')),
                  path("welcome/", views.welcome, name='welcome'),

                  # FANTASY
                  path("fantasy/", views.fantasy_home, name="fantasy_home"),


                # XML
                path('tournaments/', views.tournament_list, name='tournament_list'),
                path('tournaments/<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),
                path('matches/<int:match_id>/', views.match_detail, name='match_detail'),
                    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
                    path('players/<int:player_id>/', views.player_detail, name='player_detail'),
path('team-calendar/', views.team_calendar, name='team_calendar'),
path('api/todays-matches/', views.todays_matches, name='todays_matches'),
path('api/search-teams/', views.search_teams, name='search_teams'),
path('game/<int:game_id>/staff/', views.gameday_staff, name='gameday_staff'),
path('game/<int:game_id>/job/add/', views.add_gameday_job, name='add_gameday_job'),
path('game/<int:game_id>/job/<int:job_id>/edit/', views.edit_gameday_job, name='edit_gameday_job'),
path('game/<int:game_id>/job/<int:job_id>/delete/', views.delete_gameday_job, name='delete_gameday_job'),
path('game/<int:game_id>/job/<int:job_id>/assign-staff/', views.assign_gameday_staff, name='assign_gameday_staff'),
path('game/<int:game_id>/remove-staff/<int:assignment_id>/', views.remove_gameday_staff, name='remove_gameday_staff'),
path('game/<int:game_id>/staff-search/', views.gameday_staff_search, name='gameday_staff_search'),
path('game/<int:game_id>/job/<int:job_id>/staff/', views.get_job_staff, name='get_job_staff'),
path('game/<int:game_id>/edit-staff/<int:assignment_id>/', views.edit_gameday_staff, name='edit_gameday_staff'),
path('admin/match/<int:match_number>/lineup/', views.start_lineup_match, name='start_lineup_match'),
path('assign_player/', views.assign_player, name='assign_player'),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
