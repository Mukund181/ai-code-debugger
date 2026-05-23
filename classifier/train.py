import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sentence_transformers import SentenceTransformer
from model import ErrorClassifier, ERROR_CLASSES
import os

# --- Synthetic training data (expand this for better accuracy) ---
TRAINING_DATA = [
    ("SyntaxError: invalid syntax", "syntax_error"),
    ("unexpected EOF while parsing", "syntax_error"),
    ("IndentationError: expected an indented block", "syntax_error"),
    ("NameError: name 'x' is not defined", "runtime_error"),
    ("ZeroDivisionError: division by zero", "runtime_error"),
    ("FileNotFoundError: No such file", "runtime_error"),
    ("TypeError: unsupported operand type(s)", "type_error"),
    ("TypeError: argument of type 'int' is not iterable", "type_error"),
    ("TypeError: 'NoneType' object is not subscriptable", "type_error"),
    ("IndexError: list index out of range", "index_error"),
    ("IndexError: string index out of range", "index_error"),
    ("KeyError: 'missing_key'", "index_error"),
    ("output is always the same regardless of input", "logic_error"),
    ("infinite loop detected", "logic_error"),
    ("wrong result returned from function", "logic_error"),
]

def train():
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    texts  = [d[0] for d in TRAINING_DATA]
    labels = [ERROR_CLASSES.index(d[1]) for d in TRAINING_DATA]

    X = torch.tensor(embedder.encode(texts), dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.long)

    dataset = TensorDataset(X, y)
    loader  = DataLoader(dataset, batch_size=8, shuffle=True)

    model     = ErrorClassifier()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(60):
        for xb, yb in loader:
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
        if (epoch + 1) % 20 == 0:
            print(f"Epoch {epoch+1}  loss={loss.item():.4f}")

    os.makedirs("../models", exist_ok=True)
    torch.save(model.state_dict(), "../models/error_classifier.pth")
    print("Model saved.")

if __name__ == "__main__":
    train()