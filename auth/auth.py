# auth/auth.py

import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

USERS_FILE = Path(__file__).parent / "users.json"


def _load_users() -> dict:
    if not USERS_FILE.exists():
        return {"users": {}}
    with open(USERS_FILE) as f:
        return json.load(f)


def _save_users(data: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _hash_password(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return dk.hex()


def verify_credentials(username: str, password: str) -> dict | None:
    """Returns user dict if credentials are valid, None otherwise."""
    data = _load_users()
    user = data["users"].get(username.strip().lower())
    if not user:
        return None
    if _hash_password(password, user["salt"]) != user["password_hash"]:
        return None
    return user


def get_user(username: str) -> dict | None:
    return _load_users()["users"].get(username)


def update_user_preference(username: str, key: str, value) -> None:
    data = _load_users()
    if username in data["users"]:
        data["users"][username][key] = value
        _save_users(data)


def change_password(username: str, old_password: str, new_password: str) -> bool:
    data = _load_users()
    user = data["users"].get(username)
    if not user:
        return False
    if _hash_password(old_password, user["salt"]) != user["password_hash"]:
        return False
    new_salt = secrets.token_hex(16)
    data["users"][username]["password_hash"] = _hash_password(new_password, new_salt)
    data["users"][username]["salt"] = new_salt
    _save_users(data)
    return True


def create_default_admin() -> None:
    """Seed a default admin account if no users exist yet."""
    data = _load_users()
    if not data["users"]:
        salt = secrets.token_hex(16)
        data["users"]["admin"] = {
            "password_hash": _hash_password("admin123", salt),
            "salt": salt,
            "display_name": "Admin",
            "email": "",
            "role": "admin",
            "theme": "navy",
            "font_size": "medium",
            "created_at": datetime.now().isoformat(),
        }
        _save_users(data)
