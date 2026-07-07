import json
from pathlib import Path

notebook_path = Path(__file__).resolve().parents[1] / "trained_model" / "GUARDIAN_POC.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

modified = False
for idx, cell in enumerate(nb['cells']):
    if cell.get('cell_type') == 'code':
        source = cell.get('source', [])
        new_source = []
        cell_modified = False
        for line in source:
            # Replace old_id = int(parts[0])
            if "old_id = int(parts[0])" in line:
                line = line.replace("old_id = int(parts[0])", "old_id = int(float(parts[0]))")
                cell_modified = True
            # Replace class_counts[int(parts[0])]
            if "class_counts[int(parts[0])]" in line:
                line = line.replace("class_counts[int(parts[0])]", "class_counts[int(float(parts[0]))]")
                cell_modified = True
            # Replace secondary class_counts get call if present
            if "class_counts.get(int(parts[0])" in line:
                line = line.replace("class_counts.get(int(parts[0])", "class_counts.get(int(float(parts[0]))")
                cell_modified = True
            new_source.append(line)
        if cell_modified:
            cell['source'] = new_source
            modified = True
            print(f"Modified Cell {idx}")

if modified:
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print("Notebook successfully fixed!")
else:
    print("No matches found to modify.")
