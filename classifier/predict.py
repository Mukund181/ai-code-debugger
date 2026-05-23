import torch
from sentence_transformers import SentenceTransformer
from classifier.model import ErrorClassifier, ERROR_CLASSES

_embedder = None
_model    = None

def _load():
    global _embedder, _model
    if _model is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        _model    = ErrorClassifier()
        _model.load_state_dict(torch.load("models/error_classifier.pth", map_location="cpu"))
        _model.eval()

def classify_error(error_text: str) -> str:
    _load()
    vec    = torch.tensor(_embedder.encode([error_text]), dtype=torch.float32)
    with torch.no_grad():
        logits = _model(vec)
    idx    = logits.argmax(dim=1).item()
    return ERROR_CLASSES[idx]