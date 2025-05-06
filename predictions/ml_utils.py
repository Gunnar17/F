import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import pickle
import os
from django.conf import settings
from matches.models import Match, Team


def prepare_game_data():
    """Prepares features from historical game data"""
    # Get all played games
    games = Match.objects.filter(played=True)

    print(f"Found {len(games)} played games for training")
    if len(games) < 5:
        print("WARNING: Very few games available for training. Results may be unreliable.")

    # Create DataFrame
    data = []
    for game in games:
        # Basic game info
        row = {
            'game_id': game.id,
            'home_team_id': game.home_team.id,
            'away_team_id': game.away_team.id,
            'home_goals': game.home_goals,
            'away_goals': game.away_goals,
            'match_date': game.match_date,
        }

        # Add the result (what we're trying to predict)
        if game.home_goals > game.away_goals:
            row['result'] = 'home_win'
        elif game.home_goals < game.away_goals:
            row['result'] = 'away_win'
        else:
            row['result'] = 'draw'

        # Team form (last 5 games)
        home_team_form = calculate_team_form(game.home_team, game.match_date)
        away_team_form = calculate_team_form(game.away_team, game.match_date)

        row.update({
            'home_team_win_rate': home_team_form['win_rate'],
            'home_team_goals_scored_avg': home_team_form['goals_scored_avg'],
            'home_team_goals_conceded_avg': home_team_form['goals_conceded_avg'],
            'away_team_win_rate': away_team_form['win_rate'],
            'away_team_goals_scored_avg': away_team_form['goals_scored_avg'],
            'away_team_goals_conceded_avg': away_team_form['goals_conceded_avg'],
        })

        # Head to head statistics
        h2h_stats = get_head_to_head_stats(game.home_team, game.away_team, game.match_date)
        row.update({
            'h2h_home_win_rate': h2h_stats['home_win_rate'],
            'h2h_away_win_rate': h2h_stats['away_win_rate'],
            'h2h_draw_rate': h2h_stats['draw_rate'],
        })

        data.append(row)

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Print debugging info
    print(f"Created DataFrame with {len(df)} rows")
    print(f"DataFrame columns: {df.columns.tolist()}")

    # Sort by match_date
    if 'match_date' in df.columns and not df.empty:
        df = df.sort_values('match_date')

    # Validate required columns exist
    required_columns = [
        'home_team_win_rate', 'home_team_goals_scored_avg', 'home_team_goals_conceded_avg',
        'away_team_win_rate', 'away_team_goals_scored_avg', 'away_team_goals_conceded_avg',
        'h2h_home_win_rate', 'h2h_away_win_rate', 'h2h_draw_rate', 'result'
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"WARNING: Missing required columns: {missing_columns}")
        print("Creating default values for missing columns")

        for col in missing_columns:
            if col in ['home_team_win_rate', 'away_team_win_rate', 'h2h_home_win_rate',
                       'h2h_away_win_rate', 'h2h_draw_rate']:
                df[col] = 0.33  # Default probability
            elif col in ['home_team_goals_scored_avg', 'home_team_goals_conceded_avg',
                         'away_team_goals_scored_avg', 'away_team_goals_conceded_avg']:
                df[col] = 1.0  # Default goals
            elif col == 'result' and 'result' not in df.columns:
                # This shouldn't happen with the code above, but just in case
                df['result'] = 'home_win'  # Default result

    return df


def calculate_team_form(team, before_date, num_games=5):
    """Calculate team form based on previous games"""
    # Get last N games before this date
    home_games = Match.objects.filter(
        home_team=team,
        match_date__lt=before_date,
        played=True
    ).order_by('-match_date')[:num_games]

    away_games = Match.objects.filter(
        away_team=team,
        match_date__lt=before_date,
        played=True
    ).order_by('-match_date')[:num_games]

    # Combine and sort by date
    recent_games = list(home_games) + list(away_games)
    recent_games.sort(key=lambda x: x.match_date, reverse=True)
    recent_games = recent_games[:num_games]

    # Calculate statistics
    if not recent_games:
        return {
            'win_rate': 0.5,  # Default values if no games
            'goals_scored_avg': 1.0,
            'goals_conceded_avg': 1.0,
        }

    wins = 0
    goals_scored = 0
    goals_conceded = 0

    for game in recent_games:
        # Determine if this team was home or away
        if game.home_team.id == team.id:
            # Team played at home
            goals_scored += game.home_goals
            goals_conceded += game.away_goals
            if game.home_goals > game.away_goals:
                wins += 1
        else:
            # Team played away
            goals_scored += game.away_goals
            goals_conceded += game.home_goals
            if game.away_goals > game.home_goals:
                wins += 1

    return {
        'win_rate': wins / len(recent_games),
        'goals_scored_avg': goals_scored / len(recent_games),
        'goals_conceded_avg': goals_conceded / len(recent_games),
    }


def get_head_to_head_stats(home_team, away_team, before_date, max_games=10):
    """Get head-to-head statistics between teams"""
    # Find all previous matches between these teams
    h2h_games = Match.objects.filter(
        home_team__in=[home_team, away_team],
        away_team__in=[home_team, away_team],
        match_date__lt=before_date,
        played=True
    ).order_by('-match_date')[:max_games]

    if not h2h_games:
        return {
            'home_win_rate': 0.33,
            'away_win_rate': 0.33,
            'draw_rate': 0.33,
        }

    home_wins = 0
    away_wins = 0
    draws = 0

    for game in h2h_games:
        if game.home_goals > game.away_goals:
            if game.home_team.id == home_team.id:
                home_wins += 1
            else:
                away_wins += 1
        elif game.home_goals < game.away_goals:
            if game.home_team.id == home_team.id:
                away_wins += 1
            else:
                home_wins += 1
        else:
            draws += 1

    total = len(h2h_games)
    return {
        'home_win_rate': home_wins / total,
        'away_win_rate': away_wins / total,
        'draw_rate': draws / total,
    }


def train_model(model_type='random_forest'):
    """Train a prediction model on historical data"""
    # Get processed data
    df = prepare_game_data()

    # Define features
    feature_columns = [
        'home_team_win_rate', 'home_team_goals_scored_avg', 'home_team_goals_conceded_avg',
        'away_team_win_rate', 'away_team_goals_scored_avg', 'away_team_goals_conceded_avg',
        'h2h_home_win_rate', 'h2h_away_win_rate', 'h2h_draw_rate'
    ]

    # Check if we have enough data
    min_required_games = 10
    if len(df) < min_required_games:
        print(f"WARNING: Limited data available ({len(df)} games). Using synthetic data augmentation.")

        # Create synthetic data to supplement real data
        synthetic_data = []

        # Home advantage scenario
        synthetic_data.append({
            'home_team_win_rate': 0.6, 'home_team_goals_scored_avg': 2.0,
            'home_team_goals_conceded_avg': 0.8, 'away_team_win_rate': 0.4,
            'away_team_goals_scored_avg': 1.0, 'away_team_goals_conceded_avg': 1.5,
            'h2h_home_win_rate': 0.6, 'h2h_away_win_rate': 0.2, 'h2h_draw_rate': 0.2,
            'result': 'home_win'
        })

        # Away advantage scenario
        synthetic_data.append({
            'home_team_win_rate': 0.3, 'home_team_goals_scored_avg': 1.0,
            'home_team_goals_conceded_avg': 1.8, 'away_team_win_rate': 0.7,
            'away_team_goals_scored_avg': 2.0, 'away_team_goals_conceded_avg': 0.9,
            'h2h_home_win_rate': 0.2, 'h2h_away_win_rate': 0.6, 'h2h_draw_rate': 0.2,
            'result': 'away_win'
        })

        # Draw scenario
        synthetic_data.append({
            'home_team_win_rate': 0.4, 'home_team_goals_scored_avg': 1.3,
            'home_team_goals_conceded_avg': 1.3, 'away_team_win_rate': 0.4,
            'away_team_goals_scored_avg': 1.3, 'away_team_goals_conceded_avg': 1.3,
            'h2h_home_win_rate': 0.3, 'h2h_away_win_rate': 0.3, 'h2h_draw_rate': 0.4,
            'result': 'draw'
        })

        # Add synthetic data to supplement real data
        synthetic_df = pd.DataFrame(synthetic_data)
        df = pd.concat([df, synthetic_df])
        print(f"Added synthetic data. New dataset size: {len(df)}")

    # Ensure all required columns exist
    for column in feature_columns:
        if column not in df.columns:
            raise ValueError(f"Required column '{column}' missing from dataset")

    X = df[feature_columns]
    y = df['result']

    print(f"Feature columns shape: {X.shape}")
    print(f"Target column shape: {y.shape}")

    # Split data with stratification to preserve class distribution
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(y.unique()) > 1 else None
    )

    # Scale features
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train model
    if model_type == 'logistic':
        from sklearn.linear_model import LogisticRegression
        model = LogisticRegression(max_iter=1000, multi_class='multinomial', solver='lbfgs', class_weight='balanced')
    else:  # default to random forest
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')

    model.fit(X_train_scaled, y_train)

    # Evaluate
    from sklearn.metrics import accuracy_score
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"Model accuracy: {accuracy:.4f}")

    # Save the model and scaler
    import os
    import pickle
    from django.conf import settings

    model_filename = f"{model_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pkl"
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

    return {
        'model_type': model_type,
        'accuracy': accuracy,
        'model_path': f'prediction_models/{model_filename}',
        'feature_columns': feature_columns
    }


def predict_match(home_team_id, away_team_id, model_id=None):
    """Predict the outcome of a match"""
    from predictions.models import PredictionModel
    from matches.models import Match, Team
    import pickle
    import pandas as pd
    from django.utils import timezone

    # Get the model to use
    if model_id:
        model_instance = PredictionModel.objects.get(id=model_id)
    else:
        model_instance = PredictionModel.objects.filter(is_active=True).order_by('-accuracy').first()

    if not model_instance:
        raise ValueError("No prediction model available")

    # Load the model
    with open(model_instance.model_file.path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']
    scaler = model_data['scaler']
    feature_columns = model_data['feature_columns']

    # Get team objects
    home_team = Team.objects.get(team_number=home_team_id)
    away_team = Team.objects.get(team_number=away_team_id)

    # Current date/time for feature calculation
    current_date = timezone.now()

    # Reuse the functions from command for consistency
    from predictions.management.commands.train_initial_model import Command
    cmd = Command()

    # Calculate features
    home_stats = cmd.get_team_stats(home_team, current_date)
    away_stats = cmd.get_team_stats(away_team, current_date)
    h2h_stats = cmd.get_h2h_stats(home_team, away_team, current_date)

    # Create feature vector
    features = {
        'home_team_win_rate': home_stats['win_rate'],
        'home_team_goals_scored_avg': home_stats['goals_scored_avg'],
        'home_team_goals_conceded_avg': home_stats['goals_conceded_avg'],
        'away_team_win_rate': away_stats['win_rate'],
        'away_team_goals_scored_avg': away_stats['goals_scored_avg'],
        'away_team_goals_conceded_avg': away_stats['goals_conceded_avg'],
        'h2h_home_win_rate': h2h_stats['home_win_rate'],
        'h2h_away_win_rate': h2h_stats['away_win_rate'],
        'h2h_draw_rate': h2h_stats['draw_rate']
    }

    # Convert to DataFrame with correct columns
    X = pd.DataFrame([features])[feature_columns]

    # Scale features
    X_scaled = scaler.transform(X)

    # Make prediction
    result_proba = model.predict_proba(X_scaled)[0]

    # Get class labels
    classes = model.classes_

    # Map probabilities to results
    probabilities = {}
    for i, cls in enumerate(classes):
        probabilities[cls] = result_proba[i]

    # Default values if not all classes are present
    for result_type in ['home_win', 'draw', 'away_win']:
        if result_type not in probabilities:
            probabilities[result_type] = 0.0

    # Predict goals (simplified model)
    predicted_home_goals = (
            home_stats['goals_scored_avg'] * 0.6 +
            away_stats['goals_conceded_avg'] * 0.4
    )

    predicted_away_goals = (
            away_stats['goals_scored_avg'] * 0.6 +
            home_stats['goals_conceded_avg'] * 0.4
    )

    # Apply home advantage
    predicted_home_goals *= 1.1  # 10% home advantage

    return {
        'home_win_probability': probabilities.get('home_win', 0.0),
        'draw_probability': probabilities.get('draw', 0.0),
        'away_win_probability': probabilities.get('away_win', 0.0),
        'predicted_home_goals': predicted_home_goals,
        'predicted_away_goals': predicted_away_goals
    }
