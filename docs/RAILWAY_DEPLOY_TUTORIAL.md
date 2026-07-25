# ☁️ Tutorial Passo a Passo: Deploy 24/7 do SpotBot Pro no Railway

Este guia ensina como colocar o seu **SpotBot Pro** rodando 24 horas por dia, 7 dias por semana na nuvem usando a plataforma **Railway**, com banco de dados **PostgreSQL** e sem precisar deixar o seu computador ligado.

---

## 📋 Pré-requisitos

1. Uma conta no [Railway.app](https://railway.app) (pode fazer login direto com seu GitHub).
2. Seu repositório `spotbot` no GitHub (pode ser privado ou público).
3. Suas chaves da Binance (`mainnet_api_key` e `mainnet_secret_key`) e do Gemini (`gemini_api`).

---

## 🛠️ Passo 1: Criar o Projeto no Railway

1. Acesse o painel do [Railway](https://railway.app/dashboard).
2. Clique no botão **+ New Project**.
3. Selecione a opção **Deploy from GitHub repo**.
4. Procure e escolha o seu repositório `spotbot`.

---

## 🐘 Passo 2: Adicionar o Banco de Dados PostgreSQL

1. No canvas do seu projeto no Railway, clique em **+ New** (ou aperte `Ctrl + K` e digite *Database*).
2. Escolha a opção **Add PostgreSQL**.
3. O Railway criará uma instância de PostgreSQL em instantes.
4. **Pronto!** O Railway irá injetar automaticamente a variável `DATABASE_URL` no seu bot. O SpotBot Pro detectará o PostgreSQL de forma 100% automática!

---

## 🔑 Passo 3: Configurar as Variáveis de Ambiente (Environment Variables)

1. Clique no card do seu serviço `spotbot` no Railway.
2. Acesse a aba **Variables**.
3. Clique em **Raw Editor** (ou adicione uma a uma) e cole suas configurações:

```env
# Binance API (Chaves reais da sua conta)
mainnet_api_key=SUA_CHAVE_REAL_BINANCE
mainnet_secret_key=SEU_SECRET_REAL_BINANCE

# Google Gemini API Key
gemini_api=SUA_CHAVE_GEMINI_API

# Telegram Config (Para receber notificações no celular)
bot_token=SEU_BOT_TOKEN_TELEGRAM
chat_id=SEU_CHAT_ID_TELEGRAM

# Autenticação do Dashboard Web NiceGUI
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=sua_senha_segura
DASHBOARD_SECRET_KEY=spotbot_secret_railway_2026

# Ambiente (mainnet / testnet)
BOT_ENVIRONMENT=mainnet
```

4. Clique em **Save Changes**.

---

## 🌐 Passo 4: Gerar a URL Pública para Acessar o Dashboard

1. Ainda nas configurações do seu serviço `spotbot` no Railway, vá para a aba **Settings**.
2. Na seção **Networking**, procure por **Public Networking** e clique em **Generate Domain**.
3. O Railway criará um link público seguro (ex: `https://spotbot-production.up.railway.app`).
4. Clique no link gerado e faça login com seu `DASHBOARD_USER` e `DASHBOARD_PASSWORD`!

---

## 🎉 Pronto! O seu Robô está Operando 24/7

- O Railway lerá automaticamente o `Dockerfile` e o `Procfile` incluídos no repositório.
- Seu robô funcionará initerruptamente na nuvem.
- Se o servidor reiniciar ou houver atualização, ele religará sozinho.
- Você pode acompanhar o gráfico e os logs em tempo real pelo navegador do seu PC ou celular a qualquer hora!
