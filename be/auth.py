from fastapi import Depends, HTTPException, APIRouter, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from db.connection import get_conn
from dependency import create_access_token, get_current_user
from pydantic import BaseModel
from psycopg import AsyncConnection

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hash: str) -> bool:
    return pwd_context.verify(password, hash)

@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends(),
                conn: AsyncConnection = Depends(get_conn)):
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, role, password_hash, is_active FROM users WHERE username=%s
                """,(form.username,),
            )

            user = await cur.fetchone()
        
        if user is None or not verify_password(form.password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
        
        if not user["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

        token = create_access_token({"sub": form.username, "id": user["id"], "role": user["role"]})
        return {"access_token": token, "token_type": "bearer"}


async def require_student(cur_user: dict = Depends(get_current_user)) -> dict:
    if cur_user["role"] != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students only")
    return cur_user

async def require_teacher(cur_user: dict = Depends(get_current_user)) -> dict:
    if cur_user["role"] != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teachers only")
    return cur_user