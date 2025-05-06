from django import forms
from matches.models import Team, Game
from .models import PredictionModel


class PredictionForm(forms.Form):
    game = forms.IntegerField(required=False, widget=forms.HiddenInput())
    home_team = forms.ModelChoiceField(
        queryset=Team.objects.all(),
        label="Home Team"
    )
    away_team = forms.ModelChoiceField(
        queryset=Team.objects.all(),
        label="Away Team"
    )
    match_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Match Date"
    )
    model = forms.ModelChoiceField(
        queryset=PredictionModel.objects.filter(is_active=True),
        required=False,
        label="Prediction Model (optional)",
        help_text="Leave blank to use the default active model"
    )

    def clean(self):
        cleaned_data = super().clean()
        home_team = cleaned_data.get('home_team')
        away_team = cleaned_data.get('away_team')

        if home_team and away_team and home_team == away_team:
            raise forms.ValidationError("Home and away teams must be different")

        return cleaned_data


class ModelTrainingForm(forms.Form):
    MODEL_TYPES = [
        ('logistic', 'Logistic Regression'),
        ('random_forest', 'Random Forest'),
    ]

    name = forms.CharField(
        max_length=100,
        label="Model Name",
        help_text="A descriptive name for this prediction model"
    )
    model_type = forms.ChoiceField(
        choices=MODEL_TYPES,
        label="Algorithm Type"
    )
    set_as_active = forms.BooleanField(
        initial=True,
        required=False,
        label="Set as active model",
        help_text="Make this the default model for predictions"
    )