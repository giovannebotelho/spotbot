# ☁️ GUIA DE INFRAESTRUTURA & DEPLOY: SPOTBOT PRO v5.0 (LOCAL & NUVEM)

Este guia documenta como rodar o **SpotBot Pro v5.0 (Wall Street Edition)** com 100% de estabilidade e baixa latência, tanto **localmente no seu computador (recomendado)** quanto na **nuvem 24/7 (Railway / Render / VPS)**.

---

## 💻 Opção 1: Execução Local (Recomendado para Testes & Operações de Baixa Latência)

Rodar localmente no seu computador garante **latência mínima com os servidores da Binance**, zero custo de infraestrutura e controle total do banco de dados SQLite.

### 🛠️ Passo a Passo (Windows / Linux / macOS):

1. **Clonar o Repositório**:
   ```powershell
   git clone https://github.com/giovannebotelho/spotbot-pro-hedgefund.git
   cd spotbot-pro-hedgefund
   ```

2. **Criar e Ativar o Ambiente Virtual**:
   ```powershell
   python -m venv env_spotbot
   .\env_spotbot\Scripts\activate
   ```

3. **Instalar as Dependências**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configurar o Arquivo `.env`**:
   Crie ou edite o arquivo `.env` na raiz do projeto:
   ```env
   BOT_ENVIRONMENT=mainnet
   mainnet_api_key=SUA_CHAVE_API_BINANCE
   mainnet_secret_key=SEU_SECRET_KEY_BINANCE
   gemini_api=SUA_CHAVE_API_GEMINI
   bot_token=SEU_TOKEN_TELEGRAM_BOT
   chat_id=SEU_CHAT_ID_TELEGRAM
   DASHBOARD_USER=admin
   DASHBOARD_PASSWORD=admin123
   SECRET_KEY=spotbot_secured_key_8823
   ```

5. **Iniciar o Robô e Dashboard Web**:
   ```powershell
   python run.py --mode dashboard
   ```
   Acesse a interface gráfica no navegador em: **`http://localhost:8080`**.

---

## ☁️ Opção 2: Deploy 24/7 na Nuvem (Railway / Render / VPS)

Para colocar o robô operando 24h por dia, 7 dias por semana na nuvem:

### 📋 Passos no Railway.app:

1. **Conectar Repositório GitHub**:
   - Acesse o [Railway Dashboard](https://railway.app/dashboard) e clique em **+ New Project** $\rightarrow$ **Deploy from GitHub repo**.
   - Selecione o repositório `spotbot-pro-hedgefund`.

2. **Adicionar Variáveis de Ambiente**:
   Na aba **Variables** do projeto no Railway, adicione:
   - `mainnet_api_key`
   - `mainnet_secret_key`
   - `gemini_api`
   - `bot_token`
   - `chat_id`
   - `DASHBOARD_USER`
   - `DASHBOARD_PASSWORD`
   - `PORT=8080`

3. **Gerar URL Pública para o Dashboard**:
   - Vá para **Settings** $\rightarrow$ **Public Networking** $\rightarrow$ **Generate Domain**.
   - Acesse o link gerado (ex: `https://spotbot-production.up.railway.app`) pelo celular ou PC!

---

## 🛡️ Resiliência & Healthchecks de Infraestrutura

- **Sincronização de Relógio Binance**: O robô executa a função `sync_binance_time` na inicialização para compensar qualquer variação de latência e eliminar o erro `-1021 Timestamp ahead/behind`.
- **Persistência de Dados**: O banco SQLite (`spotbot.db`) salva todas as operações atomicamente. Em restarts, a função `monitor_oco_lifecycle` recupera posições abertas na Binance sem perdas.
- **Botão de Emergência CANCEL**: Se for necessário interromper o robô remotamente, envie o comando **`/stop`**, **`/cancel`** ou clique no botão **CANCEL (CTRL+C)** do Dashboard.
