"""RSA handshake signing for Seestar device authentication.

The handshake flow is:
1. Client sends get_verify_str to get a challenge string
2. Client signs the challenge with SHA-1 + RSA using the app's private key
3. Client sends verify_client with the base64 signature + original data
4. Device verifies with its copy of the public key and responds code=0 on success
"""

from __future__ import annotations

import base64
import logging

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

logger = logging.getLogger(__name__)

# RSA private key extracted from libopenssllib.so in the Android app.
# The device holds the corresponding public key (app_publickey.pem) and
# uses "openssl dgst -sha1 -verify" to check the signature.
_DEFAULT_PRIVATE_KEY_PEM = """\
-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAO0S7LqhYnfQP2vn
s7sZE8s4fV/QJTv1uasQ/0vxgubBdCB9E9N56B+aZSxUf3M8kU7F0Y+pmCNv9T9z
BzC7fu44SJYMgA2IgJOrGe6axLyTrxmYUXpsgC6HK6lfHCULFKOLrHX0WS+IKgm+
14vHnA7+3Ic3LIzK/OryGktpgvXhAgMBAAECgYEAwwzu+B4PhcQwafcYSLc5Mdoo
TMxT1iE1wSka4sCxkmlXweMmjLef42CEHRToR0dtxgG7iRdftMhIXwukvtOEeaUE
qCyjzLfvSYqd1xTE6LCVCwp1vKLZUIc7BeY7Ae7kVkrmKknQtlCGmO8MxZ8tFPgS
YVoUEzGBq1HztIDPTgECQQD95yTxHoBaEei9N/lkw5e3voiTomvlj8OA4n/BY0U1
8s7LHCfxklHW1BLBcLuJZc+ChWnRbqD7PlyIcPud2ckFAkEA7wgybiAaCiPpZqGI
MI3Xk8jIK7nPXCSW7eweq9jkfs6MqmYer2RDeqf2IJ87mZWQSY+p31XJcvgAHT7u
T9IgLQJAX/2oWMRoUCUfMZJc5jyQOnZ9Wht44VRF3I9FL47hVrESf3WIoGrqJ+cL
pDiDnkFwf28C/5vsnrAH+cmFRztUJQJAIgSpoLCi5BSOUBPnHPni11541nhAQZ3X
eQ7kopJgmodsz4dvEIkVbWxgA+6FfesiOMXgaC9+VwVihscBBY0jFQJAGU+fIYC7
ehg/GNbyD+UNL8xKqx9Pe69Q58B3kRnfDBce5KReMO5nNr8o3Pa/yWNu7ZjKWs3N
wzGGrKR8OsYqzw==
-----END PRIVATE KEY-----
"""

# The public key from ConstantsBase.PUB_KEY - used for license verification,
# NOT for the handshake. Kept for reference.
_LICENSE_PUB_KEY_B64 = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDRsuHZIML9s8t9wTOOx1RtpmbD"
    "GKurd1rPsv/OrrhQYQXrpuECRdd2KBHQm5N5Nevy17ryrCMSV1Gp4I+VuiNXqtib"
    "jO2KRq/AtsjrWCE7J11d3tjmbRB/mCcpRRRXA1JBpL9xhDuYG4VvqdNM9B328saL"
    "D1vnd/TYKsES7kXm2wIDAQAB"
)


def load_private_key(pem: str | None = None) -> rsa.RSAPrivateKey:
    """Load the RSA private key for handshake signing.

    Args:
        pem: PEM-encoded private key string. Uses the default app key if None.

    Returns:
        An RSA private key object.
    """
    key = serialization.load_pem_private_key(
        (pem or _DEFAULT_PRIVATE_KEY_PEM).encode("utf-8"),
        password=None,
    )
    if not isinstance(key, rsa.RSAPrivateKey):
        raise TypeError(f"Expected RSA private key, got {type(key)}")
    return key


def sign_challenge(challenge: str, priv_key: rsa.RSAPrivateKey | None = None) -> str:
    """Sign a challenge string using SHA-1 + RSA (PKCS1v15).

    The device verifies with:
        openssl dgst -sha1 -verify app_publickey.pem -signature sign.bin data

    Args:
        challenge: The plain-text challenge from get_verify_str.
        priv_key: RSA private key. Uses the default app key if None.

    Returns:
        Base64-encoded signature for the verify_client "sign" field.
    """
    if priv_key is None:
        priv_key = load_private_key()

    signature = priv_key.sign(
        challenge.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA1(),
    )
    return base64.b64encode(signature).decode("ascii")


# Backwards-compatible aliases
def load_public_key(key_b64: str | None = None) -> rsa.RSAPublicKey:
    """Load an RSA public key from base64-encoded DER format."""
    raw = base64.b64decode(key_b64 or _LICENSE_PUB_KEY_B64)
    key = serialization.load_der_public_key(raw)
    if not isinstance(key, rsa.RSAPublicKey):
        raise TypeError(f"Expected RSA public key, got {type(key)}")
    return key


def encrypt_challenge(challenge: str, pub_key: rsa.RSAPublicKey | None = None) -> str:
    """Encrypt a challenge string using RSA PKCS1v15 padding (for license verification)."""
    if pub_key is None:
        pub_key = load_public_key()
    encrypted = pub_key.encrypt(challenge.encode("utf-8"), padding.PKCS1v15())
    return base64.b64encode(encrypted).decode("ascii")
