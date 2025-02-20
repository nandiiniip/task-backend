from beanie import Document
from pydantic import EmailStr, Field
from utils import get_password_hash
from datetime import datetime

class UserRegister(Document):
    email: EmailStr = Field(..., unique=True)
    full_name: str = Field(...)
    title: str = Field(...)
    password: str = Field(..., min_length=8)

    class Settings:
        collection = "users-register"

    async def update_password(self, new_password: str):
        self.password = get_password_hash(new_password)
        await self.save()

class UserLogin(Document):
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=8)

    class Settings:
        collection = "users-login"

class PasswordReset(Document): 
    email: EmailStr = Field(...)
    token: str = Field(...)
    expiration: datetime

    class Settings:
        collection = "password-reset-tokens"