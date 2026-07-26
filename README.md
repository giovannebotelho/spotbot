# SpotBot Pro 🤖📈 — Institutional Quantitative AI Engine

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Binance Spot](https://img.shields.io/badge/Binance-Spot%20API-yellow.svg)](https://www.binance.com/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini%202.5--Flash-4285F4.svg)](https://aistudio.google.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Quantitative%20AI%20SMC-purple.svg)](docs/MASTER_ROADMAP.md)

**SpotBot Pro** é um sistema de negociação quantitativa automatizada no mercado **Spot da Binance**, projetado com conceitos da finança quantitativa institucional (**Market Microstructure, Order Flow Imbalance, Smart Money Concepts - SMC**) e potencializado pela **Inteligência Artificial Generativa do Google Gemini (SDK `google-genai`)**.

---

## 🏛️ Arquitetura Quantitativa de Élite em 5 Fases

O SpotBot Pro opera alimentado por um **Motor Quantitativo Multicamada em 5 Fases**:

```text
 🟢 FASE 1: Motor de Detecção de Regimes de Mercado (Hurst Exponent & Regime Switcher)
    ↓
 🔵 FASE 2: Caçador de Varredura de Liquidez (Smart Money Liquidity Sweeps - SMC)
    ↓
 🟣 FASE 3: Scanner 2.0 com Ranker de Força Relativa (Relative Strength vs BTC)
    ↓
 🟡 FASE 4: IA Gemini Score Quantitativo (Pontuação 0-100 & Dobrar Posição em Ouro 2x)
    ↓
 🔴 FASE 5: Gestor de Saídas Dinâmicas (Realização Parcial Scalp Locking 50% + Breakeven)
```

### 1. 🟢 Motor de Regimes de Mercado (Hurst Exponent)
- **Expoente de Hurst ($H$)**: Classifica continuamente a dinâmica da série temporal em Reversão à Média ($H < 0.48$), Tendência Persistente ($H > 0.55$) ou Movimento Aleatório.
- **Modo Defesa (Crash Panic)**: Detecta desvalorizações abruptas de mercado ($> 3.5\%$) e pausa compras normais automaticamente para proteger a banca.

### 2. 🔵 Caçador de Varreduras de Liquidez (Smart Money Concepts - SMC)
- Mapeia a mínima das últimas 24 horas (`low_24h`).
- Identifica quando os *market makers* espetam abaixo do suporte para capturar Stop Losses do varejo e o preço fecha com **vela de rejeição (pinbar/hammer)** + **pico de volume de compra ($V \ge 1.3\times$)**.
- Dispara entradas institucionais de alta taxa de vitória ($>75\%$).

### 3. 🟣 Scanner 2.0 com Ranker de Força Relativa (RS vs BTC)
- Calcula a Força Relativa ($RS\_Ratio = R_{Ativo} - R_{BTC}$) de 20 criptoativos da Binance.
- Aloca a banca nas moedas que lideram a alta do mercado no dia.

### 4. 🟡 IA Gemini Score Quantitativo (Pontuação 0 a 100)
- Avalia os dados de mercado e retorna um **Score de Confiança (0 a 100)**.
- **Score $\ge$ 80 (Oportunidade de Ouro)**: Dobra a mão da ordem (**2.0x**) para maximizar o lucro.
- **Score $< 50$**: Descarta a ordem para evitar armadilhas de mercado.

### 5. 🔴 Gestor de Saídas Dinâmicas (Scalp Locking + Breakeven)
- **Scalp Locking**: Ao atingir $+1.5\%$ de valorização, fecha automaticamente **50% da posição**, garantindo lucro no bolso.
- **Proteção Breakeven**: Move o Stop Loss dos 50% restantes para o **Zero a Zero (Preço de Entrada)**.
- **Trailing Stop ATR**: Conduz a metade restante para surfar o topo da tendência.

---

## ✨ Recursos de Destaque

- 🖥️ **Terminal Web Institucional (NiceGUI & ECharts)**:
  - Tema *Deep Obsidian* com gráficos em tempo real, indicadores sobrepostos (Bollinger, EMA 200, Volume) e Ticker contínuo estilo CoinMarketCap.
- 🎰 **Calculador de Slots Dinâmicos ($10 USDT Mínimo)**:
  - Fraciona o saldo garantindo estritamente o valor mínimo por ordem exigido pela Binance ($10.00 USDT).
- ⏱️ **Ressincronização Automática de Relógio (Anti-Drift -1021)**:
  - Sincroniza o relógio do sistema com o servidor atômico da Binance a cada 1 hora e trata exceções de offset sem parar o robô.
- 🏷️ **Desconto de 25% nas Taxas com BNB**:
  - Suporte nativo ao pagamento de comissões com BNB.
- 📱 **Bot Telegram Completo com Novos Comandos**:
  - `/status`: Estado atual, ativo em foco, RSI, tendência de 4h.
  - `/saldo`: Saldos USDT, BNB e cálculo de slots.
  - `/top20` ou `/scanner`: Top 5 oportunidades do Scanner 2.0 em tempo real.
  - `/lucro` ou `/perf`: Lucro acumulado, Win Rate e total de trades.

---

## 📊 Resultados em Simulação (Backtest de 90 Dias)

| Par | Timeframe | Perfil / Estratégia | Saldo Inicial | Saldo Final | Win Rate | Lucro Líquido |
|---|---|---|---|---|---|---|
| **SOLUSDT** | 15m (Scalp) | Multi-Asset SMC + Quant | $100.00 | **$103.66** | **60.0%** | **+3.66%** |
| **BTCUSDT** | 1h (Swing) | Trend Following | $100.00 | **$102.80** | **66.7%** | **+2.80%** |

---

## 📂 Estrutura Modular do Repositório

```text
spotbot/
│
├── config/                  # Configurações centralizadas e leitura do .env
│   └── settings.py
├── core/                    # Núcleo quantitativo de trading
│   ├── engine.py            # Loop assíncrono principal & resync Binance
│   ├── decision.py          # Decisão de compra/venda, SMC, OCO e Trailing Stop
│   ├── indicators.py        # Hurst Exponent, RS vs BTC, RSI, ADX, MACD, Bollinger, VWAP, ATR
│   ├── patterns.py          # Reconhecimento de 17 padrões de velas (Candlesticks)
│   └── post_trade.py        # Processamento de ordens e relatórios
├── services/                # Integrações externas
│   ├── binance_client.py    # Cliente assíncrono da Binance API
│   ├── database.py          # Banco de Dados Híbrido (SQLite / PostgreSQL)
│   ├── gemini_ai.py         # Conector oficial google-genai (Gemini 2.5-Flash Score 0-100)
│   └── telegram_notifier.py # Notificações e Bot Telegram
├── ui/                      # Interface Web Gráfica
│   └── dashboard.py         # Terminal Web Institucional NiceGUI
├── backtest/                # Ferramentas de simulação
│   ├── runner.py            # Motor de Backtest
│   └── optimizer.py         # Otimizador Grid Search
├── docs/                    # Documentação Mestre
│   ├── MASTER_ROADMAP.md    # Roteiro Quantitativo em 5 Fases
│   └── RAILWAY_DEPLOY_TUTORIAL.md
├── requirements.txt         # Dependências do projeto
└── run.py                   # Ponto de entrada unificado
```

---

## 🚀 Como Rodar o Robô

### 1. Clonar o Repositório e Configurar o Ambiente

```powershell
git clone https://github.com/giovannebotelho/spotbot.git
cd spotbot
python -m venv env_spotbot
.\env_spotbot\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar as Variáveis de Ambiente (.env)

Crie o arquivo `.env` na raiz do projeto:

```ini
mainnet_api_key=SUA_BINANCE_API_KEY
mainnet_secret_key=SUA_BINANCE_SECRET_KEY

bot_token=SEU_TELEGRAM_BOT_TOKEN
chat_id=SEU_TELEGRAM_CHAT_ID

gemini=SUA_GEMINI_API_KEY
PORT=8080
```

### 3. Iniciar o Terminal Web e o Bot

```powershell
python run.py --mode dashboard
```

Acesse a interface no navegador em **`http://localhost:8080`**.

---

## 📄 Licença

Este projeto está licenciado sob a licença [MIT](LICENSE).
