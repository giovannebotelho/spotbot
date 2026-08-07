# SpotBot Pro 🤖📈 — Institutional Quantitative AI Engine (v6.0)

[![Python Version](https://img.shields.io/badge/python-3.10%2B%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Binance Spot](https://img.shields.io/badge/Binance-Spot%20API-yellow.svg)](https://www.binance.com/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini%202.5--Flash-4285F4.svg)](https://aistudio.google.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Wall%20Street%20Quant%20v5.0-purple.svg)](https://github.com/giovannebotelho/spotbot-pro-hedgefund)

**SpotBot Pro v6.0** é um algoritmo de negociação quantitativa de nível institucional projetado com os pilares da microestrutura de mercado das grandes mesas de Wall Street (**Order Flow CVD Tape Reading, Cointegration Pair Trading, Correlation Lead-Lag Alpha, Smart Recovery DCA em Suportes de Fibonacci e Kelly Criterion Position Sizing**), integrado à **Inteligência Artificial Generativa do Google Gemini (SDK `google-genai`)**.

---

## 🏛️ Arquitetura Quantitativa v6.0

```mermaid
graph TD
    subgraph Quant_Engine_v6 ["🚀 SpotBot Pro v6.0 Architecture"]
        F5["📰 FASE 5 (v4.0): AI Panic News Scanner<br/>CryptoPanic + IA Gemini 2.5 Flash (Score 0-100)"] --> F1
        F1["🧪 FASE 1 (v5.0): Smart Recovery DCA & Flash Dump Protection<br/>Recompra em Suporte Fibonacci 61.8% e Override de PnL"] --> F2
        F2["⚡ FASE 2 (v5.0): Correlation Lead-Lag Alpha Engine<br/>Antecipação de impulso do BTC 1m em Altcoins (1.5x)"] --> F3
        F3["📊 FASE 3 (v5.0): Order Flow CVD Tape Reading<br/>Análise de agressão a mercado em 500 trades (Buys >= 60%)"] --> F4
        F4["🔒 FASE 4 (v6.0): Trailing Profit Lock (Market Sell)<br/>Trava de lucro aos 75% da meta TP com Market Sell"] --> KC
        KC["🏆 FASE 5 (v5.0): Kelly Criterion Position Sizing<br/>Dimensionamento ótimo (Half-Kelly) via estatísticas do SQLite"] --> OCO["🎯 Ordem OCO Enviada para a Binance (BRT Timezone)"]
    end
```

---

## 🚀 Armas Quantitativas da Versão v6.0

### 1. 🧪 Smart Recovery DCA em Suportes de Fibonacci
- **Proteção Contra Pavios**: Em *flash dumps* causados por liquidações de derivativos na Binance, o robô efetua uma única recompra de 50% no Suporte Institucional de Fibonacci (61.8% / 78.6%).
- **Recuperação de PM**: Puxa o Preço Médio ($PM$) para baixo e re-posiciona a ordem OCO com Take Profit em apenas **+0.8% acima do novo $PM$**, garantindo saída no lucro no primeiro repique!

### 2. ⚡ Correlation Lead-Lag Alpha Engine (Motor de Antecipação BTC/ETH)
- **Arbitragem Temporal**: Detecta quando o `BTCUSDT` sofre um surto de volume e preço ($\ge +0.25\%$ em 3m) no gráfico de 1 minuto.
- **Entrada Antecipada**: Entra na altcoin do Top 40 que ainda está em atraso estatístico (*Lag*) **antes** que o movimento se espalhe, alocando multiplicador **1.5x**.

### 3. 📊 Order Flow Cumulative Volume Delta (CVD Tape Reading)
- **Leitura de Agressão**: Analisa as últimas 500 negociações executadas a mercado (*Market Orders*) na Binance Spot.
- **Confirmador de Volume**: Dispara compras quando a agressão compradora atinge $\ge 60\%$ e **dobra o lote (2.0x)** se o delta acumulado ultrapassar **+$50.000 USDT**.

### 4. ⚖️ Cointegration Pair Trading & Statistical Arbitrage
- **Reversão à Média**: Monitora o Z-Score da razão de preço entre o ativo atual e o Bitcoin (`Price_Alt / Price_BTC`).
- **Desvio Estatístico**: Abre compras por arbitragem estatística quando o ativo estiver a $Z \le -2.0\sigma$ de desvio-padrão abaixo da média histórica.

### 5. 🏆 Kelly Criterion & Monte Carlo Position Sizing
- **Dimensionamento Matemático**: Substitui valores estáticos de ordem pela Fórmula do **Critério de Kelly** ($f^* = \frac{p \cdot b - q}{b}$), onde $p$ é a taxa de vitória real calculada a partir das operações salvas no banco SQLite.
- **Half-Kelly Safety**: Aplica 50% de $f^*$ para manter a banca totalmente imune ao risco de ruína.

### 6. 🔒 Trailing Profit Lock (Market Sell Direto)
- **Trava de Segurança (v6.0)**: Diferente do trailing clássico, a v6.0 aguarda o preço atingir 75% do alvo de Take Profit (TP Conservador 2~3%).
- **Liquidação a Mercado (v6.0)**: Ao atingir a trava e apresentar uma queda de 0.2% a partir do pico, o bot cancela a OCO e manda uma Market Sell para assegurar os lucros imediatos.

### 7. ⏱️ Sincronização Absoluta de Fuso Horário (BRT)
- **Horário de Brasília (v6.0)**: Todo o ciclo de operação, logs, inserções de banco de dados e relatórios (Diários e Telemetria em PDF) utilizam estritamente o fuso `America/Sao_Paulo`, prevenindo distorções de *roll-over* diário causadas pelo relógio UTC dos servidores na nuvem.

---


## 📱 Bot Telegram & Interface Web Dashboard

- 🖥️ **Dashboard Web Profissional (NiceGUI & Plotly)**:
  - Gráficos K-Line interativos em tempo real com suporte a múltiplos timeframes.
  - Ticker bar contínuo, cards de métricas em tempo real e botão de emergência **CANCEL (CTRL+C)**.
- 📱 **Comandos Telegram Interativos**:
  - `/status`: Exibe o ativo em foco, RSI, tendência e **Confluência MTF Score (4H+1H+15M)**.
  - `/noticias` ou `/sentimento`: Exibe a classificação de pânico e notícias via **IA Gemini 2.5 Flash**.
  - `/ocos` ou `/ordens`: Exibe os valores exatos de Take Profit, Stop Loss e posições ativas.
  - `/saldo`: Saldos USDT, BNB e cálculo do **Lote Máximo do Critério de Kelly**.
  - `/top20` ou `/scanner`: Varre o Rank de Força Relativa (RS vs BTC) dos 20 maiores criptoativos.
  - `/lucro` ou `/perf`: Lucro líquido acumulado e Win Rate acumulado do banco SQLite.
  - `/relatorio` ou `/pdf`: Gera e envia o **Relatório Executivo em PDF** no Telegram.

---

## ⚙️ Variáveis de Ambiente (`.env`)

Configure o arquivo `.env` na raiz do projeto:

```env
# --- Configuração do Ambiente ---
BOT_ENVIRONMENT=mainnet

# --- Chaves Binance (Spot API) ---
mainnet_api_key=SUA_CHAVE_API_BINANCE
mainnet_secret_key=SEU_SECRET_KEY_BINANCE

# --- Google Gemini IA ---
gemini_api=SUA_CHAVE_API_GEMINI

# --- Telegram Bot ---
bot_token=SEU_TOKEN_TELEGRAM_BOT
chat_id=SEU_CHAT_ID_TELEGRAM

# --- Dashboard Web NiceGUI ---
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=admin123
SECRET_KEY=spotbot_secured_key_8823
```

---

## 📂 Estrutura Modular do Repositório

```text
spotbot/
│
├── config/                  # Configurações centralizadas e resolução de variáveis .env
│   └── settings.py
├── core/                    # Núcleo quantitativo de trading v5.0
│   ├── engine.py            # Loop principal assíncrono, Telegram Bot & OCO Lifecycle
│   ├── decision.py          # SMC, Whale Walls, ATR, Lead-Lag Alpha, Stat-Arb & Kelly Sizing
│   ├── indicators.py        # MTF Matrix, Fibonacci Supports, CVD, Z-Score, ATR, RSI, MACD
│   ├── patterns.py          # Reconhecimento de padrões de velas (Candlesticks)
│   └── post_trade.py        # Processamento de ordens e estatísticas
├── services/                # Serviços e Integrações
│   ├── binance_client.py    # Cliente assíncrono Binance (Spot & Futures API)
│   ├── database.py          # Gerenciador de Banco de Dados SQLite
│   ├── gemini_ai.py         # Classificador de Sentimento e Pânico Noticioso via IA Gemini
│   ├── news_scanner.py      # Coletor de manchetes em tempo real (CryptoPanic API)
│   ├── pdf_generator.py     # Gerador de Relatório Semanal em PDF ReportLab
│   └── telegram_notifier.py # Notificador e manipulador Telegram
├── ui/                      # Interface Web NiceGUI
│   └── dashboard.py         # Terminal Web Institucional NiceGUI
├── scratch/                 # Scripts de Teste e Validação Quantitativa
│   ├── test_smart_recovery_dca.py
│   ├── test_lead_lag_alpha.py
│   ├── test_order_flow_cvd.py
│   ├── test_stat_arb_pairs.py
│   └── test_kelly_sizing.py
├── requirements.txt         # Dependências do projeto Python
└── run.py                   # Ponto de entrada unificado
```

---

## 🚀 Como Executar Localmente

```powershell
# 1. Clonar o repositório
git clone https://github.com/giovannebotelho/spotbot-pro-hedgefund.git
cd spotbot-pro-hedgefund

# 2. Ativar o ambiente virtual e instalar dependências
.\env_spotbot\Scripts\activate
pip install -r requirements.txt

# 3. Executar o Dashboard Web e Robô SpotBot Pro v6.0
python run.py --mode dashboard
```

Acesse a interface gráfica no navegador em **`http://localhost:8080`**.

---

## 📄 Licença

Este projeto está licenciado sob a licença [MIT](LICENSE).
