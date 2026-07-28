# 📖 DOCUMENTAÇÃO TÉCNICA DE ARQUITETURA E ENGENHARIA DE SOFTWARE
## SPOTBOT PRO v5.0.0-WALL_STREET_QUANT — SISTEMA INSTITUCIONAL DE TRADING ALGORÍTMICO QUANTITATIVO E INTELIGÊNCIA ARTIFICIAL

---

### 📋 SUMÁRIO EXECUTIVO
- **Nome do Sistema**: SpotBot Pro (Wall Street Quantitative Engine)
- **Versão de Software**: `v5.0.0-WALL_STREET_QUANT`
- **Classificação de Confiabilidade**: *Critical Fault-Tolerant System (Medical-Grade Standard ISO/IEC 25010)*
- **Arquitetura**: Multi-threaded Async I/O (Python `asyncio`), Event-Driven WebSockets & Neural AI Synthesis
- **Exchange Suportada**: Binance Spot & Binance Futures (API REST v3/v1 & WebSocket User/Market Streams)
- **Modelos Quantitativos Integrados**:
  - Kelly Criterion & Monte Carlo Position Sizing ($f^*$)
  - Cointegration Pair Trading & Statistical Arbitrage ($Z\text{-Score} \le -2.0\sigma$)
  - Order Flow Cumulative Volume Delta (CVD Tape Reading em 500 Trades)
  - Correlation Lead-Lag Alpha Engine (BTC 1m Momentum Lead)
  - Smart Recovery DCA em Suportes de Fibonacci (61.8% e 78.6%)
  - AI Sentiment & Market Panic Scanner (CryptoPanic + Gemini 2.5 Flash)
  - Multi-Timeframe Confluence Matrix (4H + 1H + 15M $\ge 70\%$)
  - Orderbook 50 Depth & Whale Wall Protection
  - Dynamic ATR Volatility SL/TP Protection

---

# CAPÍTULO 1: FILOSOFIA QUANTITATIVA E CASCATA DE VALIDAÇÃO v5.0

O **SpotBot Pro v5.0** opera sob o conceito de **Filtros Quantitativos Hierárquicos v5.0** (Cascata de Validação em 9 Camadas), onde cada sinal deve passar por todos os filtros de proteção antes da execução na Binance:

```text
[Dados de Mercado em Tempo Real (WebSockets & REST Spot/Futures)]
                       │
                       ▼
  [Camada 0: AI Panic News Scanner (CryptoPanic + Gemini IA)]
                       │ (Trava compras se Sentiment Score < 30)
                       ▼
  [Camada 1: Matriz Multi-Timeframe (4H + 1H + 15M)]
                       │ (Exige Confluência Score >= 70%)
                       ▼
  [Camada 2: Lead-Lag Alpha Engine (BTC 1m Lead Momentum)]
                       │ (Antecipa impulso de volume do BTC em altcoins)
                       ▼
  [Camada 3: Order Flow CVD Tape Reading (500 Market Trades)]
                       │ (Confirma agressão compradora >= 60% e CVD > 0)
                       ▼
  [Camada 4: Cointegration Stat-Arb Z-Score (Spread vs BTC)]
                       │ (Captura reversão à média quando Z <= -2.0 sigma)
                       ▼
  [Camada 5: Whale Wall Protection (Livro 50 Depth)]
                       │ (Recua TP em 0.15% antes de muros de venda >= $25k)
                       ▼
  [Camada 6: Dynamic ATR Volatility SL/TP Protection]
                       │ (Ajusta Stop Loss entre -1.2% e -3.0% por ATR)
                       ▼
  [Camada 7: Kelly Criterion Position Sizing Engine]
                       │ (Dimensiona lote ótimo Half-Kelly com base no SQLite)
                       ▼
  [Camada 8: Ordem OCO, Smart Recovery DCA em Fibonacci 61.8% & Telegram]
```

---

# CAPÍTULO 2: EQUAÇÕES MATEMÁTICAS E MODELOS QUANTITATIVOS

## 2.1 Critério de Kelly & Dimensionamento por Probabilidade (Kelly Position Sizing)
Em vez de lotes intuitivos, a alocação ótima $f^*$ de capital por operação é calculada matematicamente via **Fórmula do Critério de Kelly**:

$$f^* = \frac{p \cdot b - (1 - p)}{b}$$

Onde:
- $p$: Taxa de Vitória real (*Win Rate*) extraída do banco de dados SQLite (`db.get_stats()`).
- $b$: Payoff Ratio da estratégia ($b = \frac{\text{Take Profit \%}}{\text{Stop Loss \%}} \approx 2.0$).
- **Half-Kelly Safety**: Para eliminar qualquer risco de ruína, o robô aplica a fração defensiva:
  $$\text{Kelly}_{\text{Lote}} = \text{Saldo}_{\text{USDT}} \times \max\left(0.10, \min\left(0.40, 0.5 \cdot f^*\right)\right)$$

---

## 2.2 Cointegração e Arbitragem Estatística de Pares (Pair Trading Z-Score)
Para dois ativos cointegrados $A$ e $B$ (ex: `SOLUSDT` vs `BTCUSDT`), a razão de preço instantânea é definida como $R_t = \frac{P_{A, t}}{P_{B, t}}$.

O **Z-Score** do spread em relação à média móvel $\mu_R$ e desvio-padrão $\sigma_R$ dos últimos 50 períodos é dado por:

$$Z_t = \frac{R_t - \mu_R}{\sigma_R}$$

- **Condição de Entrada**: Se $Z_t \le -2.0\sigma$, o Ativo $A$ está estatisticamente subavaliado em relação ao Ativo $B$. O algoritmo autoriza a compra por **Reversão à Média (Mean Reversion)**.

---

## 2.3 Order Flow Cumulative Volume Delta (CVD Tape Reading)
Mede a agressão das ordens executadas a mercado (*Market Orders*) nas últimas 500 transações spot:

$$\text{CVD} = \sum V_{\text{Market Buy}} - \sum V_{\text{Market Sell}}$$

$$\text{Buy Ratio \%} = \frac{\sum V_{\text{Market Buy}}}{\sum V_{\text{Market Buy}} + \sum V_{\text{Market Sell}}} \times 100$$

- **Gatilho Bullish**: Ativado se $\text{Buy Ratio \%} \ge 60.0\%$ e $\text{CVD} > 0$.
- **Multiplicador de Ouro (2.0x)**: Ativado se $\text{CVD} \ge +\$50.000\text{ USDT}$.

---

## 2.4 Correlation Lead-Lag Alpha Engine (Impulso BTC 1m)
Avalia a variação percentual de preço e volume do `BTCUSDT` nas velas de 1 minuto:

$$\Delta P_{\text{BTC}} = \frac{P_{\text{BTC, t}} - P_{\text{BTC, t-3}}}{P_{\text{BTC, t-3}}} \times 100$$

- **Sinal de Antecipação**: Se $\Delta P_{\text{BTC}} \ge +0.25\%$ em 3m com volume $1.5\times$ acima da média e a altcoin do Top 20 ainda não acompanhou ($\Delta P_{\text{Alt}} \le 0.7 \times \Delta P_{\text{BTC}}$), entra comprado antecipadamente na altcoin com multiplicador **1.5x**.

---

## 2.5 Smart Recovery DCA em Suportes de Fibonacci
Identifica a oscilação recente de preço ($\text{Swing High}$ e $\text{Swing Low}$) nas últimas 50 velas de 15m:

$$\text{Diff} = \text{Swing High} - \text{Swing Low}$$

$$\text{Fib}_{61.8\%} = \text{Swing High} - (\text{Diff} \times 0.618)$$

$$\text{Fib}_{786\%} = \text{Swing High} - (\text{Diff} \times 0.786)$$

- **Execução do DCA**: Se a altcoin sofrer um *flash dump* de pavio atingindo $\text{Fib}_{61.8\%}$, executa recompra de 50%, recalcula o Preço Médio ($PM = \frac{q_1 p_1 + q_2 p_2}{q_1 + q_2}$) e re-posiciona a ordem OCO com Take Profit em apenas **$+0.8\%$ acima do novo $PM$**.

---

# CAPÍTULO 3: ESTRUTURA MODULAR DO CÓDIGO

```text
spotbot/
│
├── config/                  # Configurações centralizadas e leitura do .env
│   └── settings.py          # API_KEYS, TELEGRAM_CONFIG, TRADING_CONFIG, RSI_CONFIG, TOP_20_SYMBOLS.
│
├── core/                    # Núcleo de Engenharia Quantitativa v5.0
│   ├── engine.py            # Loop principal assíncrono, Telegram Bot, OCO Lifecycle & Smart Recovery DCA.
│   ├── decision.py          # Decision engine: MTF, Whale Walls, ATR, Lead-Lag, Stat-Arb, CVD & Kelly Sizing.
│   ├── indicators.py        # Algoritmos quantitativos: MTF Score, Fibonacci, CVD, Z-Score, ATR, RSI, MACD.
│   ├── patterns.py          # Reconhecimento de padrões de velas de alta precisão.
│   └── post_trade.py        # Processamento de ordens OCO, taxas BNB e registro de dados.
│
├── services/                # Conectores e Serviços de Dados
│   ├── binance_client.py    # Cliente assíncrono Binance (Spot & Futures API, Klines 3-Timeframe, Trades 500).
│   ├── database.py          # Gerenciador de Banco de Dados SQLite transacional.
│   ├── gemini_ai.py         # Classificador de Sentimento e Pânico Noticioso via IA Gemini 2.5 Flash.
│   ├── news_scanner.py      # Coletor de manchetes de notícias em tempo real (CryptoPanic API).
│   ├── pdf_generator.py     # Gerador de Relatório Semanal de Telemetria em PDF ReportLab.
│   └── telegram_notifier.py # Conector assíncrono Telegram Bot API.
│
├── ui/                      # Interface Web NiceGUI
│   └── dashboard.py         # Terminal Web Institucional NiceGUI, gráficos Plotly e cards holográficos.
│
├── scratch/                 # Scripts de Testes Quantitativos
│   ├── test_smart_recovery_dca.py
│   ├── test_lead_lag_alpha.py
│   ├── test_order_flow_cvd.py
│   ├── test_stat_arb_pairs.py
│   └── test_kelly_sizing.py
│
└── run.py                   # Ponto de entrada unificado com CLI argparse (--mode dashboard).
```

---

# CAPÍTULO 4: PROCEDIMENTOS DE OPERAÇÃO E INSTALAÇÃO

1. **Ativação do Ambiente Virtual**:
   ```powershell
   .\env_spotbot\Scripts\activate
   ```
2. **Instalação de Dependências**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Execução do Robô com Interface Web**:
   ```powershell
   python run.py --mode dashboard
   ```
4. **Navegador**: `http://localhost:8080`
