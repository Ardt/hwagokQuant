"""LSTM model: PyTorch-based binary classifier for price direction."""

import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import config as cfg
from src.logger import get

log = get("model.lstm")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODELS_DIR = os.path.join(cfg.DATA_DIR, "models")


class LSTMModel(nn.Module):
    def __init__(self, input_size: int):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=cfg.HIDDEN_SIZE,
            num_layers=cfg.NUM_LAYERS,
            dropout=cfg.DROPOUT,
            batch_first=True,
        )
        self.fc = nn.Linear(cfg.HIDDEN_SIZE, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return torch.sigmoid(self.fc(out[:, -1, :]))


def make_dataloader(X: np.ndarray, y: np.ndarray, shuffle: bool = True) -> DataLoader:
    """Create a DataLoader from numpy arrays."""
    X_t = torch.FloatTensor(X)
    y_t = torch.FloatTensor(y).unsqueeze(1)
    return DataLoader(TensorDataset(X_t, y_t), batch_size=cfg.BATCH_SIZE, shuffle=shuffle)


def train_model(X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray):
    """Train LSTM model with early stopping. Returns trained model and loss history."""
    model = LSTMModel(input_size=X_train.shape[2]).to(device)
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.LEARNING_RATE)

    train_loader = make_dataloader(X_train, y_train, shuffle=True)
    val_loader = make_dataloader(X_val, y_val, shuffle=False)

    best_val_loss, patience, counter = float("inf"), 10, 0
    history = {"train_loss": [], "val_loss": []}

    for epoch in range(cfg.EPOCHS):
        # Train
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            loss = criterion(model(X_batch), y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        # Validate
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                val_loss += criterion(model(X_batch), y_batch).item()
        val_loss /= len(val_loader)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        if (epoch + 1) % 5 == 0:
            print(f"Epoch {epoch+1}/{cfg.EPOCHS} — train: {train_loss:.4f}, val: {val_loss:.4f}")

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            counter = 0
            best_state = model.state_dict().copy()
        else:
            counter += 1
            if counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break

    model.load_state_dict(best_state)
    return model, history


def predict(model: LSTMModel, X: np.ndarray) -> np.ndarray:
    """Run inference, return probabilities."""
    model.eval()
    X_t = torch.FloatTensor(X).to(device)
    with torch.no_grad():
        probs = model(X_t).cpu().numpy().flatten()
    return probs


def save_model(model: LSTMModel, ticker: str):
    """Save model weights to data/models/{ticker}_lstm.pt"""
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, f"{ticker}_lstm.pt")
    torch.save({"state_dict": model.state_dict(), "input_size": model.lstm.input_size}, path)
    log.info(f"Saved model: {path}")


def load_model(ticker: str) -> LSTMModel | None:
    """Load model weights from data/models/{ticker}_lstm.pt"""
    path = os.path.join(MODELS_DIR, f"{ticker}_lstm.pt")
    if not os.path.exists(path):
        return None
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    model = LSTMModel(input_size=checkpoint["input_size"]).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    log.info(f"Loaded model: {path}")
    return model


def has_saved_model(ticker: str) -> bool:
    return os.path.exists(os.path.join(MODELS_DIR, f"{ticker}_lstm.pt"))
