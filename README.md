# SpotBot Pro 🤖📈

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Binance Spot](https://img.shields.io/badge/Binance-Spot%20API-yellow.svg)](https://www.binance.com/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini%202.5--Flash-4285F4.svg)](https://aistudio.google.com/)

**SpotBot Pro** é um assistente quantitativo de negociação automatizada no mercado **Spot da Binance**, combinando **Análise Técnica Avançada** (RSI, ADX, MACD, Bandas de Bollinger, VWAP, EMAs 7-200, Padrões de Candlestick, ATR) com a **Inteligência Artificial Generativa do Google Gemini (SDK `google-genai`)**, controlado por um **Terminal Web Institucional (NiceGUI & ECharts)** e notificações no **Telegram**.

---

## ✨ Funcionalidades Principais

- 🖥️ **Terminal Web Institucional (NiceGUI & ECharts)**:
  - Tema *Deep Obsidian* com gráfico interativo de velas (candlesticks), volume e médias móveis.
  - Ticker contínuo no topo estilo CoinMarketCap / DexScreener.
  - Card holográfico da IA Gemini com justificativas técnicas em tempo real.
  - Seletor de Perfis de Risco (**Conservador**, **Moderado**, **Agressivo**).
  - Chave de **Paper Trading (Simulador de Mercado)**.
- 🧠 **Validação por IA Generativa (Google Gemini 2.5-Flash)**:
  - Análise contextual de velas, livro de ofertas, médias e volume.
  - Tratamento inteligente de cotas com pausa de segurança sem interromper operações técnicas.
- 📈 **Filtros Técnicos Robustos**:
  - **ADX (Average Directional Index)**: Filtro anti-armadilha para evitar compras em mercados lateralizados.
  - **RSI Dinâmico & VWAP**: Entradas cirúrgicas em sobrevenda extrema.
  - **Padrões de Velas**: Detecção de Hammer, Engolfo, Doji, Shooting Star, Kicker e outros 12 padrões.
- 🛡️ **Gerenciamento de Risco Integrado**:
  - Ordens OCO (Lucro Alvo + Stop Loss).
  - Stop Loss por Volatilidade (**ATR**).
  - Trailing Stop Móvel automatizado.
- 📱 **Bot Telegram Integrado**:
  - Alertas automáticos de inicialização, compras, vendas, lucros e stops.
  - Comandos interativos (`/status`, `/saldo`, `/stop`, `/ajuda`).
- 💾 **Persistência de Dados**:
  - Suporte nativo a `SQLite` local (`spotbot.db`) e `PostgreSQL` para deploy em nuvem.

---

## 📂 Estrutura Modular do Repositório

```text
spotbot/
│
├── config/                  # Configurações centralizadas e leitura do .env
│   └── settings.py
├── core/                    # Núcleo quantitativo de trading
│   ├── engine.py            # Loop assíncrono principal
│   ├── decision.py          # Decisão de compra/venda, OCO e Trailing Stop
│   ├── indicators.py        # Cálculos de RSI, ADX, MACD, Bollinger, VWAP, ATR, EMAs
│   ├── patterns.py          # Reconhecimento de 17 padrões de velas (Candlesticks)
│   └── post_trade.py        # Processamento e logs pós-operação
├── services/                # Integrações externas
│   ├── binance_client.py    # Cliente assíncrono da Binance API
│   ├── database.py          # Gerenciador de Banco de Dados Híbrido (SQLite / PostgreSQL)
│   ├── gemini_ai.py         # Conector oficial google-genai (Gemini 2.5-Flash)
│   └── telegram_notifier.py # Notificações e Bot Telegram
├── ui/                      # Interface Web Grafica
│   └── dashboard.py         # Terminal Web Institucional NiceGUI
├── backtest/                # Ferramentas de simulação
│   ├── runner.py            # Motor de Backtest
│   └── optimizer.py         # Otimizador Grid Search
├── utils/                   # Utilitários de texto e ANSI
│   └── formatting.py
├── docs/                    # Guias e tutoriais
│   ├── DOCUMENTATION.md
│   └── RAILWAY_DEPLOY_TUTORIAL.md
├── Dockerfile               # Containerização para deploy em nuvem
├── Procfile                 # Process Manager
├── .env.example             # Modelo seguro de variáveis de ambiente
├── requirements.txt         # Dependências do projeto
└── run.py                   # Ponto de entrada unificado
```

---

## 🚀 Como Rodar o Robô

### 1. Clonar o Repositório e Criar o Ambiente Virtual

No Windows PowerShell:
```powershell
git clone https://github.com/giovannebotelho/spotbot.git
cd spotbot
python -m venv env_spotbot
.\env_spotbot\Scripts\activate
```

No Linux / macOS:
```bash
git clone https://github.com/giovannebotelho/spotbot.git
cd spotbot
python3 -m venv env_spotbot
source env_spotbot/bin/activate
```

### 2. Instalar as Dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar as Variáveis de Ambiente (`.env`)
Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

Abra o arquivo `.env` e preencha suas chaves:
```env
# Binance API (Chaves Spot)
mainnet_api_key=SUA_BINANCE_API_KEY
mainnet_secret_key=SEU_BINANCE_SECRET_KEY

# Google Gemini API Key (Obtenha em aistudio.google.com/app/apikey)
gemini_api=SUA_GEMINI_API_KEY

# Telegram Bot (Obtenha com o @BotFather)
bot_token=SEU_TELEGRAM_BOT_TOKEN
chat_id=SEU_TELEGRAM_CHAT_ID

# Credenciais de Acesso ao Dashboard Web
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=admin123
```

### 4. Iniciar a Aplicação

- **Modo Terminal Web Dashboard (Recomendado)**:
  ```bash
  python run.py --mode dashboard
  ```
  Acesse no navegador: `http://localhost:8080`

- **Modo Terminal CLI (Puro)**:
  ```bash
  python run.py --mode cli
  ```

- **Modo Simulação / Backtest**:
  ```bash
  python run.py --mode backtest --days 30
  ```

---

## 🔒 Licença e Segurança

- **Chaves de API**: NUNCA envie seu arquivo `.env` ou chaves reais para o GitHub. O repositório vem com `.gitignore` configurado.
- **Permissões Binance**: Ao criar sua API Key na Binance, desative permissões de **Saque** e **Transferência**, deixando ativas apenas **Leitura** e **Trading Spot**.

---

## 📜 Licença
Este projeto está sob a licença MIT. Sinta-se livre para colaborar e usar.
