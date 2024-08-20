import requests
import os

def verify_recaptcha(response):
    # Retrieve the reCAPTCHA secret key from the environment variables
    secret_key = os.getenv('RECAPTCHA_SECRET_KEY')

    # Create a payload with the secret key and the user's response
    payload = {
        'secret': secret_key,
        'response': response
    }

    # Send a POST request to the reCAPTCHA API to verify the response
    response = requests.post("https://www.google.com/recaptcha/api/siteverify", data=payload)

    # Parse the JSON response from the API
    result = response.json()

    # Return the success status of the verification, default to False if not found
    return result.get("success", False)