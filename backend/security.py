from passlib.context import CryptContext
from jose import jwt, JWTError

SECRET_KEY = "929b15e43fd8f1cf4df79d86eb93ca426ab58ae53386c7a91ac4adb45832773b"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
