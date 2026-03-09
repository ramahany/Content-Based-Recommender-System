from enum import Enum
import os 

class PathEnums(Enum):
    MOVIES_DF_PATH = os.path.join('assets','movies_df.csv')
    BOW_INDEX_PATH = os.path.join('assets','bow_index.faiss')
    BOW_DENSE_PATH = os.path.join('assets','bow_dense.pkl')
    EMB_SIMILARITY_PATH = os.path.join('assets','similarity_emb.pkl')
