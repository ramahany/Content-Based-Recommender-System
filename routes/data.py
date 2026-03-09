from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
import time
api_router = APIRouter(
    prefix='/api/v1',
    tags=["api_v1", "recommendations"]
)

@api_router.post('/recommend/{movie_name}')
async def recommend(request:Request, movie_name:str):
    start = time.time()
    movies = await request.app.recommender.recommend(movie_name)
    end = time.time()
    print("latency = ", end-start)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                    "recommendations_embd" :  movies["embdding"],
                    "recommendations_bow" : movies["bagofwords"]
                })

@api_router.get('/listmovies')
def list_movies(request:Request):
    return JSONResponse(status_code=status.HTTP_200_OK,
                    content={
                    "movies" : request.app.recommender.get_movies_titles()
                })
    

