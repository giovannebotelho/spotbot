import os
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, KeepTogether
)
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
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        if self._pageNumber > 1:
            # Header Top Bar
            self.drawString(40, 818, "SPOTBOT PRO v3.0.0-HEDGE_FUND | MANUAL TÉCNICO DE ENGENHARIA DE TRADING")
            self.drawRightString(555, 818, "CONFIDENCIAL & PROPRIETÁRIO")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(40, 810, 555, 810)
            
            # Footer Bottom Bar
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(40, 45, 555, 45)
            
            self.drawString(40, 32, "ISO/IEC 25010 MEDICAL-GRADE FAULT-TOLERANT STANDARD")
            page_text = f"Página {self._pageNumber} de {page_count}"
            self.drawRightString(555, 32, page_text)
            
        self.restoreState()

def build_pdf_from_markdown(md_file="docs/DOCUMENTATION.md", output_pdf="docs/SpotBot_Pro_Documentacao_Tecnica.pdf"):
    md_path = Path(md_file)
    pdf_path = Path(output_pdf)
    
    if not md_path.exists():
        print(f"Erro: Arquivo {md_file} não encontrado.")
        return

    content = md_path.read_text(encoding='utf-8')
    
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0284C7'),
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'ChapterH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#0369A1'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=body_style,
        leftIndent=15,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        fontName='Courier',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0F172A'),
        backColor=colors.HexColor('#F8FAFC'),
        borderColor=colors.HexColor('#E2E8F0'),
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=8,
        spaceBefore=6
    )

    story = []
    lines = content.split('\n')
    
    in_code_block = False
    code_buffer = []

    for line in lines:
        stripped = line.strip()
        
        # Check code block fences
        if stripped.startswith('```'):
            if in_code_block:
                in_code_block = False
                code_text = "\n".join(code_buffer)
                code_text_escaped = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>').replace(' ', '&nbsp;')
                story.append(Paragraph(code_text_escaped, code_style))
                code_buffer = []
            else:
                in_code_block = True
                code_buffer = []
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        if not stripped:
            continue

        # Format markdown headers
        if stripped.startswith('# '):
            text = stripped[2:].replace('**', '<b>').replace('**', '</b>')
            story.append(Paragraph(text, title_style))
            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#0284C7'), spaceAfter=12))
        elif stripped.startswith('## '):
            text = stripped[3:]
            if 'SPOTBOT PRO' in text:
                story.append(Paragraph(text, subtitle_style))
            else:
                story.append(Paragraph(text, h1_style))
                story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=8))
        elif stripped.startswith('### '):
            text = stripped[4:]
            story.append(Paragraph(text, h2_style))
        elif stripped.startswith('---'):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E2E8F0'), spaceAfter=8, spaceBefore=8))
        elif stripped.startswith('- ') or stripped.startswith('* '):
            formatted = stripped[2:]
            formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted)
            formatted = re.sub(r'\*(.*?)\*', r'<i>\1</i>', formatted)
            formatted = re.sub(r'`(.*?)`', r'<font face="Courier" color="#0284C7">\1</font>', formatted)
            story.append(Paragraph(f"• {formatted}", bullet_style))
        elif re.match(r'^\d+\.', stripped):
            formatted = re.sub(r'^\d+\.\s*', '', stripped)
            formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted)
            formatted = re.sub(r'\*(.*?)\*', r'<i>\1</i>', formatted)
            formatted = re.sub(r'`(.*?)`', r'<font face="Courier" color="#0284C7">\1</font>', formatted)
            story.append(Paragraph(f"<b>{stripped.split('.')[0]}.</b> {formatted}", bullet_style))
        elif stripped.startswith('$$') and stripped.endswith('$$'):
            formula = stripped[2:-2].strip()
            formula_escaped = formula.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(f"<b>[Fórmula Matemática]</b>: <font face=\"Courier\" color=\"#0F172A\">{formula_escaped}</font>", ParagraphStyle('Formula', parent=body_style, backColor=colors.HexColor('#F1F5F9'), borderPadding=6, leftIndent=20)))
        else:
            formatted = stripped
            formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted)
            formatted = re.sub(r'\*(.*?)\*', r'<i>\1</i>', formatted)
            formatted = re.sub(r'`(.*?)`', r'<font face="Courier" color="#0284C7">\1</font>', formatted)
            story.append(Paragraph(formatted, body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"SUCCESS: PDF gerado com sucesso em {pdf_path}")

if __name__ == "__main__":
    build_pdf_from_markdown()
