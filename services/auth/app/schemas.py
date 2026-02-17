from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenResponse(BaseModel):
    """Ответ при успешной OAuth2 аутентификации"""

    id: int
    email: EmailStr
    full_name: str | None = None
    picture_url: str | None = None
    auth_provider: str | None = None
    access_token: str
    token_type: str

    class Config:
        from_attributes = True


class User(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    picture_url: str | None = None
    auth_provider: str | None = None

    class Config:
        from_attributes = True
