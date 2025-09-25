from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import logging
import os

# Security scheme
bearer_scheme = HTTPBearer()

logger = logging.getLogger(__name__)

JWT_SECRET_KEY = os.getenv("SECRET_KEY", "HARDTOGUESSKEY")
JWT_ALGORITHM = "HS256"

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = None
) -> dict[str, str]:
    if credentials is None:
        credentials = Security(bearer_scheme)
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token: missing user_id")
        return {"user_id": user_id, "payload": payload}
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Could not validate credentials") from e
