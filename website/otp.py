import secrets
import string

def generate_otp(length=6):
    alphabet = string.ascii_letters + string.digits
    otp = ''.join(secrets.choice(alphabet) for i in range(length))
    return otp