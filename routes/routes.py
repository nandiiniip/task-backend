from fastapi import APIRouter, HTTPException
from models import UserRegister
from utils import get_password_hash

router = APIRouter()

@router.post("/register", response_model=dict)
async def register_user(user: UserRegister, confirm_password: str):
    existing_user = await UserRegister.find_one(UserRegister.email == user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    if user.password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    hashed_password = get_password_hash(user.password)
    new_user = UserRegister(
        email = user.email,
        full_name = user.full_name,
        title = user.title,
        password = hashed_password
    )

    await new_user.insert()
    return {"message": "User registered successfully"}