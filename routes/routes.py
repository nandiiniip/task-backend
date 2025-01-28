from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models import UserRegister, UserLogin
from utils import get_password_hash, verify_password,create_access_token, create_refresh_token, verify_token

router = APIRouter()

@router.post("/register", response_model=dict)
async def register_user(user: UserRegister):
    existing_user = await UserRegister.find_one(UserRegister.email == user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # if user.password != confirm_password:
    #     raise HTTPException(status_code=400, detail="Passwords do not match")
    
    hashed_password = get_password_hash(user.password)
    new_user = UserRegister(
        email = user.email,
        full_name = user.full_name,
        title = user.title,
        password = hashed_password
    )

    await new_user.insert()
    return {"message": "User registered successfully"}


refresh_token_store: Dict[str, str] = {}

@router.post("/login", response_model=dict)
async def login(user: UserLogin):
    """Authenticate the user and return tokens."""
    # Find the user in the database
    db_user = await UserRegister.find_one(UserRegister.email == user.email)
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # Generate access and refresh tokens
    access_token = create_access_token(data={"sub": db_user.email})
    refresh_token = create_refresh_token(data={"sub": db_user.email})

    # Store the refresh token for rotation
    refresh_token_store[db_user.email] = refresh_token

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=dict)
async def refresh(refresh_token: str):
    """Rotate the refresh token and issue new tokens."""
    payload = verify_token(refresh_token, "refresh")
    email = payload.get("sub")

    # Check if the token matches the stored one
    if not email or refresh_token_store.get(email) != refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    
    # Generate new tokens
    new_access_token = create_access_token(data={"sub": email})
    new_refresh_token = create_refresh_token(data={"sub": email})

    # Rotate the refresh token
    refresh_token_store[email] = new_refresh_token

    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@router.post("/logout", response_model=dict)
async def logout(token: str):
    """Invalidate the refresh token on logout."""
    payload = verify_token(token, "access")
    email = payload.get("sub")

    # Remove the refresh token from the store
    if email in refresh_token_store:
        del refresh_token_store[email]

    return {"message": "Successfully logged out"}