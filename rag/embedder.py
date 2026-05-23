import chromadb
from sentence_transformers import SentenceTransformer

_client     = None
_collection = None
_embedder   = None

def _init():
    global _client, _collection, _embedder
    if _collection is None:
        _client     = chromadb.PersistentClient(path="./chroma_db")
        _collection = _client.get_collection("debug_docs")
        _embedder   = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve(query: str, n_results: int = 3) -> str:
    _init()
    vec     = _embedder.encode([query]).tolist()
    results = _collection.query(query_embeddings=vec, n_results=n_results)
    docs    = results.get("documents", [[]])[0]
    return "\n---\n".join(docs) if docs else "No relevant docs found."