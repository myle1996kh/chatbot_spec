"""Fernet encryption utilities for API key encryption/decryption."""
from cryptography.fernet import Fernet
from src.config import settings


class EncryptionService:
    """Service for encrypting/decrypting sensitive data using Fernet."""

    def __init__(self):
        """Initialize encryption service with Fernet key from settings."""
        if not settings.FERNET_KEY:
            raise ValueError(
                "FERNET_KEY not set in environment. Generate one with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        self.cipher = Fernet(settings.FERNET_KEY.encode())

    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt API key before storing in database.

        Args:
            api_key: Plain text API key

        Returns:
            Encrypted API key as string
        """
        return self.cipher.encrypt(api_key.encode()).decode()

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt API key at runtime for LLM client.

        Args:
            encrypted_key: Encrypted API key from database

        Returns:
            Decrypted plain text API key
        """
        return self.cipher.decrypt(encrypted_key.encode()).decode()


# Global encryption service instance
encryption_service = EncryptionService() if settings.FERNET_KEY else None


def encrypt_api_key(api_key: str) -> str:
    """Convenience function to encrypt API key."""
    if not encryption_service:
        raise ValueError("Encryption service not initialized - FERNET_KEY missing")
    return encryption_service.encrypt_api_key(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Convenience function to decrypt API key."""
    if not encryption_service:
        raise ValueError("Encryption service not initialized - FERNET_KEY missing")
    return encryption_service.decrypt_api_key(encrypted_key)
