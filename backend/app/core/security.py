"""Cryptographic security utilities for session and participant management."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import string

# Character set for invitation codes: unambiguous uppercase letters and digits (omitting 0, O, 1, I)
INVITATION_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a high-entropy URL-safe random token."""
    return secrets.token_urlsafe(nbytes)


def generate_invitation_code(length: int = 8) -> str:
    """Generate a cryptographically secure, easily readable alphanumeric invitation code."""
    return "".join(secrets.choice(INVITATION_ALPHABET) for _ in range(length))


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of a plaintext token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(token: str, expected_hash: str) -> bool:
    """Verify a plaintext token against a stored SHA-256 hash in constant time."""
    computed_hash = hash_token(token)
    return hmac.compare_digest(computed_hash, expected_hash)
