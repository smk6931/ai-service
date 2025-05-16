import os
from dotenv import load_dotenv
from pydantic import BaseModel
from pymongo import MongoClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

class Settings(BaseModel):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    
    DATABASE_HOST: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PORT: int
    DATABASE_PASSWORD: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    @property
    def POSTGRESQL_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    @property
    def MONGO_CONFIG(self) -> MongoClient:
        mongo_url = f"mongodb://{self.DATABASE_HOST}:27017"
        client = MongoClient(mongo_url)
        db = client[self.DATABASE_NAME]
        return db

settings = Settings(
    OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
    , OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    , DATABASE_HOST=os.getenv("DATABASE_HOST")
    , DATABASE_NAME=os.getenv("DATABASE_NAME")
    , DATABASE_USER=os.getenv("DATABASE_USER")
    , DATABASE_PORT=int(os.getenv("DATABASE_PORT"))
    , DATABASE_PASSWORD=os.getenv("DATABASE_PASSWORD")
    , SECRET_KEY=os.getenv("SECRET_KEY")
    , ALGORITHM=os.getenv("ALGORITHM", "HS256")
    , ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)),
)