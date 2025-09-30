import httpx
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from .config import get_settings

bearer_scheme = HTTPBearer()


class AuthenticatedUser(BaseModel):
    id: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> AuthenticatedUser:
    settings = get_settings()
    token = credentials.credentials
    auth_headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(
            base_url=settings.AUTH_SERVICE_URL,
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=5.0,
        ) as client:
            response = client.get("/api/users/auth-check/", headers=auth_headers)

        if response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        response.raise_for_status()
        response_data = response.json()
        user_id = response_data.get("user_id")

        if not user_id:
            return AuthenticatedUser(id="unknown-user-placeholder")

        return AuthenticatedUser(id=str(user_id))

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service is unavailable: {e}",
        ) from e
