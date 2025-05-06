from django.db import models
from matches.models import Team, Game
import pickle
import json


class PredictionModel(models.Model):
    MODEL_TYPES = [
        ('logistic', 'Logistic Regression'),
        ('random_forest', 'Random Forest'),
        ('neural_network', 'Neural Network'),
        ('svm', 'Support Vector Machine'),
        ('xgboost', 'XGBoost'),
    ]

    name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=20, choices=MODEL_TYPES)
    model_file = models.FileField(upload_to='prediction_models/')
    feature_columns = models.JSONField(default=list)  # Stores the feature names
    created_at = models.DateTimeField(auto_now_add=True)
    accuracy = models.FloatField(default=0)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.model_type}) - {self.accuracy:.2f} accuracy"


class GamePrediction(models.Model):
    model = models.ForeignKey(PredictionModel, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='predictions')
    home_win_probability = models.FloatField()
    draw_probability = models.FloatField()
    away_win_probability = models.FloatField()
    predicted_home_goals = models.FloatField(null=True, blank=True)
    predicted_away_goals = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prediction for {self.game} - {self.home_win_probability:.2f}/{self.draw_probability:.2f}/{self.away_win_probability:.2f}"

    @property
    def prediction_result(self):
        """Returns the most likely result"""
        probs = [
            ("Home Win", self.home_win_probability),
            ("Draw", self.draw_probability),
            ("Away Win", self.away_win_probability)
        ]
        return max(probs, key=lambda x: x[1])[0]