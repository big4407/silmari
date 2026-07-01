import chromadb

client = chromadb.PersistentClient(
    path="data/chroma_db"
)

def get_collection():
    return client.get_or_create_collection(
        name="person_embeddings"
    )