import torch
import torch.nn as nn

ERROR_CLASSES = [
    "syntax_error",
    "runtime_error",
    "type_error",
    "index_error",
    "logic_error"
]

class ErrorClassifier(nn.Module):
    def __init__(self, input_dim=384, hidden_dim=128, num_classes=5):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        return self.net(x)