# SpotBot Pro 🤖📈

**SpotBot Pro** é um assistente de trading automatizado para o mercado **Spot da Binance**, combinando **Análise Técnica quantitativa** (RSI, MACD, Bandas de Bollinger, VWAP, EMAs, Padrões de Candlestick, ATR) com a **Inteligência Artificial Generativa do Google Gemini / Gemma** e controle total via **Dashboard Web (NiceGUI)** e **Notificações bidirecionais no Telegram**.

---

## ✨ Funcionalidades Principais

- 🖥️ **Dashboard Web Interativo (NiceGUI)**: Interface moderna em tempo real na porta `8080` com gráfico ECharts, saldo de USDT/BNB, controle de start/stop e exibição dos raciocínios da IA.
- 🧠 **Validação por IA (Google GenAI)**: Suporte aos modelos de última geração (`gemini-2.5-flash`, `gemini-2.0-flash`, `gemma-3-27b-it`) para confirmação de sinais e filtragem de armadilhas de mercado.
- 📱 **Bot Telegram Bidirecional**: Recebe alertas automáticos de ordens/lucros e responde a comandos (`/status`, `/saldo`, `/stop`, `/ajuda`).
- 🛡️ **Gerenciamento de Risco Inteligente**: Ordens OCO (Lucro Alvo + Stop Loss), Stop baseado em Volatilidade (ATR) e Trailing Stop móvel automatizado.
- 💾 **Persistência Híbrida de Dados**: Suporte nativo a `SQLite` (`spotbot.db`) para desenvolvimento local e `PostgreSQL` para deploy 24/7 na nuvem.
- 🧪 **Simulador & Otimizador**: Ferramentas integradas para Backtest e Grid Search de parâmetros técnicos.

---

## 📂 Estrutura Modular do Projeto

```text
spotbot/
│
├── config/             # Configurações centralizadas e variáveis .env
│   └── settings.py
├── core/               # Motor de trading e indicadores técnicos
│   ├── engine.py       # Loop assíncrono principal
│   ├── decision.py     # Lógica de decisão de compra/venda, OCO e Trailing Stop
│   ├── indicators.py   # Cálculos quânticos (RSI, MACD, Bollinger, VWAP, ATR)
│   ├── patterns.py     # Reconhecimento de padrões de velas (Candlesticks)
│   └── post_trade.py   # Tratamento de resultados pós-operação
├── services/           # Integrações externas
│   ├── binance_client.py # Cliente Binance API
│   ├── database.py     # Gerenciador de Banco de Dados Híbrido (SQLite / PostgreSQL)
│   ├── gemini_ai.py    # Conector oficial com a SDK google-genai
│   └── telegram_notifier.py # Notificações e Bot Telegram
├── ui/                 # Interface Gráfica Web
│   └── dashboard.py    # Painel NiceGUI
├── backtest/           # Ferramentas de simulação
│   └── runner.py       # Motor de Backtest
├── utils/              # Formatação e utilitários
│   └── formatting.py
├── Dockerfile          # Container para deploy no Railway / Docker
├── Procfile            # Gerenciador de processos do Railway
├── .env.example        # Modelo de variáveis de ambiente
└── run.py              # Ponto de entrada unificado da aplicação
```

---

## 🚀 Como Rodar Localmente

### 1. Criar o Ambiente Virtual
No Windows PowerShell:
```powershell
python -m venv env_spotbot
.\env_spotbot\Scripts\activate
```

No Linux / macOS:
```bash
python3 -m venv env_spotbot
source env_spotbot/bin/activate
```

### 2. Instalar as Dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar as Variáveis de Ambiente (`.env`)
Copie o arquivo `.env.example` para `.env` e preencha suas chaves:
```bash
cp .env.example .env
```

### 4. Executar a Aplicação

- **Modo Dashboard Web (Recomendado)**:
  ```bash
  python run.py --mode dashboard
  ```
  Acesse no seu navegador: `http://localhost:8080` (Credenciais padrão: `admin` / `admin123`).

- **Modo Terminal CLI (Puro)**:
  ```bash
  python run.py --mode cli
  ```

- **Modo Simulação (Backtest)**:
  ```bash
  python run.py --mode backtest --days 30
  ```

---

## ☁️ Deploy 24/7 no Railway (Nuvem)

O SpotBot Pro vem 100% preparado para ser implantado no **Railway**:

1. Crie um novo projeto no [Railway.app](https://railway.app).
2. Conecte seu repositório privado ou público do GitHub.
3. Adicione um plugin de **PostgreSQL** no Railway (ele fornecerá a variável `DATABASE_URL` automaticamente).
4. Em **Variables** do projeto no Railway, adicione suas chaves do `.env`:
   - `mainnet_api_key`
   - `mainnet_secret_key`
   - `gemini_api`
   - `bot_token`
   - `chat_id`
   - `DASHBOARD_USER`
   - `DASHBOARD_PASSWORD`
   - `DASHBOARD_SECRET_KEY`
5. O Railway usará o `Dockerfile` / `Procfile` automaticamente para manter seu robô rodando 24 horas por dia sem gastar energia do seu computador!

---

## 🔒 Licença e Segurança

- Nunca suba o seu arquivo `.env` ou o arquivo `spotbot.db` para o GitHub.
- Certifique-se de restringir a permissão das suas API Keys da Binance apenas para **Leitura** e **Trading Spot** (Desative permissões de Saque/Transferência).
