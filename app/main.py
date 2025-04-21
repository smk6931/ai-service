# import os
# import sys
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from api import users

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["users"])