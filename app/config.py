import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

class Settings(BaseModel):
    DATABASE_HOST: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PORT: int
    DATABASE_PASSWORD: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    class Config:
        case_sensitive = True

settings = Settings(
    DATABASE_HOST=os.getenv("DATABASE_HOST")
    , DATABASE_NAME=os.getenv("DATABASE_NAME")
    , DATABASE_USER=os.getenv("DATABASE_USER")
    , DATABASE_PORT=int(os.getenv("DATABASE_PORT"))
    , DATABASE_PASSWORD=os.getenv("DATABASE_PASSWORD")
    , SECRET_KEY=os.getenv("SECRET_KEY")
    , ALGORITHM=os.getenv("ALGORITHM", "HS256")
    , ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)),
)