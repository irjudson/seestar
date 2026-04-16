"""Tests for RSA crypto handshake."""

import base64

from seestar.crypto import load_private_key, sign_challenge


def test_load_default_private_key():
    key = load_private_key()
    assert key is not None
    assert key.key_size == 1024


def test_sign_challenge():
    result = sign_challenge("test_challenge_string")
    # Should be valid base64
    decoded = base64.b64decode(result)
    # RSA 1024-bit produces 128-byte signature
    assert len(decoded) == 128


def test_sign_different_challenges_produce_different_output():
    r1 = sign_challenge("challenge_1")
    r2 = sign_challenge("challenge_2")
    assert r1 != r2


def test_sign_same_challenge_produces_same_output():
    # Unlike encryption, deterministic SHA-1 + PKCS1v15 signing is deterministic
    r1 = sign_challenge("same_challenge")
    r2 = sign_challenge("same_challenge")
    assert r1 == r2


def test_sign_with_explicit_key():
    key = load_private_key()
    result = sign_challenge("test", priv_key=key)
    assert len(base64.b64decode(result)) == 128
