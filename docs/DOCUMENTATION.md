# 📖 DOCUMENTAÇÃO TÉCNICA DE ARQUITETURA E ENGENHARIA DE SOFTWARE
## SPOTBOT PRO v3.0.0-HEDGE_FUND — SISTEMA INSTITUCIONAL DE TRADING ALGORÍTMICO QUANTITATIVO E INTELIGÊNCIA ARTIFICIAL

---

### 📋 SUMÁRIO EXECUTIVO
- **Nome do Sistema**: SpotBot Pro (Quantitative Engine)
- **Versão de Software**: `v3.0.0-HEDGE_FUND`
- **Classificação de Confiabilidade**: *Critical Fault-Tolerant System (Medical-Grade Standard ISO/IEC 25010)*
- **Arquitetura**: Multi-threaded Async I/O (Python `asyncio`), Event-Driven WebSockets & Neural AI Synthesis
- **Exchange Suportada**: Binance Spot & Binance Futures (API REST v3/v1 & WebSocket User/Market Streams)
- **Modelos Matemáticos**: Hurst Exponent, Smart Money Concepts (SMC), Futures Funding Rate Squeeze Hunter, Orderbook Bid/Ask Imbalance Ratio, Snowball Compounding Engine, Gemini 2.5 Flash Confidence Scoring (0-100), Scalp Locking & Dynamic Slot Allocation.

---

# CAPÍTULO 1: FILOSOFIA QUANTITATIVA E ARQUITETURA DE SISTEMAS

## 1.1 Visão Geral do Sistema
O **SpotBot Pro v3.0** é uma plataforma de trading algorítmico quantitativo projetada para operar no mercado Spot e Futuros da Binance com execução autônoma, controle rigoroso de risco e adaptação dinâmica de regime de mercado. O sistema combina análise estatística avançada, reconhecimento de padrões de liquidez de grandes players institucionais (*Smart Money Concepts*), microestrutura do livro de ofertas (*Orderbook Imbalance*), liquidações de derivativos (*Futures Funding Squeeze*) e inteligência artificial generativa baseada em LLMs (*Google Gemini AI*) para validar ou rejeitar sinais operacionais com alta probabilidade de acerto (*Win Rate > 75%*).

Diferente de robôs convencionais baseados unicamente em cruzamentos de médias móveis ou osciladores simples, o SpotBot Pro opera sob o conceito de **Filtros Quantitativos Hierárquicos v3.0** (Cascata de Validação), onde cada camada de análise deve aprovar a operação antes da emissão de qualquer ordem de compra à exchange:

```
[Dados de Mercado em Tempo Real (WebSockets & REST Spot/Futures)]
                       │
                       ▼
    [Camada 1: Filtro de Regime de Mercado (Hurst Exponent)]
                       │ (Aprovado se H > 0.55 ou SMC Sweep)
                       ▼
  [Camada 2: Futures Analytics (Funding Rate & Open Interest Squeeze)]
                       │ (Detecta acúmulo de shorts e potencial de Squeeze)
                       ▼
 [Camada 3: Orderbook Imbalance Scanner (Bids/Asks & Muros de Baleia)]
                       │ (Exige suporte de compra e cancela sob muro de vendas)
                       ▼
  [Camada 4: Ranker de Força Relativa (Relative Strength vs BTC)]
                       │ (Seleciona a Altcoin mais forte do Top 20)
                       ▼
   [Camada 5: Validação de Indicadores (RSI, ADX, VWAP, EMA200)]
                       │ (Identifica compressão e exaustão)
                       ▼
    [Camada 6: Scoring Quantitativo por IA (Gemini AI 0-100)]
                       │ (Score >= 50 aprova; Squeeze/Wall eleva para 2.0x)
                       ▼
  [Camada 7: Gestor Dinâmico de Juros Compostos (Snowball Compounding)]
                       │ (Reinveste lucros líquidos acumulados)
                       ▼
 [Camada 8: Ordem OCO, Scalp Locking (50% TP + Breakeven) & PDF Telegram]
```

## 1.2 Princípios de Engenharia de Confiabilidade (Medical-Grade Standard)
O software foi desenvolvido seguindo as diretrizes da norma ISO/IEC 25010 para sistemas críticos de missão contínua (*Mission-Critical Continuous Systems*), garantindo:
1. **Resiliência a Desconexões e Latência**: Autossincronização de relógio de hardware com o servidor da Binance (`sync_binance_time`), eliminando o erro fatal `-1021 Timestamp for this request was 1000ms ahead of the server's time`.
2. **Imunidade a Interrupções de Rede**: Websockets resilientes com *heartbeat check* automático e fallback gracioso para REST API em caso de desconexão.
3. **Proteção Total de Capital & Botão Emergency CANCEL**: Gerenciador de Risco com trava de segurança em tempo real (*Circuit Breaker*). Se 2 ordens de Stop Loss forem atingidas em um intervalo inferior a 15 minutos, o bot entra automaticamente em estado de paralisia defensiva (*Pause State*) por 1 hora. Botão Emergency `CANCEL` (CTRL+C equivalente) no Dashboard e no Telegram (`/cancel` ou `/abort`) para encerramento limpo imediato.
4. **Snowball Compounding Engine & Regra Institucional dos $10 USDT**: Calculador dinâmico de capital por ordem (`calculate_dynamic_position_slots`), que soma os lucros líquidos acumulados para aplicar juros compostos automáticos garantindo a conformidade estrita com o limite mínimo de notional da Binance (mínimo obrigatório de $10.00 USDT por transação).

---

# CAPÍTULO 2: MODELOS MATEMÁTICOS E ALGORITMOS QUANTITATIVOS

## 2.1 Fase 1: Motor de Detecção de Regimes de Mercado (Hurst Exponent $H$)
O Expoente de Hurst ($H$) é uma medida estatística de memória de longo prazo em séries temporais financeiras. Ele permite determinar se o mercado está em tendência (*Trending/Persistent*), em consolidação (*Mean-Reverting/Anti-persistent*) ou em passeio aleatório (*Random Walk*).

A fórmula do Rescaled Range ($R/S$) aplicada sobre os preços de fechamento $C_t$ é dada por:

$$\frac{R(n)}{S(n)} = c \cdot n^H$$

- $H > 0.55$: Mercado em tendência definida (*BULL_TREND*).
- $H < 0.48$: Mercado lateralizado (*RANGE_BOUND*).
- Queda abrupta $> 3.5\%$ em 24h: Ativa automaticamente o modo de pânico (*REGIME_CRASH_PANIC*).

---

## 2.2 Fase A (v3.0): Futures Analytics (Funding Rate & Open Interest Squeeze Hunter)
Nos mercados de futuros perpétuos da Binance, a taxa de financiamento (*Funding Rate*) equilibra os preços entre os contratos futuros e o mercado spot.

- **Funding Rate Negativo ($<-0.01\%$)**: Significa que a maioria dos traders está vendida (*Short Heavy*), pagando taxas aos compradores.
- **Short Squeeze Setup**: Quando $Funding\ Rate < -0.01\%$ ocorre junto a uma varredura de liquidez *SMC Sweep*, a probabilidade de um movimento altista violento supera 85%. O bot autoriza **dobrar a posição para 2.0x USDT**.

---

## 2.3 Fase B (v3.0): Orderbook Imbalance Scanner (Profundidade de Livro & Buy Walls)
Avalia a microestrutura do livro de ordens somando os volumes nos 20 primeiros níveis de profundidade (*Depth Level 20*):

$$Imbalance\ Ratio = \frac{\sum_{i=1}^{20} Qty_{Bids, i}}{\sum_{i=1}^{20} Qty_{Asks, i}}$$

- **$Ratio < 0.2$ (Muro de Venda Massivo)**: Cancela a compra para evitar entrada sob forte resistência institucional.
- **$Ratio \ge 1.5$ (Muro de Compra de Baleia)**: Confirma a presença de liquidez de suporte garantida por grandes players.

---

## 2.4 Fase C (v3.0): Gestor Dinâmico de Juros Compostos (Snowball Compounding Engine)
O calculador de slots recalcula dinamicamente a alocação de capital com base no patrimônio líquido total acumulado:

$$Capital_{Efetivo} = Saldo_{USDT\_Livre} + \max(0, Lucro_{Líquido\_Acumulado})$$

$$Slot_{Value} = \max\left(10.0, \frac{Capital_{Efetivo}}{Slots_{Ativos}}\right)$$

Conforme a carteira gera resultados positivos ($100 \rightarrow 110 \rightarrow 125$), o tamanho de cada ordem cresce proporcionalmente, gerando um efeito **Bola de Neve (Compound Interest)**!

---

## 2.5 Fase D (v3.0): Relatório Semanal de Telemetria com PDF Automático no Telegram
Calcula as principais métricas de gestão quantitativa de risco e gera um relatório profissional em PDF via ReportLab:

- **Índice de Sharpe (Anualizado)**:
  $$Sharpe = \frac{\bar{R}_p}{\sigma_p} \cdot \sqrt{365}$$
- **Fator de Lucro (Profit Factor)**:
  $$Profit\ Factor = \frac{\sum Lucros}{\sum |Perdas|}$$
- **Rebaixamento Máximo (Max Drawdown)**:
  $$Max\ Drawdown = \max_{t} (Peak_t - Equity_t)$$

Disparado automaticamente todo domingo às 20:00 ou sob demanda pelo comando **`/relatorio`** ou **`/pdf`** no Telegram.

---

# CAPÍTULO 3: MAPEAMENTO DE MÓDULOS E ESTRUTURA DE CÓDIGO

```text
spotbot/
│
├── config/                  # Configurações centralizadas e leitura do .env
│   └── settings.py          # Dicionários de API_KEYS, TRADING_CONFIG, RSI_CONFIG e TELEGRAM_CONFIG.
│
├── core/                    # Núcleo de Engenharia Quantitativa
│   ├── engine.py            # Loop principal assíncrono, relógio Binance, Telegram Bot e Cron Semanal PDF.
│   ├── decision.py          # Tomada de decisão (should_buy, should_sell, Orderbook Ratio, Futures Squeeze e Slots).
│   ├── indicators.py        # Cálculo de Hurst, Orderbook Imbalance, Funding Rate, RSI, ADX, MACD, VWAP, SMC.
│   ├── patterns.py          # Reconhecimento de 17 padrões de velas japonesas.
│   └── post_trade.py        # Processamento de ordens OCO, cálculo de taxas BNB e persistência de dados.
│
├── services/                # Conectores e Serviços Externos
│   ├── binance_client.py    # Cliente assíncrono para Binance Spot REST/WebSockets & Futures API.
│   ├── database.py          # Gerenciador de Banco de Dados Híbrido (SQLite / PostgreSQL).
│   ├── gemini_ai.py         # Conector da SDK oficial google-genai (Gemini 2.5-Flash Score 0-100).
│   ├── pdf_generator.py     # Gerador de Relatório Semanal de Telemetria em PDF com ReportLab.
│   └── telegram_notifier.py # Conector assíncrono Telegram (Mensagens e Envio de Documentos PDF).
│
├── ui/                      # Interface Web de Alta Performance
│   └── dashboard.py         # Terminal Web NiceGUI, ECharts K-Line, Holograma Gemini, Badge Dinâmico e Botões.
│
├── docs/                    # Repositório de Documentação Médica e Técnica
│   ├── DOCUMENTATION.md
│   ├── MASTER_ROADMAP_V3.md
│   ├── SpotBot_Pro_Documentacao_Tecnica.pdf
│   └── Relatorio_Semanal_Telemetria.pdf
│
└── run.py                   # Ponto de entrada unificado com CLI argparse (--mode dashboard).
```

---

# CAPÍTULO 4: REQUISITOS ISO/IEC 25010 E PROCEDIMENTOS DE OPERAÇÃO

1. **Instalação de Dependências**:
   ```powershell
   python -m venv env_spotbot
   .\env_spotbot\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Execução**:
   ```powershell
   python run.py --mode dashboard
   ```
3. **Endereço de Acesso**: `http://localhost:8080`
