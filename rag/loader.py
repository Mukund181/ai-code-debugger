import os
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR    = "data/docs"
COLLECTION  = "debug_docs"

def load_docs_to_chromadb():
    client     = chromadb.PersistentClient(path="./chroma_db")
    embedder   = SentenceTransformer("all-MiniLM-L6-v2")

    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION)

    docs, ids, metas = [], [], []
    for i, fname in enumerate(os.listdir(DOCS_DIR)):
        fpath = os.path.join(DOCS_DIR, fname)
        if not fname.endswith((".txt", ".md")):
            continue
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        # Chunk into ~300-char pieces
        chunks = [content[j:j+300] for j in range(0, len(content), 300)]
        for k, chunk in enumerate(chunks):
            docs.append(chunk)
            ids.append(f"{fname}_{k}")
            metas.append({"source": fname})

    embeddings = embedder.encode(docs).tolist()
    collection.add(documents=docs, embeddings=embeddings, ids=ids, metadatas=metas)
    print(f"Indexed {len(docs)} chunks from {DOCS_DIR}")

if __name__ == "__main__":
    load_docs_to_chromadb()