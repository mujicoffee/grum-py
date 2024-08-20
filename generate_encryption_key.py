import os

key = os.urandom(32)
print(f"Generated key: {key.hex()}")