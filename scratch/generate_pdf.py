import os
import re
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (Top bar)
        self.drawString(40, 815, "SpotBot Pro v2.5.0-QUANT | Documentação Técnica de Arquitetura")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(40, 808, 555, 808)
        
        # Footer (Bottom bar)
        self.line(40, 45, 555, 45)
        self.drawString(40, 32, "CONFIDENCIAL & PROPRIETÁRIO — SPOTBOT PRO QUANTITATIVE ENGINE")
        page_str = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(555, 32, page_str)
        self.restoreState()

def convert_md_to_pdf(md_filepath, pdf_filepath):
    with open(md_filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    doc = SimpleDocTemplate(
        pdf_filepath,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=55,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()
    
    PRIMARY = colors.HexColor("#0B0E14")
    TEXT_COLOR = colors.HexColor("#1E293B")
    CYAN_ACCENT = colors.HexColor("#0088CC")
    DARK_BLUE = colors.HexColor("#0F172A")
    BG_LIGHT = colors.HexColor("#F8FAFC")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=DARK_BLUE,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'DocH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=CYAN_ACCENT,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=DARK_BLUE,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=TEXT_COLOR,
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        'DocCode',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=colors.HexColor("#E2E8F0"),
        borderWidth=0.5,
        borderPadding=5,
        spaceBefore=4,
        spaceAfter=6
    )

    story = []

    lines = content.split('\n')
    in_code_block = False
    code_lines = []
    in_table = False
    table_data = []

    def clean_text(text):
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        text = re.sub(r'`(.*?)`', r'<font face="Courier" color="#0088CC">\1</font>', text)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<font color="#0088CC"><u>\1</u></font>', text)
        return text

    for line in lines:
        stripped = line.strip()

        # Handle Code Blocks
        if stripped.startswith('```'):
            if in_code_block:
                in_code_block = False
                code_text = "<br/>".join([c.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for c in code_lines])
                story.append(Paragraph(code_text, code_style))
                code_lines = []
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # Handle Tables
        if '|' in line and ('---' in line or ':' in line) and not table_data:
            continue

        if '|' in line:
            parts = [clean_text(p.strip()) for p in line.split('|')[1:-1]]
            if parts and any(parts):
                table_data.append(parts)
                in_table = True
                continue

        if in_table and ('|' not in line or not stripped):
            in_table = False
            if table_data:
                formatted_table_data = []
                for row_idx, row in enumerate(table_data):
                    formatted_row = []
                    for cell in row:
                        style = ParagraphStyle('TableCell', parent=body_style, fontSize=7.5, leading=9.5)
                        if row_idx == 0:
                            style.fontName = 'Helvetica-Bold'
                            style.textColor = colors.white
                        formatted_row.append(Paragraph(cell, style))
                    formatted_row_data = formatted_row
                    formatted_table_data.append(formatted_row_data)

                col_widths = [120, 130, 260] if len(table_data[0]) == 3 else None
                t = Table(formatted_table_data, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])
                ]))
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 6))
                table_data = []

        if not stripped:
            continue

        if stripped.startswith('# '):
            story.append(Paragraph(clean_text(stripped[2:]), title_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=CYAN_ACCENT, spaceBefore=2, spaceAfter=10))
        elif stripped.startswith('## '):
            story.append(Paragraph(clean_text(stripped[3:]), h1_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=2, spaceAfter=6))
        elif stripped.startswith('### '):
            story.append(Paragraph(clean_text(stripped[4:]), h2_style))
        elif stripped.startswith('- ') or stripped.startswith('* '):
            story.append(Paragraph(f"• {clean_text(stripped[2:])}", bullet_style))
        elif re.match(r'^\d+\.', stripped):
            story.append(Paragraph(clean_text(stripped), bullet_style))
        elif stripped.startswith('> '):
            quote_style = ParagraphStyle('Quote', parent=body_style, fontName='Helvetica-Oblique', leftIndent=12, textColor=colors.HexColor("#475569"))
            story.append(Paragraph(clean_text(stripped[2:]), quote_style))
        else:
            story.append(Paragraph(clean_text(stripped), body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"SUCCESS: PDF created at {pdf_filepath}")

if __name__ == "__main__":
    src_md = r"c:\Py\spotbot\docs\DOCUMENTATION.md"
    dst_pdf = r"c:\Py\spotbot\docs\SpotBot_Pro_Documentacao_Tecnica.pdf"
    convert_md_to_pdf(src_md, dst_pdf)
