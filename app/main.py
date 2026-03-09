from fastapi import FastAPI, routing
from routes import base, data
from models import Recommender
from contextlib import asynccontextmanager



@asynccontextmanager
async def lifespan(app:FastAPI):
    app.recommender = Recommender()
    yield


app = FastAPI(lifespan=lifespan)

#routers
app.include_router(base.api_router)
app.include_router(data.api_router)
