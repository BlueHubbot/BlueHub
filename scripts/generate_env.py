"""Generate .env file with JWT RSA keys for the BlueHub project."""
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> None:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    private_escaped = private_pem.replace("\n", "\\n")
    public_escaped = public_pem.replace("\n", "\\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f'JWT_PRIVATE_KEY="{private_escaped}"\n')
        f.write(f'JWT_PUBLIC_KEY="{public_escaped}"\n')

    print(f"Created {env_path}")
    print(f"Private key length: {len(private_pem)} chars")
    print(f"Public key length: {len(public_pem)} chars")

if __name__ == "__main__":
    main()
