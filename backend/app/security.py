import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import defaultdict
from fastapi import HTTPException
from .config import settings


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 120000).hex()
    return f'pbkdf2_sha256${salt}${digest}'


def verify_password(password, encoded):
    try:
        algorithm, salt, digest = encoded.split('$')
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 120000).hex()
        return algorithm == 'pbkdf2_sha256' and hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


def create_token(user):
    raw = json.dumps({'sub': user.id, 'tv': user.token_version, 'exp': int(time.time()) + settings.token_seconds}).encode()
    payload = base64.urlsafe_b64encode(raw).decode().rstrip('=')
    signature = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest()
    return payload + '.' + base64.urlsafe_b64encode(signature).decode().rstrip('=')


def decode_token(token):
    try:
        payload, signature = token.split('.')
        expected = base64.urlsafe_b64encode(hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest()).decode().rstrip('=')
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        if not isinstance(data, dict) or not isinstance(data.get('sub'), int) or not isinstance(data.get('tv'), int) or not isinstance(data.get('exp'), (int, float)):
            return None
        return data if data['exp'] > time.time() else None
    except (ValueError, TypeError, KeyError, UnicodeError):
        return None


class Limiter:
    def __init__(self):
        self.entries = defaultdict(list)
        self.lock = threading.Lock()

    def consume(self, key, limit, seconds):
        with self.lock:
            now = time.monotonic()
            hits = [t for t in self.entries[key] if t > now - seconds]
            self.entries[key] = hits
            if len(hits) >= limit:
                raise HTTPException(429, '请求过于频繁，请稍后再试')
            hits.append(now)

    def clear(self, key):
        with self.lock:
            self.entries.pop(key, None)


limiter = Limiter()

