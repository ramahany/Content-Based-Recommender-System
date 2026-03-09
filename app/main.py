from fastapi import FastAPI, routing
from routes import base, data
from models import Recommender
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app:FastAPI):
    app.recommender = Recommender()
    yield


app = FastAPI(lifespan=lifespan)


#routers
app.include_router(base.api_router)
app.include_router(data.api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
