from pydantic import BaseModel

# Schemas Pydantic para validação de entrada/saída (Requests e Responses da API)

class UserBase(BaseModel):
    pass

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    pass
