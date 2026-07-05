from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    token_limit: int
    tokens_used: int

    model_config = {"from_attributes": True}
