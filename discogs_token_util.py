import json
import os

def get_template_path():
    settings_path = os.path.expanduser("~/.ripzbuddy_settings.json")
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        if 'template_path' in settings and os.path.exists(settings['template_path']):
            return settings['template_path']
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "CDs.json")
    if os.path.exists(desktop_path):
        return desktop_path
    raise RuntimeError("No template file found. Please place your template (e.g. CDs.json) on your Desktop or set the template_path in settings.")

def load_discogs_token_from_template():
    template_path = get_template_path()
    with open(template_path, 'r', encoding='utf-8') as f:
        template = json.load(f)
    token = template.get('discogs_token')
    if not token:
        raise RuntimeError("No Discogs token found in template.")
    return token
