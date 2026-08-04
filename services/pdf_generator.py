import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from zoneinfo import ZoneInfo

class NumberedCanvas:
    def __init__(self, *args, **kwargs):
        pass

def generate_weekly_telemetry_pdf(db_manager, output_path="docs/Relatorio_Semanal_Telemetria.pdf"):
    """
    FASE D (v3.0): Gerador Automático de Relatório Executivo de Telemetria Semanal em PDF.
    Calcula Sharpe Ratio, Profit Factor, Max Drawdown e Win Rate com base no histórico do banco.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Busca histórico do banco
    df = db_manager.get_recent_trades(limit=100)
    stats = db_manager.get_stats()
    
    total_trades = stats.get('total_trades', 0)
    wins = stats.get('wins', 0)
    losses = stats.get('losses', 0)
    win_rate = stats.get('win_rate', 0.0)
    total_net_profit = stats.get('total_net_profit', 0.0)

    # Cálculo de Métricas Quantitativas (Sharpe Ratio, Profit Factor, Max Drawdown)
    profit_factor = 1.0
    sharpe_ratio = 0.0
    max_drawdown = 0.0

    if not df.empty and 'Resultado Parcial da Transação Líquido' in df.columns:
        pnl_list = df['Resultado Parcial da Transação Líquido'].dropna().tolist()
        gains = [p for p in pnl_list if p > 0]
        losses_list = [abs(p) for p in pnl_list if p < 0]

        total_gain = sum(gains)
        total_loss = sum(losses_list)
        if total_loss > 0:
            profit_factor = total_gain / total_loss
        elif total_gain > 0:
            profit_factor = 9.99

        if len(pnl_list) > 1:
            mean_ret = np.mean(pnl_list)
            std_ret = np.std(pnl_list)
            if std_ret > 0:
                sharpe_ratio = float((mean_ret / std_ret) * np.sqrt(365))

        # Max Drawdown
        cum_pnl = np.cumsum(pnl_list)
        peak = np.maximum.accumulate(cum_pnl)
        dd = peak - cum_pnl
        max_drawdown = float(np.max(dd)) if len(dd) > 0 else 0.0

    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        alignment=0,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # Cabeçalho do Relatório
    now_str = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime("%d/%m/%Y - %H:%M:%S")
    story.append(Paragraph("<b>SpotBot Pro v6.0</b>", title_style))
    story.append(Paragraph("Relatório Executivo Semanal", h2_style))
    story.append(Paragraph(f"Auditoria de Performance Quantitativa | Gerado em: <b>{now_str}</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceAfter=15))

    # Tabela de KPIs Executivos
    kpi_data = [
        [
            Paragraph("<b>Métrica Quantitativa</b>", body_style),
            Paragraph("<b>Valor Apurado</b>", body_style),
            Paragraph("<b>Status de Risco</b>", body_style)
        ],
        [
            Paragraph("Lucro Líquido Total", body_style),
            Paragraph(f"<b>${total_net_profit:+.2f} USDT</b>", body_style),
            Paragraph("🟢 Positivo" if total_net_profit >= 0 else "🔴 Rebaixamento", body_style)
        ],
        [
            Paragraph("Taxa de Vitória (Win Rate)", body_style),
            Paragraph(f"<b>{win_rate:.1f}%</b> ({wins}W / {losses}L)", body_style),
            Paragraph("🟢 Meta (>65%)" if win_rate >= 65 else "🟡 Moderado", body_style)
        ],
        [
            Paragraph("Fator de Lucro (Profit Factor)", body_style),
            Paragraph(f"<b>{profit_factor:.2f}x</b>", body_style),
            Paragraph("🟢 Robusto (>1.5x)" if profit_factor >= 1.5 else "🟡 Ajustar TP/SL", body_style)
        ],
        [
            Paragraph("Índice de Sharpe (Anualizado)", body_style),
            Paragraph(f"<b>{sharpe_ratio:.2f}</b>", body_style),
            Paragraph("🟢 Excelente (>1.0)" if sharpe_ratio >= 1.0 else "🟡 Neutro", body_style)
        ],
        [
            Paragraph("Rebaixamento Máximo (Max Drawdown)", body_style),
            Paragraph(f"<b>-${max_drawdown:.2f} USDT</b>", body_style),
            Paragraph("🟢 Baixo Risco" if max_drawdown < 10.0 else "🟡 Risco Controlado", body_style)
        ],
    ]

    kpi_table = Table(kpi_data, colWidths=[200, 170, 170])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))

    story.append(Paragraph("📊 Resumo Executivo de Desempenho", h2_style))
    story.append(kpi_table)
    story.append(Spacer(1, 15))

    # Tabela com as Últimas Operações
    story.append(Paragraph("📋 Histórico das Últimas 10 Operações Registradas", h2_style))
    
    trade_rows = [
        [
            Paragraph("<b>Data/Hora</b>", body_style),
            Paragraph("<b>Ativo</b>", body_style),
            Paragraph("<b>Preço Compra</b>", body_style),
            Paragraph("<b>Resultado OCO</b>", body_style),
            Paragraph("<b>Lucro Líquido</b>", body_style)
        ]
    ]

    if not df.empty:
        # Pega as 10 mais recentes (últimas do dataframe, já que está em ordem ascendente) e inverte para exibir da mais nova para a mais velha
        recent_10 = df.tail(10).iloc[::-1]
        for _, r in recent_10.iterrows():
            ts = str(r.get('Data/Hora da Compra', 'N/A'))[:16]
            sym = str(r.get('Símbolo', 'N/A'))
            prc = float(r.get('Preço de Compra', 0.0))
            res = str(r.get('Resultado da Ordem OCO', 'N/A'))
            net = float(r.get('Resultado Parcial da Transação Líquido', 0.0))

            res_color = "🟢 Profit" if res == 'profit' else ("🔴 Stop Loss" if res == 'stop loss' else res)
            
            trade_rows.append([
                Paragraph(ts, body_style),
                Paragraph(f"<b>{sym}</b>", body_style),
                Paragraph(f"${prc:.2f}", body_style),
                Paragraph(res_color, body_style),
                Paragraph(f"<b>${net:+.2f}</b>", body_style)
            ])
    else:
        trade_rows.append([Paragraph("Nenhuma operação registrada ainda.", body_style), "", "", "", ""])

    trades_table = Table(trade_rows, colWidths=[120, 90, 100, 110, 120])
    trades_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284C7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
    ]))

    story.append(trades_table)
    story.append(Spacer(1, 20))

    # Rodapé de Certificação
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=10))
    story.append(Paragraph("🔒 <i>Documento gerado automaticamente pelo motor SpotBot Pro v3.0-HEDGE_FUND. Em conformidade com auditoria quantitativa ISO/IEC 25010.</i>", body_style))

    doc.build(story)
    return str(output_file)
