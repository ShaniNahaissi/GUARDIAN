import json
from pathlib import Path

notebook_path = Path(__file__).resolve().parents[1] / "trained_model" / "GUARDIAN_POC.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

print(f"Total cells: {len(nb['cells'])}")
for idx, cell in enumerate(nb['cells']):
    cell_type = cell.get('cell_type', '')
    source = cell.get('source', [])
    source_str = "".join(source)
    first_few_lines = "\n".join(source_str.split("\n")[:4])
    print(f"Cell {idx} | Type: {cell_type} | Metadata ID: {cell.get('metadata', {}).get('id', 'N/A')}")
    print(f"--- Source (first 4 lines) ---\n{first_few_lines}\n------------------------------\n")
