import requests
from bs4 import BeautifulSoup
from datetime import datetime
from .models import Game

MEN_URL = "https://www.ksi.is/mot/stakt-mot/?motnumer=49315"
WOMEN_URL = "https://www.ksi.is/mot/stakt-mot/?motnumer=49321"


def fetch_games(url, category):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Example scraping logic (update selectors as needed)
    matches = []
    for row in soup.select(".match-row"):  # Adjust class based on actual structure
        home_team = row.select_one(".home-team").text.strip()
        away_team = row.select_one(".away-team").text.strip()
        date_str = row.select_one(".match-date").text.strip()
        match_date = datetime.strptime(date_str, "%d.%m.%Y %H:%M")

        game, created = Game.objects.get_or_create(
            home_team=home_team, away_team=away_team, match_date=match_date, category=category
        )
        matches.append(game)

    return matches


def update_games():
    fetch_games(MEN_URL, "men")
    fetch_games(WOMEN_URL, "women")
