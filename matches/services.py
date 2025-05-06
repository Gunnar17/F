# services.py
from zeep import Client
from zeep.transports import Transport
from requests import Session
from django.conf import settings


class KSIService:
    """
    A service class to interact with the KSI SOAP services.
    """

    def __init__(self):
        self.base_url = "http://www2.ksi.is/vefthjonustur/mot.asmx"
        # Create a session with appropriate timeout settings
        session = Session()
        session.verify = True
        transport = Transport(session=session, timeout=30)
        self.client = Client(f"{self.base_url}?WSDL", transport=transport)

    def get_tournament_matches(self, tournament_number):
        """Get all matches for a specific tournament."""
        try:
            response = self.client.service.MotLeikir(MotNumer=str(tournament_number))
            # Just return the response directly and handle the structure in the sync function
            return response
        except Exception as e:
            print(f"Error fetching tournament matches: {e}")
            return None

    def get_tournament_standings(self, tournament_number):
        """Get standings for a specific tournament."""
        try:
            response = self.client.service.MotStada(MotNumer=str(tournament_number))
            return response.MotStadaSvar
        except Exception as e:
            print(f"Error fetching tournament standings: {e}")
            return None

    def get_team_matches(self, team_number, start_date, end_date, venue_number=None, category=None, gender=None):
        """Get all matches for a specific team within a date range."""
        try:
            response = self.client.service.FelogLeikir(
                FelagNumer=str(team_number),
                VollurNumer=str(venue_number) if venue_number else "",
                FlokkurNumer=str(category) if category else "",
                Kyn=str(gender) if gender else "",
                DagsFra=start_date,
                DagsTil=end_date
            )
            return response.FelogLeikirSvar
        except Exception as e:
            print(f"Error fetching team matches: {e}")
            return None

    def get_match_details(self, match_number):
        """Get detailed information about a specific match."""
        try:
            response = self.client.service.Leikir(LeikirNumer=str(match_number))
            return response.MotLeikirSvar
        except Exception as e:
            print(f"Error fetching match details: {e}")
            return None

    def get_match_events(self, match_number):
        """Get all events for a specific match."""
        try:
            response = self.client.service.LeikurAtburdir(LeikurNumer=str(match_number))
            return response
        except Exception as e:
            print(f"Error fetching match events: {e}")
            return None

    def get_player_info(self, player_number):
        """Get detailed information about a specific player."""
        try:
            response = self.client.service.Leikmadur(LeikmadurNumer=str(player_number))
            return response.LeikmadurSvar
        except Exception as e:
            print(f"Error fetching player info: {e}")
            return None

    # Add more methods for other endpoints as needed