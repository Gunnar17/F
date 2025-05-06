from django.core.management.base import BaseCommand
from predictions.models import PredictionModel
from matches.models import Match, Team, Tournament
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import os
import pickle
from django.conf import settings
import time
from django.db.models import Q


class Command(BaseCommand):
    help = 'Trains a prediction model using Match data in chunks'

    def handle(self, *args, **options):
        self.stdout.write('Training prediction model from Match data...')

        # Check if models already exist
        if PredictionModel.objects.exists():
            self.stdout.write(self.style.WARNING('Models already exist. Use --force to create anyway.'))
            if not options.get('force', False):
                return
            else:
                self.stdout.write("Force flag detected, continuing...")

        try:
            # Define the specific teams you want to focus on
            top_team_names = [
                'Afturelding',
                'Augnablik',
                'BF 108',
                'Bolungarvík',
                'FH',
                'FHL',
                'Fjarðabyggð',
                'Fjölnir',
                'Fylkir',
                'Grindavík',
                'Grótta',
                'HK',
                'HK/Víkingur',
                'Hamar',
                'Haukar',
                'Haukar/KÁ',
                'Huginn/Einherji',
                'Huginn/Höttur',
                'Huginn/Höttur/Leiknir',
                'Huginn/Spyrnir',
                'Hvíti riddarinn',
                'Höttur',
                'KA',
                'KR',
                'Keflavík',
                'KÁ',
                'Kórdrengir',
                'Leiknir R.',
                'Mídas',
                'Njarðvík',
                'Selfoss',
                'Smári',
                'Snæfellsnes',
                'Stjarnan',
                'Tindastóll',
                'UMFL',
                'Valur',
                'Vestri',
                'Víkingur R.',
                'Víkingur Ó.',
                'Víðir',
                'Völsungur',
                'Árbær',
                'Ármann',
                'Ægir',
                'ÍA',
                'ÍBV',
                'ÍBA',
                'ÍR',
                ]

            # Get these teams from the database
            top_teams = Team.objects.filter(name__in=top_team_names)
            missing_teams = set(top_team_names) - set(top_teams.values_list('name', flat=True))
            self.stdout.write(f"Missing teams: {missing_teams}")

            team_count = top_teams.count()
            self.stdout.write(f"Found {team_count} teams from your specified list")

            if team_count == 0:
                self.stdout.write(self.style.WARNING("No teams found. Check team names or database."))
                return

            if team_count < len(top_team_names):
                self.stdout.write(
                    self.style.WARNING(f"Only found {team_count} out of {len(top_team_names)} specified teams"))

            # Get matches between these teams only
            matches_with_scores = Match.objects.filter(
                home_team__in=top_teams,
                away_team__in=top_teams,
                home_score__isnull=False,
                away_score__isnull=False
            ).exclude(
                home_score='',
                away_score=''
            )

            total_matches = Match.objects.all().count()
            self.stdout.write(f"Total matches in database: {total_matches}")

            matches_with_scores = Match.objects.filter(
                home_team__in=top_teams,
                away_team__in=top_teams
            )
            self.stdout.write(f"Matches between specified teams: {matches_with_scores.count()}")

            matches_with_scores = matches_with_scores.filter(
                home_score__isnull=False,
                away_score__isnull=False
            )
            self.stdout.write(f"Matches with scores: {matches_with_scores.count()}")

            matches_with_scores = matches_with_scores.exclude(
                home_score='',
                away_score=''
            )
            self.stdout.write(f"Final matches after all filters: {matches_with_scores.count()}")

            # Define chunk size
            chunk_size = 100
            total_chunks = (total_matches + chunk_size - 1) // chunk_size

            self.stdout.write(f"Processing in {total_chunks} chunks of {chunk_size} matches each")

            # Process data in chunks
            all_data = []

            for chunk_num in range(total_chunks):
                start_time = time.time()
                start_idx = chunk_num * chunk_size
                end_idx = min((chunk_num + 1) * chunk_size, total_matches)

                self.stdout.write(f"Processing chunk {chunk_num + 1}/{total_chunks} (matches {start_idx}-{end_idx})")

                # Get chunk of matches
                chunk_matches = matches_with_scores.order_by('match_number')[start_idx:end_idx]

                # Process chunk
                chunk_data = []
                # Inside the match processing loop

                for match in chunk_matches:
                    try:
                        print(
                            f"Processing Match {match.match_number}: {match.home_team} vs {match.away_team} - Score: {match.home_score}-{match.away_score}")

                        if match.home_score is None or match.away_score is None or match.home_score == '' or match.away_score == '':
                            print(f"⚠️ Skipping match {match.match_number} - Missing or empty scores")
                            continue                        # Print match details for debugging
                        print(
                            f"Processing match {match.match_number} - {match.home_team} vs {match.away_team} | Score: {match.home_score}-{match.away_score}")

                        if match.home_score is None or match.away_score is None or match.home_score == '' or match.away_score == '':
                            print(f"Skipping match {match.match_number} - Missing or empty scores")
                            continue

                        # Try to parse scores as integers
                        try:
                            home_goals = int(match.home_score)
                            away_goals = int(match.away_score)
                        except ValueError:
                            print(f"❌ Invalid score format for match {match.match_number}: {match.home_score} - {match.away_score}")
                            # Try to extract first number from score string using regex
                            import re
                            home_match = re.search(r'\d+', str(match.home_score))
                            away_match = re.search(r'\d+', str(match.away_score))

                            if not home_match or not away_match:
                                # Skip if we can't parse the score
                                continue

                            home_goals = int(home_match.group())
                            away_goals = int(away_match.group())

                        # Determine the result
                        if home_goals > away_goals:
                            result = 'home_win'
                        elif home_goals < away_goals:
                            result = 'away_win'
                        else:
                            result = 'draw'  # Parse scores as before

                        # Get the basic information
                        home_team = match.home_team
                        away_team = match.away_team
                        match_date = match.match_date

                        # Enhanced team form with more detailed metrics
                        home_form = self.get_detailed_team_form(home_team, match_date)
                        away_form = self.get_detailed_team_form(away_team, match_date)

                        if not home_form or not away_form:
                            print(f"⚠️ Skipping match {match.match_number} - Team form data is missing")
                            continue

                        # Enhanced head-to-head with recency weighting
                        h2h_stats = self.get_h2h_stats(home_team, away_team, match_date)
                        if not h2h_stats:
                            print(f"⚠️ Skipping match {match.match_number} - H2H stats missing")
                            continue

                        home_advantage = self.calculate_home_advantage(home_team)
                        if home_advantage is None:
                            print(f"⚠️ Skipping match {match.match_number} - Home advantage calculation failed")
                            continue
                        # Get rest and fixture congestion
                        home_rest = self.calculate_rest_days(home_team, match_date)
                        away_rest = self.calculate_rest_days(away_team, match_date)

                        # Team availability (placeholder)
                        home_availability = self.get_team_availability(home_team, match_date)
                        away_availability = self.get_team_availability(away_team, match_date)

                        # Create enhanced feature row
                        row = {
                            'match_id': match.match_number,
                            'home_team_id': home_team.team_number,
                            'away_team_id': away_team.team_number,
                            'home_goals': home_goals,
                            'away_goals': away_goals,
                            'result': result,

                            # Form features
                            'home_win_rate': home_form['win_rate'],
                            'home_goals_scored_avg': home_form['goals_scored_avg'],
                            'home_goals_conceded_avg': home_form['goals_conceded_avg'],
                            'home_form_score': home_form['form_score'],
                            'home_win_streak': home_form['win_streak'],
                            'home_unbeaten_streak': home_form['unbeaten_streak'],
                            'home_clean_sheet_rate': home_form['clean_sheets'],
                            'home_failed_to_score_rate': home_form['failed_to_score'],
                            'home_gd_per_game': home_form['gd_per_game'],

                            'away_win_rate': away_form['win_rate'],
                            'away_goals_scored_avg': away_form['goals_scored_avg'],
                            'away_goals_conceded_avg': away_form['goals_conceded_avg'],
                            'away_form_score': away_form['form_score'],
                            'away_win_streak': away_form['win_streak'],
                            'away_unbeaten_streak': away_form['unbeaten_streak'],
                            'away_clean_sheet_rate': away_form['clean_sheets'],
                            'away_failed_to_score_rate': away_form['failed_to_score'],
                            'away_gd_per_game': away_form['gd_per_game'],

                            # Head-to-head features
                            'h2h_home_win_rate': h2h_stats['home_win_rate'],
                            'h2h_away_win_rate': h2h_stats['away_win_rate'],
                            'h2h_draw_rate': h2h_stats['draw_rate'],
                            'home_h2h_dominance': h2h_stats['home_recent_dominance'],
                            'away_h2h_dominance': h2h_stats['away_recent_dominance'],
                            'h2h_games_played': h2h_stats['h2h_games_played'],
                            'home_h2h_goals_per_game': h2h_stats['home_h2h_goals_per_game'],
                            'home_h2h_conceded_per_game': h2h_stats['home_h2h_conceded_per_game'],

                            # Home advantage
                            'home_advantage_factor': home_advantage,

                            # Rest and fixture congestion
                            'home_days_rest': home_rest['days_since_last_match'],
                            'away_days_rest': away_rest['days_since_last_match'],
                            'home_congestion': home_rest['matches_last_30_days'],
                            'away_congestion': away_rest['matches_last_30_days'],
                            'home_is_congested': int(home_rest['is_congested_period']),
                            'away_is_congested': int(away_rest['is_congested_period']),

                            # Availability (if implemented)
                            'home_availability': home_availability['availability_pct'],
                            'away_availability': away_availability['availability_pct'],
                            'home_key_players_missing': home_availability['key_players_missing'],
                            'away_key_players_missing': away_availability['key_players_missing'],
                        }

                        chunk_data.append(row)
                    except Exception as e:
                        print(f"Error processing match {match.match_number}: {str(e)}")
                        continue
                # Add chunk data to all data
                all_data.extend(chunk_data)

                # Report progress
                end_time = time.time()
                self.stdout.write(
                    f"Processed {len(chunk_data)} valid matches in chunk {chunk_num + 1} ({end_time - start_time:.2f} seconds)")
                self.stdout.write(f"Total valid matches processed so far: {len(all_data)}")

            self.stdout.write(f"Completed processing all {len(all_data)} valid matches")

            if len(all_data) < 10:
                self.stdout.write(self.style.ERROR("Not enough valid match data for training"))
                return

            # Sample data for training if it's too large
            max_training_size = 50000  # Limit training data size for performance
            if len(all_data) > max_training_size:
                self.stdout.write(f"Sampling {max_training_size} matches from {len(all_data)} for training")
                import random
                random.seed(42)  # For reproducibility
                all_data = random.sample(all_data, max_training_size)

            # Convert to DataFrame
            df = pd.DataFrame(all_data)

            # Update the feature columns
            feature_columns = [
                # Form features
                'home_win_rate', 'home_goals_scored_avg', 'home_goals_conceded_avg',
                'home_form_score', 'home_win_streak', 'home_unbeaten_streak',
                'home_clean_sheet_rate', 'home_failed_to_score_rate', 'home_gd_per_game',

                'away_win_rate', 'away_goals_scored_avg', 'away_goals_conceded_avg',
                'away_form_score', 'away_win_streak', 'away_unbeaten_streak',
                'away_clean_sheet_rate', 'away_failed_to_score_rate', 'away_gd_per_game',

                # Head-to-head features
                'h2h_home_win_rate', 'h2h_away_win_rate', 'h2h_draw_rate',
                'home_h2h_dominance', 'away_h2h_dominance', 'h2h_games_played',
                'home_h2h_goals_per_game', 'home_h2h_conceded_per_game',

                # Home advantage
                'home_advantage_factor',

                # Rest and fixture congestion
                'home_days_rest', 'away_days_rest',
                'home_congestion', 'away_congestion',
                'home_is_congested', 'away_is_congested',

                # Availability (if implemented)
                'home_availability', 'away_availability',
                'home_key_players_missing', 'away_key_players_missing',
            ]

            X = df[feature_columns]
            y = df['result']

            # Verify data
            self.stdout.write(f"Feature data shape: {X.shape}")
            self.stdout.write(f"Target data shape: {y.shape}")
            self.stdout.write(f"Classes: {np.unique(y)}")

            # Check class distribution
            class_counts = df['result'].value_counts()
            self.stdout.write("Class distribution:")
            for cls, count in class_counts.items():
                self.stdout.write(f"  {cls}: {count} ({count / len(df) * 100:.1f}%)")

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42,
                stratify=y if len(np.unique(y)) > 1 else None
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            self.stdout.write("Training Random Forest model...")
            start_time = time.time()
            model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1,  # Use all CPU cores
                class_weight='balanced'
            )
            model.fit(X_train_scaled, y_train)
            end_time = time.time()
            self.stdout.write(f"Model training completed in {end_time - start_time:.2f} seconds")

            # Evaluate
            from sklearn.metrics import accuracy_score, classification_report
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)

            self.stdout.write(f"Model accuracy: {accuracy:.4f}")
            self.stdout.write("Classification report:")
            self.stdout.write(classification_report(y_test, y_pred))

            # Save the model
            model_filename = f"match_model_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            model_path = os.path.join(settings.MEDIA_ROOT, 'prediction_models', model_filename)

            # Ensure directory exists
            os.makedirs(os.path.dirname(model_path), exist_ok=True)

            # Save as pickle
            with open(model_path, 'wb') as f:
                pickle.dump({
                    'model': model,
                    'scaler': scaler,
                    'feature_columns': feature_columns
                }, f)

            # Create DB entry
            model_entry = PredictionModel(
                name="Match Prediction Model",
                model_type='random_forest',
                model_file=f'prediction_models/{model_filename}',
                feature_columns=feature_columns,
                accuracy=accuracy,
                is_active=True
            )

            # Deactivate other models if setting this active
            if model_entry.is_active:
                PredictionModel.objects.all().update(is_active=False)

            model_entry.save()

            self.stdout.write(self.style.SUCCESS(f"Successfully trained model with {accuracy:.2%} accuracy"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error training model: {str(e)}"))

    def get_team_stats(self, team, before_date, num_games=5):
        """Calculate team stats from previous matches"""
        home_matches = Match.objects.filter(
            home_team=team,
            match_date__lt=before_date,
            home_score__isnull=False,
            away_score__isnull=False
        ).exclude(
            home_score='',
            away_score=''
        ).order_by('-match_date')[:num_games]

        away_matches = Match.objects.filter(
            away_team=team,
            match_date__lt=before_date,
            home_score__isnull=False,
            away_score__isnull=False
        ).exclude(
            home_score='',
            away_score=''
        ).order_by('-match_date')[:num_games]

        # Combine matches
        matches = list(home_matches) + list(away_matches)
        matches.sort(key=lambda x: x.match_date, reverse=True)
        matches = matches[:num_games]

        if not matches:
            return {
                'win_rate': 0.5,  # Default values
                'goals_scored_avg': 1.5,
                'goals_conceded_avg': 1.0,
            }

        wins = 0
        goals_scored = 0
        goals_conceded = 0

        for match in matches:
            try:
                # Parse scores
                try:
                    home_score = int(match.home_score)
                    away_score = int(match.away_score)
                except ValueError:
                    import re
                    home_match = re.search(r'\d+', str(match.home_score))
                    away_match = re.search(r'\d+', str(match.away_score))

                    if not home_match or not away_match:
                        continue

                    home_score = int(home_match.group())
                    away_score = int(away_match.group())

                if match.home_team.id == team.id:
                    # Team played at home
                    goals_scored += home_score
                    goals_conceded += away_score
                    if home_score > away_score:
                        wins += 1
                else:
                    # Team played away
                    goals_scored += away_score
                    goals_conceded += home_score
                    if away_score > home_score:
                        wins += 1
            except:
                continue

        valid_matches = len(matches)
        return {
            'win_rate': wins / valid_matches if valid_matches > 0 else 0.5,
            'goals_scored_avg': goals_scored / valid_matches if valid_matches > 0 else 1.5,
            'goals_conceded_avg': goals_conceded / valid_matches if valid_matches > 0 else 1.0,
        }

    def get_h2h_stats(self, home_team, away_team, before_date, max_games=10):
        """Get enhanced head-to-head statistics with recency weighting"""
        h2h_matches = Match.objects.filter(
            home_team__in=[home_team, away_team],
            away_team__in=[home_team, away_team],
            match_date__lt=before_date,
            home_score__isnull=False,
            away_score__isnull=False
        ).exclude(
            home_score='',
            away_score=''
        ).order_by('-match_date')[:max_games]

        if not h2h_matches:
            return {
                'home_win_rate': 0.45,
                'away_win_rate': 0.30,
                'draw_rate': 0.25,
                'home_recent_dominance': 0,
                'away_recent_dominance': 0,
                'h2h_games_played': 0
            }

        home_wins = 0
        away_wins = 0
        draws = 0

        # Track goal differences and weighted results
        home_goals_for = 0
        home_goals_against = 0

        # Recency weighting - more recent games count more
        recency_weights = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1][:len(h2h_matches)]
        total_weight = sum(recency_weights)

        home_weighted_wins = 0
        away_weighted_wins = 0

        for i, match in enumerate(h2h_matches):
            weight = recency_weights[i]

            try:
                # Parse scores
                try:
                    home_score = int(match.home_score)
                    away_score = int(match.away_score)
                except ValueError:
                    import re
                    home_match = re.search(r'\d+', str(match.home_score))
                    away_match = re.search(r'\d+', str(match.away_score))

                    if not home_match or not away_match:
                        continue

                    home_score = int(home_match.group())
                    away_score = int(away_match.group())

                current_home_is_prediction_home = match.home_team.id == home_team.id

                # Track goals for the team that's home in our prediction
                if current_home_is_prediction_home:
                    home_goals_for += home_score
                    home_goals_against += away_score
                else:
                    home_goals_for += away_score
                    home_goals_against += home_score

                # Determine winner
                if home_score > away_score:
                    if current_home_is_prediction_home:
                        home_wins += 1
                        home_weighted_wins += weight
                    else:
                        away_wins += 1
                        away_weighted_wins += weight
                elif home_score < away_score:
                    if current_home_is_prediction_home:
                        away_wins += 1
                        away_weighted_wins += weight
                    else:
                        home_wins += 1
                        home_weighted_wins += weight
                else:
                    draws += 1
            except:
                continue

        valid_matches = home_wins + away_wins + draws

        # Calculate dominance scores - how much one team has been winning recently
        home_recent_dominance = home_weighted_wins / total_weight if total_weight > 0 else 0
        away_recent_dominance = away_weighted_wins / total_weight if total_weight > 0 else 0

        return {
            'home_win_rate': home_wins / valid_matches if valid_matches > 0 else 0.45,
            'away_win_rate': away_wins / valid_matches if valid_matches > 0 else 0.30,
            'draw_rate': draws / valid_matches if valid_matches > 0 else 0.25,
            'home_recent_dominance': home_recent_dominance,
            'away_recent_dominance': away_recent_dominance,
            'home_h2h_goals_per_game': home_goals_for / valid_matches if valid_matches > 0 else 1.0,
            'home_h2h_conceded_per_game': home_goals_against / valid_matches if valid_matches > 0 else 1.0,
            'h2h_games_played': valid_matches
        }

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force training even if models already exist',
        )

    def calculate_home_advantage(self, home_team, competition=None):
        """Calculate how strong home advantage is for this team/competition"""
        # Get all home matches for this team
        home_matches = Match.objects.filter(
            home_team=home_team,
            home_score__isnull=False,
            away_score__isnull=False
        ).exclude(
            home_score='',
            away_score=''
        )

        # Filter by competition if provided
        if competition:
            home_matches = home_matches.filter(tournament=competition)

        # Calculate home form
        matches_count = home_matches.count()
        if matches_count == 0:
            return 1.3  # Default home advantage factor

        try:
            # Count wins, draws, losses
            home_wins = 0
            home_draws = 0
            home_losses = 0

            for match in home_matches:
                try:
                    home_score = int(match.home_score)
                    away_score = int(match.away_score)
                except ValueError:
                    import re
                    home_match = re.search(r'\d+', str(match.home_score))
                    away_match = re.search(r'\d+', str(match.away_score))

                    if not home_match or not away_match:
                        continue

                    home_score = int(home_match.group())
                    away_score = int(away_match.group())

                if home_score > away_score:
                    home_wins += 1
                elif home_score == away_score:
                    home_draws += 1
                else:
                    home_losses += 1

            total_valid = home_wins + home_draws + home_losses
            if total_valid == 0:
                return 1.3

            # Calculate points per game at home
            points = (home_wins * 3) + home_draws
            ppg_home = points / total_valid

            # Adjust home advantage (higher if team performs better at home)
            # Range typically from 1.1 to 1.5
            home_advantage = 1.0 + (ppg_home / 10)

            # Keep in reasonable range
            return max(1.1, min(1.5, home_advantage))

        except Exception as e:
            # Fallback to default
            return 1.3

    def get_detailed_team_form(self, team, before_date, num_games=10):
        """Get detailed recent form metrics"""
        home_matches = Match.objects.filter(
            home_team=team,
            match_date__lt=before_date,
            home_score__isnull=False,
            away_score__isnull=False
        ).exclude(
            home_score='',
            away_score=''
        ).order_by('-match_date')[:num_games]

        away_matches = Match.objects.filter(
            away_team=team,
            match_date__lt=before_date,
            home_score__isnull=False,
            away_score__isnull=False
        ).exclude(
            home_score='',
            away_score=''
        ).order_by('-match_date')[:num_games]

        # Combine matches
        matches = list(home_matches) + list(away_matches)
        matches.sort(key=lambda x: x.match_date, reverse=True)
        matches = matches[:num_games]

        if not matches:
            return {
                'win_rate': 0.5,
                'goals_scored_avg': 1.5,
                'goals_conceded_avg': 1.0,
                'form_score': 0.5,  # Normalized form score (0-1)
                'win_streak': 0,
                'unbeaten_streak': 0,
                'clean_sheets': 0,
                'failed_to_score': 0,
                'scoring_streak': 0,
                'gd_per_game': 0.5
            }

        # Track basic stats
        wins = 0
        draws = 0
        losses = 0
        goals_scored = 0
        goals_conceded = 0

        # Track streaks and form
        current_win_streak = 0
        current_unbeaten_streak = 0
        current_scoring_streak = 0
        max_win_streak = 0
        max_unbeaten_streak = 0
        max_scoring_streak = 0
        clean_sheets = 0
        failed_to_score = 0

        # Calculate form score (3 pts for win, 1 for draw, weighted by recency)
        form_scores = []

        # Track goal differences
        goal_differences = []

        for match in matches:
            try:
                # Parse scores
                try:
                    home_score = int(match.home_score)
                    away_score = int(match.away_score)
                except ValueError:
                    import re
                    home_match = re.search(r'\d+', str(match.home_score))
                    away_match = re.search(r'\d+', str(match.away_score))

                    if not home_match or not away_match:
                        continue

                    home_score = int(home_match.group())
                    away_score = int(away_match.group())

                is_home = match.home_team.id == team.id

                team_score = home_score if is_home else away_score
                opponent_score = away_score if is_home else home_score

                # Update basic counters
                goals_scored += team_score
                goals_conceded += opponent_score

                # Calculate goal difference
                goal_diff = team_score - opponent_score
                goal_differences.append(goal_diff)

                # Determine result
                if team_score > opponent_score:
                    wins += 1
                    current_win_streak += 1
                    current_unbeaten_streak += 1
                    form_scores.append(3)
                elif team_score == opponent_score:
                    draws += 1
                    current_win_streak = 0
                    current_unbeaten_streak += 1
                    form_scores.append(1)
                else:
                    losses += 1
                    current_win_streak = 0
                    current_unbeaten_streak = 0
                    form_scores.append(0)

                # Update max streaks
                max_win_streak = max(max_win_streak, current_win_streak)
                max_unbeaten_streak = max(max_unbeaten_streak, current_unbeaten_streak)

                # Clean sheet and scoring
                if opponent_score == 0:
                    clean_sheets += 1

                if team_score == 0:
                    failed_to_score += 1
                    current_scoring_streak = 0
                else:
                    current_scoring_streak += 1
                    max_scoring_streak = max(max_scoring_streak, current_scoring_streak)

            except Exception as e:
                continue

        valid_matches = len(form_scores)
        if valid_matches == 0:
            return {
                'win_rate': 0.5,
                'goals_scored_avg': 1.5,
                'goals_conceded_avg': 1.0,
                'form_score': 0.5,
                'win_streak': 0,
                'unbeaten_streak': 0,
                'clean_sheets': 0,
                'failed_to_score': 0,
                'scoring_streak': 0,
                'gd_per_game': 0.5
            }

        # Weight recent matches more heavily for form score
        form_weights = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1][:valid_matches]
        weighted_form = sum(s * w for s, w in zip(form_scores, form_weights)) / sum(form_weights)

        # Normalize to 0-1 scale (max possible is 3.0)
        normalized_form = weighted_form / 3.0

        return {
            'win_rate': wins / valid_matches,
            'goals_scored_avg': goals_scored / valid_matches,
            'goals_conceded_avg': goals_conceded / valid_matches,
            'form_score': normalized_form,
            'win_streak': current_win_streak,
            'unbeaten_streak': current_unbeaten_streak,
            'clean_sheets': clean_sheets / valid_matches,  # As a rate
            'failed_to_score': failed_to_score / valid_matches,  # As a rate
            'scoring_streak': current_scoring_streak,
            'gd_per_game': sum(goal_differences) / valid_matches
        }

    def get_team_availability(self, team, match_date):
        """
        Calculate team strength based on player availability
        This is a placeholder assuming you'll add injury/suspension tracking
        """
        try:
            # Placeholder for injury/suspension data
            # This would need to be implemented based on your data structure
            key_players_available = 11  # Default - all players available

            # If you implement an Injury/Suspension model:
            # suspended_players = Suspension.objects.filter(
            #     team=team,
            #     start_date__lte=match_date,
            #     end_date__gte=match_date
            # ).count()

            # injured_players = Injury.objects.filter(
            #     player__team=team,
            #     start_date__lte=match_date,
            #     expected_return_date__gte=match_date
            # ).count()

            # key_players_available = 11 - (suspended_players + injured_players)

            # Calculate availability percentage
            availability_pct = key_players_available / 11.0

            # Add squad strength factor
            return {
                'availability_pct': availability_pct,
                'key_players_missing': 11 - key_players_available
            }
        except Exception:
            # Default if calculation fails
            return {
                'availability_pct': 1.0,
                'key_players_missing': 0
            }

    def calculate_rest_days(self, team, match_date):
        """Calculate days since last match and fixture congestion"""
        try:
            # Find the most recent match before this one
            previous_match = Match.objects.filter(
                Q(home_team=team) | Q(away_team=team),
                match_date__lt=match_date
            ).order_by('-match_date').first()

            if not previous_match:
                return {
                    'days_since_last_match': 7,  # Default rest
                    'matches_last_30_days': 0,
                    'is_congested_period': False
                }

            # Calculate days since last match
            days_rest = (match_date.date() - previous_match.match_date.date()).days

            # Calculate fixture congestion (matches in last 30 days)
            thirty_days_ago = match_date - time.timezone.timedelta(days=30)
            recent_matches = Match.objects.filter(
                Q(home_team=team) | Q(away_team=team),
                match_date__lt=match_date,
                match_date__gte=thirty_days_ago
            ).count()

            # Determine if this is a congested period (more than 1 match per week on average)
            is_congested = recent_matches > 4  # More than 4 matches in 30 days

            return {
                'days_since_last_match': days_rest,
                'matches_last_30_days': recent_matches,
                'is_congested_period': is_congested
            }
        except Exception:
            # Default values
            return {
                'days_since_last_match': 7,
                'matches_last_30_days': 0,
                'is_congested_period': False
            }

    def get_top_tier_teams_and_competitions(self):
        """Identify top-tier teams and competitions"""
        # Identify top leagues/tournaments
        # These could be identified by name patterns or IDs
        top_tier_tournament_ids = [
            49315,  # Men's top league ID (from your URLs)
            49321,  # Women's top league ID (from your URLs)
            # Add other top competitions
        ]

        # Or filter by name if IDs aren't consistent
        top_tier_tournaments = Tournament.objects.filter(
            Q(name__icontains='besta deild') |  # Main Icelandic league
            Q(name__icontains='premier') |
            Q(id__in=top_tier_tournament_ids)
        )

        # Get teams from these top competitions
        top_teams = Team.objects.filter(
            Q(home_matches__tournament__in=top_tier_tournaments) |
            Q(away_matches__tournament__in=top_tier_tournaments)
        ).distinct()

        return top_teams, top_tier_tournaments