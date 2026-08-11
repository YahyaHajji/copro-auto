from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> int:
    private = Ed25519PrivateKey.generate()
    private_raw = private.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption(),
    )
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    print("LICENSE_SIGNING_PRIVATE_KEY=" + base64.b64encode(private_raw).decode("ascii"))
    print("COPRO_AUTO_LICENSE_PUBLIC_KEY=" + base64.b64encode(public_raw).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
