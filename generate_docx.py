import os
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_styled_paragraph(doc, text, style='Normal', space_after=6, line_spacing=1.15):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    
    # Simple inline bold parsing: **text**
    parts = re.split(r'(\*\*.*?\*\*)', text)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            run = p.add_run(part[2:-2])
            run.bold = True
        else:
            p.add_run(part)
    return p

def convert_md_to_docx(md_path, output_docx_path):
    doc = Document()

    # Set page margins (1 inch)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Configure Default Font
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Calibri'
    font.size = Pt(11)
    font.color.rgb = RGBColor(0x26, 0x26, 0x26)

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False
    code_lines = []
    in_table = False
    table_lines = []

    def flush_code_block():
        nonlocal code_lines
        if not code_lines:
            return
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.right_indent = Inches(0.2)
        
        full_code = "".join(code_lines).rstrip()
        run = p.add_run(full_code)
        run.font.name = 'Consolas'
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
        code_lines = []

    def flush_table():
        nonlocal table_lines
        if not table_lines:
            return
        # Parse markdown table
        rows_data = []
        for l in table_lines:
            if '---' in l:
                continue
            cols = [c.strip() for c in l.strip().split('|')[1:-1]]
            if cols:
                rows_data.append(cols)
        
        if rows_data:
            table = doc.add_table(rows=len(rows_data), cols=len(rows_data[0]))
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.style = 'Table Grid'
            for r_idx, row_cols in enumerate(rows_data):
                for c_idx, text in enumerate(row_cols):
                    if c_idx < len(table.columns):
                        cell = table.cell(r_idx, c_idx)
                        cell.text = ""
                        p = cell.paragraphs[0]
                        p.paragraph_format.space_after = Pt(2)
                        p.paragraph_format.space_before = Pt(2)
                        
                        parts = re.split(r'(\*\*.*?\*\*)', text)
                        for part in parts:
                            if part.startswith('**') and part.endswith('**'):
                                run = p.add_run(part[2:-2])
                                run.bold = True
                            else:
                                p.add_run(part)
                                
                        if r_idx == 0:
                            for run in p.runs:
                                run.bold = True
                            set_cell_background(cell, "E5E7EB")
                        set_cell_margins(cell, top=60, bottom=60, left=100, right=100)
            doc.add_paragraph() # spacing after table
        table_lines = []

    for l in lines:
        line = l.rstrip('\r\n')

        # Code block toggle
        if line.strip().startswith('```'):
            if in_code_block:
                flush_code_block()
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line + '\n')
            continue

        # Table lines
        if line.strip().startswith('|') and line.strip().endswith('|'):
            in_table = True
            table_lines.append(line)
            continue
        elif in_table:
            flush_table()
            in_table = False

        # Horizontal rule
        if line.strip() == '---' or line.strip() == '***':
            doc.add_paragraph()
            continue

        # Headings
        if line.startswith('# '):
            p = doc.add_heading(line[2:].strip(), level=0)
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(6)
            continue
        elif line.startswith('## '):
            p = doc.add_heading(line[3:].strip(), level=1)
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            continue
        elif line.startswith('### '):
            p = doc.add_heading(line[4:].strip(), level=2)
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(4)
            continue
        elif line.startswith('#### '):
            p = doc.add_heading(line[5:].strip(), level=3)
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            continue
        elif line.startswith('##### '):
            p = doc.add_heading(line[6:].strip(), level=4)
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            continue

        # Bullet lists
        if line.strip().startswith('* ') or line.strip().startswith('- '):
            text = line.strip()[2:].strip()
            add_styled_paragraph(doc, text, style='List Bullet', space_after=3)
            continue

        # Ordered lists
        match = re.match(r'^\d+\.\s+(.*)', line.strip())
        if match:
            text = match.group(1)
            add_styled_paragraph(doc, text, style='List Number', space_after=3)
            continue

        # Normal text
        if line.strip():
            add_styled_paragraph(doc, line.strip(), style='Normal', space_after=6)

    try:
        doc.save(output_docx_path)
        print(f"Successfully generated Word document: {output_docx_path}")
    except PermissionError:
        fallback_path = output_docx_path.replace(".docx", "_New.docx")
        print(f"WARNING: Permission denied writing to {output_docx_path}. The file might be open in another application.")
        print(f"Attempting to write to fallback file: {fallback_path}")
        doc.save(fallback_path)
        print(f"Successfully generated fallback Word document: {fallback_path}")

if __name__ == '__main__':
    md_path = os.path.join(os.path.dirname(__file__), 'FINAL_PROJECT_BOOK.md')
    out_path = os.path.join(os.path.dirname(__file__), 'GUARDIAN_Final_Project_Book.docx')
    convert_md_to_docx(md_path, out_path)
