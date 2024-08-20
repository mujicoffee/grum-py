from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import os

# Retrieve the key from an environment variable
key_hex = os.getenv('AES_KEY')
if not key_hex:
    raise ValueError("AES_KEY not set in environment variables")

# Convert the key from hexadecimal format to bytes
key = bytes.fromhex(key_hex)

KEY = get_random_bytes(32)

def encrypt_token(token):
    nonce = os.urandom(12)  # Generate a secure random nonce (12 bytes for AES-GCM)
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    ct_bytes = encryptor.update(token.encode()) + encryptor.finalize()
    # Encode nonce, ciphertext, and tag in base64 for easy storage/transmission
    iv = base64.b64encode(nonce).decode('utf-8')
    ct = base64.b64encode(ct_bytes).decode('utf-8')
    # Authentication tag
    tag = base64.b64encode(encryptor.tag).decode('utf-8')
    return iv, ct, tag

def decrypt_token(iv, ct, tag):
    # Decode base64 encoded values
    iv = base64.b64decode(iv)
    ct = base64.b64decode(ct)
    tag = base64.b64decode(tag)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    # Verify integrity and decrypt
    pt = decryptor.update(ct) + decryptor.finalize()
    return pt.decode('utf-8')

def encrypt_message(message):
    cipher = AES.new(KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(message.encode(), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    ct = base64.b64encode(ct_bytes).decode('utf-8')
    return iv, ct

def decrypt_message(iv, ct):
    iv = base64.b64decode(iv)
    ct = base64.b64decode(ct)
    cipher = AES.new(KEY, AES.MODE_CBC, iv=iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size).decode('utf-8')
    return pt