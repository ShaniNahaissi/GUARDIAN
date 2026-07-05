#!/usr/bin/env python3
"""PyTorch training script and boilerplate for the Temporal Action GRU Classifier.

This script defines the PyTorch training loop and custom dataset loader for training
the lightweight GRU sequence classifier on the Smart-City CCTV Violence Detection (SCVD),
CCTV Action Recognition, UCF Crime, and Weapons Detection datasets, and exports the
resulting parameters to a NumPy-compatible weights file.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import numpy as np

# PyTorch imports (lazy-loaded or conditionally imported in case local environment lacks it)
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    torch = None
    nn = None
    optim = None
    Dataset = object
    DataLoader = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("guardian.train_temporal")

REPO_ROOT = Path(__file__).resolve().parents[1]


if torch is not None and nn is not None:
    class TemporalGRUClassifier(nn.Module):
        """PyTorch implementation of the GRU action classifier matching the NumPy forward pass."""
        def __init__(self, input_dim: int = 12, hidden_dim: int = 32, num_classes: int = 4) -> None:
            super().__init__()
            self.hidden_dim = hidden_dim
            self.gru = nn.GRU(input_dim, hidden_dim, batch_first=True)
            self.fc = nn.Linear(hidden_dim, num_classes)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x shape: (batch_size, seq_len, input_dim)
            out, _ = self.gru(x)
            # Take the output of the last time step
            last_out = out[:, -1, :]
            logits = self.fc(last_out)
            return logits
else:
    class TemporalGRUClassifier:
        pass


class TemporalActionDataset(Dataset):
    """Custom Dataset for sequence threat classification.

    Loads and structures sequences of bounding boxes, velocities, and proximities.
    """
    def __init__(
        self,
        data_dir: str,
        sequence_length: int = 30,
        feature_dim: int = 12,
        is_train: bool = True
    ) -> None:
        self.data_dir = Path(data_dir)
        self.sequence_length = sequence_length
        self.feature_dim = feature_dim
        self.is_train = is_train
        self.samples = self._load_and_preprocess_dataset()

    def _load_and_preprocess_dataset(self) -> list[tuple[np.ndarray, int]]:
        """Placeholder structuring files from SCVD, CCTV action, and UCF Crime directories.

        In a real run, this parses coordinate histories from tracking logs or annotation txts.
        """
        samples: list[tuple[np.ndarray, int]] = []
        
        # Target classes: 0: Normal, 1: Shooting, 2: Stabbing, 3: Violence
        # Let's generate synthetic sequences for boilerplate runs, or load if files exist.
        scvd_path = self.data_dir / "SCVD"
        ucf_path = self.data_dir / "UCF_Crime"
        weapons_path = self.data_dir / "Weapons_Detection"
        
        if not self.data_dir.exists() or not any([scvd_path.exists(), ucf_path.exists(), weapons_path.exists()]):
            logger.warning(
                "Specified datasets directories not found at %s. Creating synthetic dataset for boilerplate validation.",
                self.data_dir
            )
            # Create synthetic samples: 100 per class
            rng = np.random.default_rng(42 if self.is_train else 24)
            for cls_idx in range(4):
                for _ in range(100):
                    # Sequence of shape (sequence_length, feature_dim)
                    seq = rng.normal(0, 0.5, (self.sequence_length, self.feature_dim)).astype(np.float32)
                    # Add features characterising the class
                    if cls_idx == 0:  # Normal
                        seq[:, 9] = 1.0  # Far from weapons
                    elif cls_idx == 1:  # Shooting
                        seq[:, 8] = 0.95  # High detection confidence
                        seq[:, 9] = rng.uniform(0.0, 0.2, self.sequence_length)  # Close to weapon
                    elif cls_idx == 2:  # Stabbing
                        seq[:, 9] = rng.uniform(0.0, 0.1, self.sequence_length)  # Very close to weapon
                        seq[:, 11] = 1.0  # Weapon overlapping
                    elif cls_idx == 3:  # Violence
                        seq[:, 10] = rng.uniform(0.0, 0.25, self.sequence_length)  # Suspects close to each other
                    
                    samples.append((seq, cls_idx))
            return samples
            
        # Real dataset ingestion parser boilerplate:
        # 1. Load punches/kicks from SCVD and CCTV Action Recognition
        if scvd_path.exists():
            logger.info("Ingesting SCVD punches/kicks data from %s...", scvd_path)
            # Parse CSVs or annotation folders...
            pass
            
        # 2. Load shootings and stabbings from UCF Crime
        if ucf_path.exists():
            logger.info("Ingesting UCF Crime shooting/stabbing annotations from %s...", ucf_path)
            # Parse UCF Crime labels...
            pass
            
        # 3. Load baseline static objects (Weapons Detection)
        if weapons_path.exists():
            logger.info("Ingesting weapons baseline dataset from %s...", weapons_path)
            # Parse baseline static shapes...
            pass
            
        return samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor | np.ndarray, int]:
        features, label = self.samples[idx]
        if torch is not None:
            return torch.tensor(features, dtype=torch.float32), label
        return features, label


def export_to_numpy_weights(model: nn.Module, output_path: Path) -> None:
    """Exports trained PyTorch weights to a NumPy-compatible .npz format."""
    state_dict = model.state_dict()
    
    # Extract GRU weights (PyTorch aggregates input & hidden weights)
    w_ih = state_dict["gru.weight_ih_l0"].cpu().numpy()  # Shape: (3 * hidden_dim, input_dim)
    w_hh = state_dict["gru.weight_hh_l0"].cpu().numpy()  # Shape: (3 * hidden_dim, hidden_dim)
    b_ih = state_dict["gru.bias_ih_l0"].cpu().numpy()    # Shape: (3 * hidden_dim,)
    b_hh = state_dict["gru.bias_hh_l0"].cpu().numpy()    # Shape: (3 * hidden_dim,)
    
    # Extract Fully Connected Layer weights
    w_fc = state_dict["fc.weight"].cpu().numpy()        # Shape: (num_classes, hidden_dim)
    b_fc = state_dict["fc.bias"].cpu().numpy()          # Shape: (num_classes,)
    
    np.savez_compressed(
        output_path,
        w_ih=w_ih,
        w_hh=w_hh,
        b_ih=b_ih,
        b_hh=b_hh,
        w_fc=w_fc,
        b_fc=b_fc
    )
    logger.info("Successfully exported weights to NumPy format at: %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Train Temporal Action GRU Classifier")
    parser.add_argument("--data_dir", type=str, default="./data", help="Root folder for SCVD, UCF datasets")
    parser.add_argument("--epochs", type=int, default=15, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=32, help="DataLoader batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Adam optimizer learning rate")
    parser.add_argument(
        "--output_weights",
        type=str,
        default=str(REPO_ROOT / "trained_model" / "temporal_action_weights.npz"),
        help="Path to export final weights"
    )
    args = parser.parse_args()

    if torch is None or nn is None or optim is None:
        logger.error(
            "PyTorch is not installed in the current environment. "
            "Please install torch to execute training: 'pip install torch'"
        )
        return

    logger.info("Initializing dataset loaders...")
    train_dataset = TemporalActionDataset(args.data_dir, is_train=True)
    val_dataset = TemporalActionDataset(args.data_dir, is_train=False)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)

    logger.info("Building PyTorch Temporal GRU Model...")
    model = TemporalGRUClassifier(input_dim=12, hidden_dim=32, num_classes=4)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    logger.info("Training on device: %s", device)

    best_loss = float("inf")
    
    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        correct = 0
        total = 0
        
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * batch_x.size(0)
            preds = torch.argmax(logits, dim=1)
            correct += (preds == batch_y).sum().item()
            total += batch_y.size(0)
            
        train_loss /= len(train_dataset)
        train_acc = correct / total
        
        # Validation Step
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                logits = model(batch_x)
                loss = criterion(logits, batch_y)
                
                val_loss += loss.item() * batch_x.size(0)
                preds = torch.argmax(logits, dim=1)
                val_correct += (preds == batch_y).sum().item()
                val_total += batch_y.size(0)
                
        val_loss /= len(val_dataset)
        val_acc = val_correct / val_total
        
        logger.info(
            "Epoch %d/%d: Train Loss=%.4f, Train Acc=%.2f%% | Val Loss=%.4f, Val Acc=%.2f%%",
            epoch, args.epochs, train_loss, train_acc * 100, val_loss, val_acc * 100
        )
        
        if val_loss < best_loss:
            best_loss = val_loss
            # Save checkpoints
            torch.save(model.state_dict(), REPO_ROOT / "trained_model" / "temporal_action_best.pt")

    logger.info("Training complete. Exporting weights to NumPy...")
    # Load best checkpoint
    model.load_state_dict(torch.load(REPO_ROOT / "trained_model" / "temporal_action_best.pt"))
    export_to_numpy_weights(model, Path(args.output_weights))


if __name__ == "__main__":
    main()
