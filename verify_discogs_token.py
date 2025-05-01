import requests

def verify_discogs_token(token):
    """
    Verifies a Discogs personal access token by fetching the user's profile.
    Returns the username if valid, None otherwise.
    """
    try:
        headers = {
            'Authorization': f'Discogs token={token}',
            'User-Agent': 'NFO-GUI/1.0 +https://github.com/yourrepo'
        }
        resp = requests.get('https://api.discogs.com/oauth/identity', headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('username')
        return None
    except Exception:
        return None
