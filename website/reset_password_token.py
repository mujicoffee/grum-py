import secrets

def generate_reset_password_token():
    # Generate a random URL-safe token of 32 bytes
    token = secrets.token_urlsafe(32)
    return token