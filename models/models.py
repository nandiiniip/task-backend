from beanie import Document
from pydantic import EmailStr, Field

class UserRegister(Document):
    email: EmailStr = Field(..., unique=True)
    full_name: str = Field(...)
    title: str = Field(...)
    password: str = Field(..., min_length=8)

    class Settings:
        collection = "users-register"