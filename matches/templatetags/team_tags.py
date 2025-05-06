from django import template
import json
import os
from django.conf import settings

register = template.Library()


@register.simple_tag
def get_visible_teams():
    """
    Load visible teams from JSON file
    """
    json_path = os.path.join(settings.STATIC_ROOT, 'visible_teams.json')

    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except:
        # Return empty list if file doesn't exist or can't be read
        return []