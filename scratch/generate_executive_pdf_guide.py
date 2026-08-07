import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Cabeçalho (Páginas > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "SPOTBOT PRO v7.0 — GUIA EXECUTIVO PARA O INVESTIDOR")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Rodapé em todas as páginas
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)

        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "SpotBot Pro v7.0 (HedgeFund Edition) • Inteligência Quantitativa & IA Generativa")
        page_str = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()

def create_executive_pdf(output_filename="docs/SpotBot_Pro_Guia_Executivo_do_Usuario.pdf"):
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=54, rightMargin=54,
        topMargin=54, bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Cores de Paleta Premium
    PRIMARY = colors.HexColor("#0F172A")     # Azul Noturno Profundo
    SECONDARY = colors.HexColor("#1E293B")   # Grafite Institucional
    ACCENT = colors.HexColor("#2563EB")      # Azul Royal Elétrico
    SUCCESS = colors.HexColor("#059669")     # Verde Esmeralda
    WARNING = colors.HexColor("#D97706")     # Âmbar Ouro
    TEXT_DARK = colors.HexColor("#1E293B")   # Escuro para Texto
    BG_LIGHT = colors.HexColor("#F8FAFC")    # Cinza Suave de Fundo
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    # Estilos de Parágrafo Personalizados
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=24, leading=28,
        textColor=PRIMARY, alignment=0, spaceAfter=8
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=12, leading=16,
        textColor=colors.HexColor("#475569"), spaceAfter=15
    )
    h1_style = ParagraphStyle(
        'Header1', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=15, leading=19,
        textColor=PRIMARY, spaceBefore=16, spaceAfter=8, keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Header2', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=12, leading=16,
        textColor=ACCENT, spaceBefore=12, spaceAfter=6, keepWithNext=True
    )
    body_style = ParagraphStyle(
        'BodyDark', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9.5, leading=14,
        textColor=TEXT_DARK, spaceAfter=8
    )
    bullet_style = ParagraphStyle(
        'BulletText', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, leading=13.5,
        textColor=TEXT_DARK, leftIndent=12, spaceAfter=4
    )
    box_text_style = ParagraphStyle(
        'BoxText', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=9, leading=13.5,
        textColor=colors.HexColor("#334155")
    )
    table_cell = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=12,
        textColor=TEXT_DARK
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5, leading=12,
        textColor=PRIMARY
    )
    table_cell_header = ParagraphStyle(
        'TableCellHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5, leading=12,
        textColor=colors.white
    )

    story = []

    # ==========================================
    # CABEÇALHO DA CAPA / PRIMEIRA PÁGINA
    # ==========================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("🤖 SpotBot Pro v7.0 (HedgeFund & Futures Edition)", title_style))
    story.append(Paragraph("<b>O Guia Definitivo do Investidor</b> — Entenda Como Funciona o Seu Piloto Automático Quantitativo Sem Jargões Complicados", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=15))

    # ==========================================
    # 1. INTRODUÇÃO
    # ==========================================
    story.append(Paragraph("1. O que é o SpotBot Pro e Por Que Ele Existe?", h1_style))
    intro_text = (
        "Se você já tentou investir no mercado de criptomoedas manualmente, certamente viveu este dilema: "
        "o medo de comprar na hora errada, a dúvida se deve vender ou esperar subir mais, ou a ansiedade de olhar o celular no meio da noite. "
        "O <b>SpotBot Pro v7.0</b> foi criado para eliminar 100% da emoção humana dos seus investimentos. "
        "Ele funciona como um <b>Piloto Automático de Alta Precisão</b>, que analisa o mercado 24 horas por dia, 7 dias por semana, "
        "usando os mesmos modelos matemáticos dos grandes fundos de investimento de Wall Street combinados com a Inteligência Artificial do Google Gemini."
    )
    story.append(Paragraph(intro_text, body_style))

    # Box de Destaque 1
    callout_1 = [
        [Paragraph("<b>💡 O Princípio Sagrado do SpotBot Pro:</b> O robô nunca adivinha o mercado. Ele só entra em uma operação quando múltiplos fatores matemáticos (como volume, notícias, tendência e preço de baleias) concordam exatamente ao mesmo tempo.", box_text_style)]
    ]
    t_callout1 = Table(callout_1, colWidths=[504])
    t_callout1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BFDBFE")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_callout1)
    story.append(Spacer(1, 12))

    # ==========================================
    # 2. DICIONÁRIO TRADUZIDO DE TERMOS
    # ==========================================
    story.append(Paragraph("2. Dicionário Descomplicado: Traduzindo o Mercado Cripto para o Português", h1_style))
    story.append(Paragraph("Para você entender cada notificação que o robô envia no seu Telegram, traduzimos os principais conceitos quantitativos para uma linguagem simples e intuitiva:", body_style))

    terms_data = [
        [Paragraph("Termo em Inglês", table_cell_header), Paragraph("Tradução Simples", table_cell_header), Paragraph("Como o SpotBot Pro Usa?", table_cell_header)],
        
        [Paragraph("Take Profit (TP)", table_cell_bold), Paragraph("Trava de Lucro no Bolso", table_cell), Paragraph("Preço programado para vender e colocar o lucro automaticamente na sua conta.")],
        
        [Paragraph("Stop Loss (SL)", table_cell_bold), Paragraph("Cinto de Segurança de Perda", table_cell), Paragraph("Preço de emergência para limitar uma perda pequena caso o mercado caia de repente.")],
        
        [Paragraph("Ordem OCO", table_cell_bold), Paragraph("Ordem Dupla Inteligente", table_cell), Paragraph("Ordem enviada à Binance com TP e SL simultâneos. Se o TP vende no lucro, o SL é cancelado sozinho!")],
        
        [Paragraph("Orderbook (Livro)", table_cell_bold), Paragraph("A Fila da Feira de Compras", table_cell), Paragraph("Onde todos os compradores e vendedores da Binance colocam suas propostas de preço.")],
        
        [Paragraph("Whale Walls", table_cell_bold), Paragraph("Paredões das Baleias", table_cell), Paragraph("Grandes investidores colocando milhões em uma única faixa de preço. O bot antecipa o lucro antes deles.")],
        
        [Paragraph("ATR (Volatilidade)", table_cell_bold), Paragraph("Medidor de Balanço do Mar", table_cell), Paragraph("Mede o quanto o preço está balançando para ajustar o tamanho do cinto de segurança (SL).")],
        
        [Paragraph("Smart Recovery DCA", table_cell_bold), Paragraph("Recompra no Desconto", table_cell), Paragraph("Em caídas rápidas de pavio, recompra no suporte de Fibonacci para puxar o preço médio e sair no lucro!")],
        
        [Paragraph("Lead-Lag Alpha", table_cell_bold), Paragraph("Efeito Dominó do Bitcoin", table_cell), Paragraph("O Bitcoin dispara primeiro e as outras moedas seguem 30s depois. O robô entra na moeda antes que ela suba.")],
        
        [Paragraph("CVD (Tape Reading)", table_cell_bold), Paragraph("Pressão no Balcão", table_cell), Paragraph("Verifica se há compradores 'devorando' as moedas a qualquer preço na Binance.")],
        
        [Paragraph("Kelly Criterion", table_cell_bold), Paragraph("Calculadora de Lote Profissional", table_cell), Paragraph("Fórmula matemática que decide exatamente quanto dinheiro alocar no trade com base no histórico.")],
        
        [Paragraph("Gemini IA", table_cell_bold), Paragraph("O Leitor de Notícias IA", table_cell), Paragraph("A IA do Google lê as manchetes do mercado e avisa se há pânico noticioso antes de comprar.")]
    ]

    t_terms = Table(terms_data, colWidths=[110, 130, 264])
    t_terms.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_terms)
    story.append(Spacer(1, 14))

    # ==========================================
    # 3. O PASSO A PASSO DE UMA OPERAÇÃO (FLUXO)
    # ==========================================
    story.append(Paragraph("3. O Passo a Passo de Uma Operação (A Jornada do Trade)", h1_style))
    story.append(Paragraph("Veja como o SpotBot Pro analisa e executa uma compra do início ao fim sem você precisar mover um dedo:", body_style))

    steps_data = [
        Paragraph("<b>Etapa 1: Análise Noticiosa pela IA (Filtro de Pânico)</b><br/>Antes de olhar qualquer gráfico, a IA Gemini lê as últimas notícias do mercado cripto. Se houver pânico ou falência de corretora, o robô trava as compras e protege o seu dinheiro.", bullet_style),
        Paragraph("<b>Etapa 2: Checagem Tridimensional (Multi-Timeframe 4H + 1H + 15M)</b><br/>O robô olha a moeda em três lentes: o gráfico de 4 horas (macro), o de 1 hora (médio) e o de 15 minutos (gatilho). Ele exige que pelo menos 70% dos sinais estejam apontando para alta.", bullet_style),
        Paragraph("<b>Etapa 3: Efeito Dominó do Bitcoin (Lead-Lag Engine)</b><br/>O robô detecta se o Bitcoin deu uma arrancada forte de volume no último minuto. Como as moedas menores demoram alguns segundos para reagir, ele compra a altcoin no início exato da subida.", bullet_style),
        Paragraph("<b>Etapa 4: Leitura do Balcão de Negócios (Order Flow CVD)</b><br/>O robô examina as últimas 500 compras reais feitas na Binance. Se os compradores estiverem atacando o mercado com mais de 60% de dominância, a compra é confirmada.", bullet_style),
        Paragraph("<b>Etapa 5: Verificação dos Paredões das Baleias (Orderbook Depth 50)</b><br/>Ele analisa até 50 níveis de preço no livro de ofertas. Se houver um muro de vendas de uma baleia em $10.00, o robô ajusta o alvo para vender em $9.98, garantindo que o seu lucro entre no bolso antes da baleia.", bullet_style),
        Paragraph("<b>Etapa 6: Ajuste do Cinto de Segurança por Volatilidade (ATR)</b><br/>Se o mercado estiver calmo, o Stop Loss fica em -1.2%. Se estiver agitado, ele afasta o Stop Loss para evitar ser violinado por balanços temporários.", bullet_style),
        Paragraph("<b>Etapa 7: Cálculo Matemático do Lote (Kelly Criterion)</b><br/>A fórmula de Kelly lê a taxa de vitória real acumulada nas suas operações passadas e define exatamente quantos dólares alocar no trade (ex: $20.00 USDT).", bullet_style),
        Paragraph("<b>Etapa 8: Envio da Ordem Dupla (OCO) para a Binance</b><br/>A compra a mercado é realizada e a ordem OCO de venda é colocada instantaneamente na Binance. Seu lucro e seu cinto de segurança ficam programados na corretora.", bullet_style),
        Paragraph("<b>Etapa 9: Acompanhamento e Notificação no Telegram</b><br/>Você recebe uma notificação clara e bonita no Telegram com o valor da compra, Take Profit e Stop Loss. Se o preço subir +1.5%, ele vende 50% no lucro e garante o restante no zero-a-zero!", bullet_style)
    ]

    for st in steps_data:
        story.append(st)
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 10))

    # ==========================================
    # 4. COMANDOS DO TELEGRAM PARA O INVESTIDOR
    # ==========================================
    story.append(Paragraph("4. Como Acompanhar Tudo Pelo Telegram", h1_style))
    story.append(Paragraph("Você pode controlar e consultar o seu robô direto do celular enviando comandos simples na conversa do Telegram:", body_style))

    cmd_data = [
        [Paragraph("Comando", table_cell_header), Paragraph("O que ele faz para você?", table_cell_header)],
        [Paragraph("<b>/status</b>", table_cell), Paragraph("Exibe qual moeda o robô está analisando, a tendência do mercado e o score de confluência.")],
        [Paragraph("<b>/noticias</b>", table_cell), Paragraph("Mostra a análise de sentimento da IA Gemini e as notícias mais recentes do mercado cripto.")],
        [Paragraph("<b>/ocos</b> ou <b>/ordens</b>", table_cell), Paragraph("Exibe todas as ordens abertas na Binance com o valor exato de TP (Lucro) e SL (Segurança).")],
        [Paragraph("<b>/saldo</b>", table_cell), Paragraph("Mostra o seu saldo em dólares (USDT), BNB e a alocação de banca calculada pelo Critério de Kelly.")],
        [Paragraph("<b>/top40</b>", table_cell), Paragraph("Exibe o ranking das 5 moedas mais fortes do mercado no momento.")],
        [Paragraph("<b>/lucro</b>", table_cell), Paragraph("Exibe o seu lucro líquido acumulado total e a taxa de vitória (%) das operações.")],
        [Paragraph("<b>/relatorio</b>", table_cell), Paragraph("Gera e envia no Telegram um relatório executivo em PDF completo com estatísticas da semana.")],
        [Paragraph("<b>/stop</b> ou <b>/cancel</b>", table_cell), Paragraph("Botão de emergência para pausar o robô de forma limpa e segura a qualquer momento.")]
    ]

    t_cmd = Table(cmd_data, colWidths=[120, 384])
    t_cmd.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_cmd)
    story.append(Spacer(1, 14))

    # ==========================================
    # 5. GUIA DE RISCO E BOAS PRÁTICAS
    # ==========================================
    story.append(Paragraph("5. Recomendações de Segurança e Gestão de Banca", h1_style))
    story.append(Paragraph("Para garantir uma experiência tranquila e lucrativa no longo prazo, siga as recomendações abaixo:", body_style))

    rec_list = [
        Paragraph("• <b>Alocação Inicial Recomendada</b>: Comece testando o robô com <b>$30.00 a $50.00 USDT</b>. Esse valor é ideal para permitir operações de $15.00 a $25.00 USDT por ordem com margem de sobra na Binance.", bullet_style),
        Paragraph("• <b>Deixe o Robô Trabalhar sem Ansiedade</b>: O mercado cripto oscila. O SpotBot Pro possui proteção contra pânico, muros de baleias e recompras no desconto (Smart DCA). Evite fechar ordens manualmente na Binance antes da hora.", bullet_style),
        Paragraph("• <b>Proteção Automática contra Sequências Ruins</b>: Se o robô tiver 2 Stop Losses em menos de 15 minutos, ele entra sozinho em pausa defensiva de 1 hora para esperar o mercado acalmar.", bullet_style),
        Paragraph("• <b>Chaves de API Seguras</b>: Suas chaves de API da Binance devem ter autorização apenas para leitura e negociação Spot. Nunca ative a opção de saque (*Withdrawal*) nas suas chaves!", bullet_style)
    ]
    for r in rec_list:
        story.append(r)

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=10))
    story.append(Paragraph("<b>SpotBot Pro v7.0</b> — Engenharia Quantitativa Institucional & Inteligência Artificial Generativa.", ParagraphStyle('FooterTag', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1, textColor=PRIMARY)))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"SUCCESS: PDF Executivo do Usuario gerado com sucesso em: {output_filename}")

if __name__ == "__main__":
    create_executive_pdf("docs/SpotBot_Pro_Guia_Executivo_do_Usuario.pdf")
    create_executive_pdf("docs/SpotBot_Pro_Documentacao_Tecnica.pdf")
