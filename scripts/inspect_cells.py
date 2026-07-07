import json
from pathlib import Path

notebook_path = Path(__file__).resolve().parents[1] / "trained_model" / "GUARDIAN_POC.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells_to_inspect = [1, 2, 7, 15, 17, 19]
for idx in cells_to_inspect:
    if idx < len(nb['cells']):
        cell = nb['cells'][idx]
        print(f"================ CELL {idx} ================")
        print("".join(cell.get('source', [])))
        print("===========================================\n")
