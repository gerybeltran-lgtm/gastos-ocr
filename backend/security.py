"""Authentication and RBAC helpers for the FastAPI service."""

import os
import threading
import time
from dataclasses import dataclass

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


ADMIN_EMAILS = frozenset({
    "gerardo.beltran@e-voltage.cl",
    "jose.diaz@e-voltage.cl",
    "jorge.salas@e-voltage.cl",
})
APPROVER_EMAILS = frozenset({
    "gerardo.beltran@e-voltage.cl",
    "jose.diaz@e-voltage.cl",
})

_bearer = HTTPBearer(auto_error=False)
_cache: dict[str, tuple[float, "AuthenticatedUser"]] = {}
_cache_lock = threading.Lock()
_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_DEFAULT_GOOGLE_CLIENT_ID = "478414532725-9plr5a15q3s6ti4qhref9m0as3baq6k3.apps.googleusercontent.com"


@dataclass(frozen=True)
class AuthenticatedUser:
    email: str
    name: str

    @property
    def is_admin(self) -> bool:
        return self.email in ADMIN_EMAILS

    @property
    def is_approver(self) -> bool:
        return self.email in APPROVER_EMAILS


def _verify_google_access_token(token: str) -> AuthenticatedUser:
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(token)
        if cached and cached[0] > now:
            return cached[1]

    try:
        response = requests.get(
            _TOKENINFO_URL,
            params={"access_token": token},
            timeout=(3.05, 5),
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="No fue posible validar la sesión") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o expirada")

    claims = response.json()
    expected_client_id = os.environ.get("GOOGLE_CLIENT_ID", _DEFAULT_GOOGLE_CLIENT_ID).strip()
    audience = claims.get("aud") or claims.get("audience") or claims.get("issued_to")
    if audience != expected_client_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token emitido para otra aplicación")

    email = str(claims.get("email", "")).strip().lower()
    verified = claims.get("email_verified", claims.get("verified_email"))
    if verified not in (True, "true") or not email.endswith("@e-voltage.cl"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere una cuenta corporativa verificada")

    name = email.split("@", 1)[0]
    try:
        profile_response = requests.get(
            _USERINFO_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=(3.05, 5),
        )
        if profile_response.status_code == 200:
            profile = profile_response.json()
            if str(profile.get("email", "")).lower() == email:
                name = str(profile.get("name") or name)
    except requests.RequestException:
        pass

    user = AuthenticatedUser(email=email, name=name)
    ttl = min(max(int(claims.get("expires_in", 60)), 1), 300)
    with _cache_lock:
        _cache[token] = (now + ttl, user)
        if len(_cache) > 1000:
            expired = [key for key, (deadline, _) in _cache.items() if deadline <= now]
            for key in expired:
                _cache.pop(key, None)
    return user


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _verify_google_access_token(credentials.credentials)


def require_admin(user: AuthenticatedUser = Depends(current_user)) -> AuthenticatedUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso reservado a administradores")
    return user


def require_approver(user: AuthenticatedUser = Depends(current_user)) -> AuthenticatedUser:
    if not user.is_approver:
        raise HTTPException(status_code=403, detail="Acceso reservado a Gerencia/Finanzas")
    return user
