from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def read_users():
    """
    Recuperar lista de usuários.
    """
    return []

@router.post("/")
def create_user():
    """
    Criar novo usuário.
    """
    pass
