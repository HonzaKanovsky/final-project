from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class VideoEncryption:
    def __init__(self, password):
        # Generate a key from the password
        salt = b'fixed_salt'  # In production, use a random salt and store it securely
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.cipher_suite = Fernet(key)

    def encrypt_frame(self, frame_data):
        """Encrypt a video frame"""
        return self.cipher_suite.encrypt(frame_data)

    def decrypt_frame(self, encrypted_data):
        """Decrypt a video frame"""
        return self.cipher_suite.decrypt(encrypted_data) 