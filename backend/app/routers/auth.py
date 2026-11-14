from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.auth import create_access_token, hash_password, verify_password
from app.database import db
from app.schemas import AuthResponse, UserCredentials, UserResponse

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(credentials: UserCredentials):
    email = str(credentials.email).lower()
    user = {"_id": str(uuid4()), "email": email, "password_hash": hash_password(credentials.password)}
    try:
        db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    return AuthResponse(
        access_token=create_access_token(user["_id"]),
        user=UserResponse(id=user["_id"], email=email),
    )


@router.post("/login", response_model=AuthResponse)
def login(credentials: UserCredentials):
    email = str(credentials.email).lower()
    user = db.users.find_one({"email": email})
    if user is None or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return AuthResponse(
        access_token=create_access_token(user["_id"]),
        user=UserResponse(id=user["_id"], email=email),
    )
