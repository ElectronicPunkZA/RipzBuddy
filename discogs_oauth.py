import discogs_client
import webbrowser

CONSUMER_KEY = 'dZcgvrZrDnbnbSKhbhtQ'
CONSUMER_SECRET = 'dxeWMPEkeIoDVjaUWtheKRkIqNvBSmsT'
USER_AGENT = 'NFO-GUI/1.0 +https://github.com/yourrepo'

def oauth_login():
    """
    Initiates Discogs OAuth 1.0a login flow.
    Returns (access_token, access_token_secret, username) on success, or (None, None, None) on failure.
    """
    d = discogs_client.Client(USER_AGENT, consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET)
    request_token, request_token_secret, authorize_url = d.get_authorize_url()
    webbrowser.open(authorize_url)
    print(f"Opened browser for Discogs authorization: {authorize_url}")
    print("After authorizing, you will receive a PIN (verifier code). Paste it below.")
    verifier = input("Enter Discogs PIN: ").strip()
    try:
        d.get_access_token(verifier)
        user = d.identity()
        return d.token, d.token_secret, getattr(user, 'username', None)
    except Exception as e:
        print(f"OAuth failed: {e}")
        return None, None, None
