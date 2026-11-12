"""Bearer API-key check (Lesson 6.6).

- no Authorization header      -> 401
- wrong key                     -> 401
- right key                     -> request goes through
Keys are compared in constant time and are never logged.
"""
import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import config

# scheme_name matches the security scheme name in the Module 2 spec
bearer = HTTPBearer(auto_error=False, scheme_name="bearerAuth")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


def require_api_key(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthorized("Not authenticated")
    given = creds.credentials.encode()
    # fail closed: if no keys are configured nobody gets in
    if not any(hmac.compare_digest(given, key.encode()) for key in config.API_KEYS):
        raise _unauthorized("Invalid API key")
