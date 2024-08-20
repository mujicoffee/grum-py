import secrets

# Generate a secure random pepper value
pepper = secrets.token_bytes(32)
print(pepper.hex())
