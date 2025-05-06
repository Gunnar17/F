from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator

from matches.models import Team, Game
from .models import PredictionModel, GamePrediction
from .ml_utils import train_model, predict_match
from .forms import PredictionForm, ModelTrainingForm


def predictions_home(request):
    """Home page for predictions"""
    # Get active model
    active_model = PredictionModel.objects.filter(is_active=True).first()

    # Recent predictions
    recent_predictions = GamePrediction.objects.all().order_by('-created_at')[:10]

    # Upcoming games
    upcoming_games = Game.objects.filter(played=False).order_by('match_date')[:10]

    return render(request, 'predictions/home.html', {
        'active_model': active_model,
        'recent_predictions': recent_predictions,
        'upcoming_games': upcoming_games,
    })


@login_required
def new_prediction(request):
    """Create a new prediction"""
    if request.method == 'POST':
        form = PredictionForm(request.POST)
        if form.is_valid():
            home_team_id = form.cleaned_data['home_team'].id
            away_team_id = form.cleaned_data['away_team'].id
            model_id = form.cleaned_data.get('model')

            # If there's already a game scheduled
            game_id = form.cleaned_data.get('game')
            if game_id:
                game = Game.objects.get(id=game_id)
            else:
                # Create a placeholder game object
                game = Game(
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    match_date=form.cleaned_data.get('match_date'),
                    played=False
                )
                game.save()

            # Make prediction
            prediction_data = predict_match(home_team_id, away_team_id, model_id)

            # Save prediction
            model = PredictionModel.objects.get(id=model_id) if model_id else \
                PredictionModel.objects.filter(is_active=True).first()

            prediction = GamePrediction(
                model=model,
                game=game,
                home_win_probability=prediction_data['home_win_probability'],
                draw_probability=prediction_data['draw_probability'],
                away_win_probability=prediction_data['away_win_probability'],
                predicted_home_goals=prediction_data['predicted_home_goals'],
                predicted_away_goals=prediction_data['predicted_away_goals']
            )
            prediction.save()

            messages.success(request, 'Prediction created successfully!')
            return redirect('prediction_detail', prediction_id=prediction.id)
    else:
        # For GET requests, pre-populate game if provided
        game_id = request.GET.get('game')
        initial = {}

        if game_id:
            try:
                game = Game.objects.get(id=game_id)
                initial = {
                    'game': game.id,
                    'home_team': game.home_team.id,
                    'away_team': game.away_team.id,
                    'match_date': game.match_date
                }
            except Game.DoesNotExist:
                pass

        form = PredictionForm(initial=initial)

    return render(request, 'predictions/new_prediction.html', {
        'form': form
    })


def prediction_detail(request, prediction_id):
    """View a prediction's details"""
    prediction = get_object_or_404(GamePrediction, id=prediction_id)

    # Get actual result if game has been played
    actual_result = None
    if prediction.game.played:
        if prediction.game.home_goals > prediction.game.away_goals:
            actual_result = "Home Win"
        elif prediction.game.home_goals < prediction.game.away_goals:
            actual_result = "Away Win"
        else:
            actual_result = "Draw"

    return render(request, 'predictions/prediction_detail.html', {
        'prediction': prediction,
        'actual_result': actual_result
    })


@user_passes_test(lambda u: u.is_staff)
def train_prediction_model(request):
    """Train a new prediction model"""
    if request.method == 'POST':
        form = ModelTrainingForm(request.POST)
        if form.is_valid():
            model_type = form.cleaned_data['model_type']
            name = form.cleaned_data['name']

            # Train the model
            try:
                result = train_model(model_type)

                # Create model instance
                model = PredictionModel(
                    name=name,
                    model_type=model_type,
                    model_file=result['model_path'],
                    feature_columns=result['feature_columns'],
                    accuracy=result['accuracy'],
                    is_active=form.cleaned_data['set_as_active']
                )
                model.save()

                # If set as active, deactivate other models
                if form.cleaned_data['set_as_active']:
                    PredictionModel.objects.exclude(id=model.id).update(is_active=False)

                messages.success(request,
                                 f"Model '{name}' trained successfully with {result['accuracy']:.2%} accuracy!")
                return redirect('model_detail', model_id=model.id)

            except Exception as e:
                messages.error(request, f"Error training model: {str(e)}")
    else:
        form = ModelTrainingForm()

    return render(request, 'predictions/train_model.html', {
        'form': form
    })


@user_passes_test(lambda u: u.is_staff)
def model_detail(request, model_id):
    """View a model's details"""
    model = get_object_or_404(PredictionModel, id=model_id)

    # Get predictions made with this model
    predictions = GamePrediction.objects.filter(model=model).order_by('-created_at')

    # Accuracy on played games
    played_predictions = predictions.filter(game__played=True)
    correct_predictions = 0

    for pred in played_predictions:
        game = pred.game
        actual_result = None
        if game.home_goals > game.away_goals:
            actual_result = "Home Win"
        elif game.home_goals < game.away_goals:
            actual_result = "Away Win"
        else:
            actual_result = "Draw"

        if actual_result == pred.prediction_result:
            correct_predictions += 1

    # Calculate accuracy
    if played_predictions:
        real_world_accuracy = correct_predictions / len(played_predictions)
    else:
        real_world_accuracy = None

    return render(request, 'predictions/model_detail.html', {
        'model': model,
        'predictions': predictions[:50],  # Limit to recent 50
        'total_predictions': predictions.count(),
        'played_predictions': played_predictions.count(),
        'correct_predictions': correct_predictions,
        'real_world_accuracy': real_world_accuracy
    })


@user_passes_test(lambda u: u.is_staff)
def set_active_model(request, model_id):
    """Set a model as the active one"""
    model = get_object_or_404(PredictionModel, id=model_id)

    # Deactivate all models
    PredictionModel.objects.all().update(is_active=False)

    # Activate this model
    model.is_active = True
    model.save()

    messages.success(request, f"Model '{model.name}' is now active")
    return redirect('model_detail', model_id=model.id)


@user_passes_test(lambda u: u.is_staff)
def delete_model(request, model_id):
    """Delete a prediction model"""
    model = get_object_or_404(PredictionModel, id=model_id)

    if request.method == 'POST':
        # If this was the active model, we need to select a new one
        was_active = model.is_active

        # Delete the model file
        if model.model_file:
            try:
                model.model_file.delete()
            except:
                pass

        # Delete the model
        model.delete()

        # If this was active, make the most accurate remaining model active
        if was_active:
            best_model = PredictionModel.objects.order_by('-accuracy').first()
            if best_model:
                best_model.is_active = True
                best_model.save()

        messages.success(request, "Model deleted successfully")
        return redirect('predictions_home')

    return render(request, 'predictions/delete_model.html', {
        'model': model
    })