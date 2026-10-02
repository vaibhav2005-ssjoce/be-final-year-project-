from pydantic import BaseModel
from typing import Literal

class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    role: Literal["user", "admin"]

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    access_token: str
    user: UserResponse
