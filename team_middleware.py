from django.shortcuts import redirect
from django.urls import resolve


class TeamSelectionMiddleware:
    """
    Middleware to ensure a team is selected before accessing the site.
    Redirects to welcome page if no team is selected in the session.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the current URL name
        resolved = resolve(request.path_info)
        url_name = resolved.url_name

        # Skip this check for certain paths
        exempt_urls = [
            'welcome',
            'login',
            'register',
            'logout',
            'admin',  # Allow admin URLs to pass through
            'static',  # Allow static files to pass through
        ]

        # Skip middleware for exempt URLs and admin paths
        if url_name in exempt_urls or request.path.startswith('/admin/'):
            return self.get_response(request)

        # Check if user has selected a team (either in session or in localStorage via JS)
        if not request.session.get('selected_team_id') and request.user.is_authenticated:
            # Store the current URL in the session for later redirect
            full_path = request.get_full_path()
            request.session['redirect_after_team_selection'] = full_path

            # Redirect to welcome page
            return redirect('welcome')

        # Continue with the request
        response = self.get_response(request)
        return response