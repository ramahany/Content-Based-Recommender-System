import pandas as pd 
import pickle
from .enums.PathEnums import PathEnums
import logging
from helpers.config import get_settings
import requests_async
import asyncio  
import heapq
import faiss
import os
class Recommender:
    def __init__(self):
        self.settings = get_settings()
        self.movies_df = pd.read_csv(PathEnums.MOVIES_DF_PATH.value)
        self.bow_index = faiss.read_index(PathEnums.BOW_INDEX_PATH.value)
        self.bow_dense = pickle.load(open(PathEnums.BOW_DENSE_PATH.value, 'rb'))
        self.emb_similarity = pickle.load(open(PathEnums.EMB_SIMILARITY_PATH.value, 'rb'))
        self.logger = logging.getLogger(__name__)

    async def recommend(self, movie_name:str): 
        recommendations = {}
        recommendations["embdding"] =  await self.recommend_emb(movie_name=movie_name)
        recommendations["bagofwords"] = await self.recommend_bow(movie_name=movie_name)

        return recommendations

    async def recommend_emb(self, movie_name:str): 
        movie_index = self.movies_df[self.movies_df["title"]==movie_name].index[0]
        movie_similarity_vec = self.emb_similarity[movie_index]

        #nlog k instead of n log n with sorted()
        similar_movies = heapq.nlargest(7, enumerate(movie_similarity_vec), key=lambda x: x[1])

        #storing tasks then gathering, list compreh will force the seq execution and wontbenifit from the async implementation 
        poster_tasks = [self.get_poster_url(int(self.movies_df["movie_id"].iloc[id])) for id, _ in similar_movies[1:]]
        posters = await asyncio.gather(*poster_tasks)

        respose = [{"movie_id": int(self.movies_df["movie_id"].iloc[id]),
                    "movie_name":self.movies_df["title"].iloc[id],
                    "poster":posters[i], 
                    "score": float(score)}
                for i, (id, score) in enumerate(similar_movies[1:])]

        return respose

    async def recommend_bow(self, movie_name:str, k = 7): 
        movie_index = self.movies_df[self.movies_df["title"]==movie_name].index[0]
        query_vec = self.bow_dense[movie_index].reshape(1, -1) 
        
        distances, indices = self.bow_index.search(query_vec.astype('float32'), k) 
        poster_tasks = [self.get_poster_url(int(self.movies_df["movie_id"].iloc[id])) for id in indices[0][1:]]
        posters = await asyncio.gather(*poster_tasks)

        respose = [{"movie_id": int(self.movies_df["movie_id"].iloc[id]),
                    "movie_name":self.movies_df["title"].iloc[id],
                    "poster":posters[i], 
                    "score": float(distances[0][i])}
                for i, id in enumerate(indices[0][1:])]
        return respose
    
    async def get_poster_url(self, movie_id: int):
        url = 'https://api.themoviedb.org/3/movie/{}'.format(movie_id)
        headers = {
            "Authorization": 'Bearer {}'.format(self.settings.TMDB_ACCESS_TOKEN)
        }
        responce = await requests_async.get(url=url, headers=headers)
        image_path = None
        if responce.status_code == 200:
            image_path = 'https://image.tmdb.org/t/p/w500/{}'.format(responce.json()["poster_path"])
        return image_path
    
    def get_movies_titles(self):
        return list(self.movies_df["title"])

