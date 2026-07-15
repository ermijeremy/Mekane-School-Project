from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from config import SECRET_KEY, ALGORITHM, EXPIRE_MINUTE

oauth2_token = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(Data: dict) -> str:
    payload = Data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTE)
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_token)) -> dict:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Couldn't validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        role: str = payload.get("role")

        if username is None or user_id is None:
            raise credentials_error

    except JWTError:
        raise credentials_error

    return {"id": user_id, "username": username, "token": token, "role": role}
