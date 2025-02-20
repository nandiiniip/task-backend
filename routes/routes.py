from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict
from pydantic import BaseModel, EmailStr
from jose import JWTError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models import UserRegister, UserLogin, PasswordReset
from utils import get_password_hash, verify_password,create_access_token, create_refresh_token, verify_token
from uuid import uuid4
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = "myqfbrzatlnsvptc"

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decode the token and get the current user."""
    try:
        payload = verify_token(token, "access")
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user = await UserRegister.find_one(UserRegister.email == email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

def send_email(to_email: str, reset_link: str):
    sender_email = SENDER_EMAIL
    sender_pwd = SENDER_PASSWORD
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEText(f"Click here to reset your password: {reset_link}")
    msg["Subject"] = "Password Reset Request"
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_pwd)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email sending failed: ", e)
        raise HTTPException(status_code=500, detail="Error sending emial")

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

@router.get("/user/me", response_model=dict)
async def get_user_details(current_user: UserRegister = Depends(get_current_user)):
    """Endpoint to get logged in user's details."""
    return {
        "email": current_user.email,
        "full_name": current_user.full_name,
        "title": current_user.title,
    }

class PasswordResetRequest(BaseModel):
    email: EmailStr

@router.post("/password-reset/request")
async def request_password_reset(request: PasswordResetRequest):
    user = await UserRegister.find_one({"email": request.email})
    if not user: 
        raise HTTPException(status_code = 404, detail = "User not found")
    
    token = str(uuid4())
    expiration = datetime.utcnow() + timedelta(hours=1)

    reset_token = PasswordReset(email=user.email, token=token, expiration=expiration)
    await reset_token.insert()

    reset_link = f"http://localhost:3000/reset-password?token={token}"
    send_email(user.email, reset_link)

    return {"message": "Password Reset link sent"}

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

@router.post("/password-reset/confirm")
async def confirm_password_reset(request: PasswordResetConfirm):
    reset_token = await PasswordReset.find_one({"token": request.token})
    if not reset_token or reset_token.expiration < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid token")
    
    user = await UserRegister.find_one({"email": reset_token.email})
    if not user: 
        raise HTTPException(status_code=404, detail = "User not found")
    
    await user.update_password(request.new_password)
    await reset_token.delete()

    return {"message": "Password has been reset successfully"}
