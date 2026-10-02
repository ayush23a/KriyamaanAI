import base64
import json
import logging
from typing import Annotated, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import Settings, settings
from app.dependencies import get_db, get_settings
from persistence.models import UserModel
from persistence.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

http_bearer = HTTPBearer(auto_error=False)

_jwk_client_cache: dict[str, PyJWKClient] = {}


def _get_jwk_client(jwks_url: str) -> PyJWKClient:
    if jwks_url not in _jwk_client_cache:
        _jwk_client_cache[jwks_url] = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwk_client_cache[jwks_url]


def derive_jwks_url_from_publishable_key(key: str) -> str | None:
    """Derive Clerk JWKS URL from base64-encoded Frontend API in publishable key."""
    if not key or not key.startswith(("pk_test_", "pk_live_")):
        return None
    try:
        raw = key.split("_", 2)[2]
        padded = raw + "=" * (-len(raw) % 4)
        host = base64.b64decode(padded).decode("utf-8").rstrip("$").strip()
        if host:
            return f"https://{host}/.well-known/jwks.json"
    except Exception:
        return None
    return None


def format_pem_public_key(key_str: str) -> str:
    """Format PEM public key with appropriate headers and normalized newlines."""
    clean = key_str.strip().replace("\\n", "\n")
    if not clean.startswith("-----BEGIN"):
        clean = f"-----BEGIN PUBLIC KEY-----\n{clean}\n-----END PUBLIC KEY-----"
    return clean


def verify_clerk_token(token: str, app_settings: Settings) -> dict[str, Any]:
    """Verify and decode a Clerk session JWT token."""
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Staging/Test Mock Token Bypass for development and automated test suites
    if (
        token.startswith("mock_clerk_")
        or token.startswith("test_token_")
    ) and app_settings.app_env in ["development", "test"]:
        parts = token.split(":")
        sub = parts[1] if len(parts) > 1 else token
        email = parts[2] if len(parts) > 2 else f"{sub}@example.com"
        name = parts[3] if len(parts) > 3 else "Test User"
        return {"sub": sub, "email": email, "name": name}

    # 2. RS256 Verification with PEM Public Key
    if app_settings.clerk_pem_public_key and app_settings.clerk_pem_public_key.strip():
        pem_key = format_pem_public_key(app_settings.clerk_pem_public_key)
        try:
            decode_opts: dict[str, Any] = {"verify_aud": bool(app_settings.clerk_audience)}
            kwargs: dict[str, Any] = {
                "jwt": token,
                "key": pem_key,
                "algorithms": ["RS256"],
                "options": decode_opts,
            }
            if app_settings.clerk_audience:
                kwargs["audience"] = app_settings.clerk_audience
            if app_settings.clerk_issuer:
                kwargs["issuer"] = app_settings.clerk_issuer

            payload = jwt.decode(**kwargs)
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Clerk token verification failed with PEM key: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. RS256 Verification with Clerk JWKS Endpoint
    jwks_url = app_settings.clerk_jwks_url
    if not jwks_url and app_settings.clerk_issuer:
        jwks_url = f"{app_settings.clerk_issuer.rstrip('/')}/.well-known/jwks.json"
    if not jwks_url and app_settings.clerk_publishable_key:
        jwks_url = derive_jwks_url_from_publishable_key(app_settings.clerk_publishable_key)

    if jwks_url:
        try:
            jwks_client = _get_jwk_client(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            decode_opts = {"verify_aud": bool(app_settings.clerk_audience)}
            kwargs = {
                "jwt": token,
                "key": signing_key.key,
                "algorithms": ["RS256"],
                "options": decode_opts,
            }
            if app_settings.clerk_audience:
                kwargs["audience"] = app_settings.clerk_audience
            if app_settings.clerk_issuer:
                kwargs["issuer"] = app_settings.clerk_issuer

            payload = jwt.decode(**kwargs)
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Clerk token verification failed with JWKS: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Error fetching Clerk JWKS signing key: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to verify authentication token with Clerk JWKS.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 4. Fallback verification with CLERK_SECRET_KEY if HMAC is used in dev
    if app_settings.clerk_secret_key and app_settings.clerk_secret_key.strip():
        try:
            payload = jwt.decode(
                token,
                key=app_settings.clerk_secret_key.strip(),
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception:
            pass

    # If no verification method is configured
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Backend authentication is not configured. Please set CLERK_PEM_PUBLIC_KEY, CLERK_JWKS_URL, or CLERK_ISSUER.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> UserModel:
    """FastAPI dependency to authenticate requests using Clerk and resolve the application user."""
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_clerk_token(token, app_settings)

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing identity subject (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(db)
    email = payload.get("email") or payload.get("primary_email_address")
    display_name = payload.get("name") or payload.get("username")

    user = await user_repo.get_or_create_clerk_user(
        auth_subject=sub,
        email=email,
        display_name=display_name,
    )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled.",
        )

    return user
