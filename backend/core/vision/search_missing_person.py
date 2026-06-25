import numpy as np
import json

def load_embedding_data(embedding_dir:str):
    """
        임베딩된 목록을 가져온다
    """
    np.load("image_embeddings.npy")
    json.load("metadata.json")

def create_text_embedding():
    """
        검색에 사용한 텍스트를 임베딩된 사람 크롭 이미지와 비교하여 찾기 위하여 임베딩한다.
    """

def serach_similar_images():
    """
        텍스트 임베딩과 이미지 임베딩을 비교하여 점수를 매겨 순위가 높은 이미지를 가져온다.
    """