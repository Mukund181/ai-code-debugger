import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sentence_transformers import SentenceTransformer
try:
    from classifier.model import ErrorClassifier, ERROR_CLASSES
except ImportError:
    from model import ErrorClassifier, ERROR_CLASSES
import os

# --- Comprehensive expanded training data ---
TRAINING_DATA = [
    # Syntax Errors
    ("SyntaxError: invalid syntax", "syntax_error"),
    ("unexpected EOF while parsing", "syntax_error"),
    ("IndentationError: expected an indented block", "syntax_error"),
    ("SyntaxError: positional argument follows keyword argument", "syntax_error"),
    ("SyntaxError: unmatched ')'", "syntax_error"),
    ("SyntaxError: invalid syntax (empty block or missing colons)", "syntax_error"),
    ("TabError: inconsistent use of tabs and spaces in indentation", "syntax_error"),
    ("IndentationError: unexpected indent", "syntax_error"),
    ("SyntaxError: f-string: unmatched '('", "syntax_error"),
    ("SyntaxError: cannot assign to literal", "syntax_error"),
    ("SyntaxError: Generator expression must be parenthesized", "syntax_error"),
    ("IndentationError: unindent does not match any outer indentation level", "syntax_error"),
    ("SyntaxError: invalid character in identifier", "syntax_error"),

    # Runtime Errors
    ("NameError: name 'x' is not defined", "runtime_error"),
    ("ZeroDivisionError: division by zero", "runtime_error"),
    ("FileNotFoundError: No such file or directory: 'data.csv'", "runtime_error"),
    ("ImportError: cannot import name 'nonexistent_func'", "runtime_error"),
    ("ModuleNotFoundError: No module named 'pandas'", "runtime_error"),
    ("RecursionError: maximum recursion depth exceeded", "runtime_error"),
    ("PermissionError: [Errno 13] Permission denied", "runtime_error"),
    ("RuntimeError: working directory not set", "runtime_error"),
    ("RuntimeError: thread died unexpectedly", "runtime_error"),
    ("OSError: failed to write to disk", "runtime_error"),
    ("StopIteration: end of iterator reached", "runtime_error"),
    ("ModuleNotFoundError: No module named 'numpy'", "runtime_error"),
    ("ImportError: cannot import name 'LSTM' from 'torch.nn'", "runtime_error"),

    # Type Errors
    ("TypeError: unsupported operand type(s) for +: 'int' and 'str'", "type_error"),
    ("TypeError: argument of type 'int' is not iterable", "type_error"),
    ("TypeError: 'NoneType' object is not subscriptable", "type_error"),
    ("TypeError: object of type 'float' has no len()", "type_error"),
    ("TypeError: 'tuple' object does not support item assignment", "type_error"),
    ("TypeError: add() missing 1 required positional argument: 'b'", "type_error"),
    ("TypeError: 'int' object is not callable", "type_error"),
    ("TypeError: can only concatenate str (not 'int') to str", "type_error"),
    ("TypeError: object is not subscriptable or slicable", "type_error"),
    ("TypeError: invalid arguments passed to function", "type_error"),
    ("TypeError: cannot unpack non-iterable int object", "type_error"),
    ("TypeError: 'list' object cannot be interpreted as an integer", "type_error"),
    ("TypeError: 'dict' object is not callable", "type_error"),

    # Index Errors / Key Errors
    ("IndexError: list index out of range", "index_error"),
    ("IndexError: string index out of range", "index_error"),
    ("KeyError: 'missing_key'", "index_error"),
    ("KeyError: 404", "index_error"),
    ("IndexError: tuple index out of range", "index_error"),
    ("KeyError: 'user_id' not found in dictionary", "index_error"),
    ("IndexError: index 5 is out of bounds for axis 0 with size 2", "index_error"),
    ("KeyError: database record field does not exist", "index_error"),
    ("IndexError: pop from empty list", "index_error"),
    ("KeyError: accessing absent dictionary value", "index_error"),
    ("KeyError: 'items' is missing", "index_error"),
    ("IndexError: list assignment index out of range", "index_error"),

    # Logic Errors
    ("output is always the same regardless of input", "logic_error"),
    ("infinite loop detected", "logic_error"),
    ("wrong result returned from function", "logic_error"),
    ("off by one error in loop count", "logic_error"),
    ("function returns None instead of boolean value", "logic_error"),
    ("sorting order is reversed", "logic_error"),
    ("incorrect mathematical calculation or formula", "logic_error"),
    ("variable values are updated incorrectly inside loop", "logic_error"),
    ("condition is always True causing loop to run forever", "logic_error"),
    ("algorithm computes wrong average or sum", "logic_error"),
    ("fibonacci function returns wrong values for index n", "logic_error"),
    ("binary search gets stuck in middle element", "logic_error"),
    ("sorting algorithm fails on edge case list", "logic_error")
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

    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(os.path.dirname(current_dir), "models")
    os.makedirs(models_dir, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(models_dir, "error_classifier.pth"))
    print("Model saved.")

if __name__ == "__main__":
    train()