# SpotBot Pro 🤖📈 — Institutional Quantitative AI Engine (v3.0-HEDGE_FUND)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Binance Spot](https://img.shields.io/badge/Binance-Spot%20API-yellow.svg)](https://www.binance.com/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini%202.5--Flash-4285F4.svg)](https://aistudio.google.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Hedge%20Fund%20v3.0-purple.svg)](docs/MASTER_ROADMAP_V3.md)
[![Documentation PDF](https://img.shields.io/badge/Documentation-17%20Pages%20PDF-red.svg)](docs/SpotBot_Pro_Documentacao_Tecnica.pdf)

**SpotBot Pro v3.0** é um sistema de negociação quantitativa de nível institucional no mercado **Spot e Futuros da Binance**, projetado com microestrutura de mercado (**Market Microstructure, Orderbook Imbalance, Futures Funding Squeeze, Smart Money Concepts - SMC**) e potencializado pela **Inteligência Artificial Generativa do Google Gemini (SDK `google-genai`)**.

---

## 🏛️ Arquitetura Quantitativa de Élite v3.0 (Hedge Fund Edition)

O SpotBot Pro opera alimentado por um **Motor Quantitativo Multicamada v3.0**:

```text
  🟢 FASE 1: Motor de Regimes de Mercado (Hurst Exponent & Regime Switcher)
     ↓
  🔵 FASE 2: Caçador de Varredura de Liquidez (Smart Money Liquidity Sweeps - SMC)
     ↓
  📊 FASE A (v3.0): Futures Analytics (Funding Rate & Open Interest Squeeze Hunter)
     ↓
  📖 FASE B (v3.0): Orderbook Imbalance Scanner (Profundidade de Livro & Muros de Baleias)
     ↓
  🟣 FASE 3: Scanner 2.0 com Ranker de Força Relativa (Relative Strength vs BTC)
     ↓
  🟡 FASE 4: IA Gemini Score Quantitativo (Pontuação 0-100 & Dobrar Posição em Ouro 2x)
     ↓
  ❄️ FASE C (v3.0): Gestor Dinâmico de Juros Compostos (Snowball Compounding Engine)
     ↓
  🔴 FASE 5: Gestor de Saídas Dinâmicas (Realização Parcial Scalp Locking 50% + Breakeven)
     ↓
  📊 FASE D (v3.0): Relatório Semanal de Telemetria com PDF Automático no Telegram
```

---

## 🚀 Novas Armas Quantitativas da Versão v3.0

### 1. 📊 Futures Analytics (Funding Rate & Open Interest Squeeze Hunter)
- **Detecção de Short Squeeze**: Escanear em tempo real o *Funding Rate* ($<-0.01\%$) e *Open Interest* nos Futuros Perpétuos da Binance.
- **Dobra de Posição**: Quando o mercado futuro está supersaturado de *Shorts* e ocorre um *SMC Liquidity Sweep*, o robô autoriza **dobrar a posição para 2.0x USDT**.

### 2. 📖 Orderbook Imbalance Scanner (Muros de Baleias no Livro)
- **Análise de Profundidade**: Soma o volume nos 20 primeiros níveis de ofertas ($Ratio = \frac{\sum Qty_{Bids}}{\sum Qty_{Asks}}$).
- **Proteção Anti-Armadilha**: Cancela a compra se houver muro de vendas opressivo ($Ratio < 0.2$).
- **Suporte Institucional**: Confirma *Buy Walls* de suporte de grandes players ($Ratio \ge 1.5$).

### 3. ❄️ Gestor Dinâmico de Juros Compostos (Snowball Compounding Engine)
- Reinveste automaticamente os lucros líquidos acumulados do banco SQLite.
- O calculador de slots expande dinamicamente a alocação de capital por ordem de forma exponencial (*Compound Interest*).

### 4. 📊 Relatório Semanal em PDF no Telegram
- Calcula o **Sharpe Ratio (Anualizado)**, **Profit Factor**, **Win Rate** e **Max Drawdown**.
- Disparo automático todo domingo às 20:00 ou sob demanda enviando **`/relatorio`** ou **`/pdf`** no Telegram.

---

## ✨ Recursos da Interface e Comandos Telegram

- 🖥️ **Terminal Web Institucional (NiceGUI & ECharts)**:
  - Gráfico K-Line em tempo real com Badge Dinâmico do Ativo Ativo, painel holográfico da IA Gemini e Ticker Bar contínuo responsivo.
  - Botão de Emergência **CANCEL (CTRL+C)** para parada imediata de segurança.
- 📱 **Bot Telegram Completo**:
  - `/status`: Estado atual, ativo em foco, RSI e tendência.
  - `/saldo`: Saldos USDT, BNB e slots com Juros Compostos.
  - `/top20` ou `/scanner`: Top 5 oportunidades de Força Relativa.
  - `/lucro` ou `/perf`: Lucro líquido total e Win Rate.
  - `/relatorio` ou `/pdf`: Envia o PDF de Telemetria Executiva.
  - `/cancel` ou `/abort`: Interrupção imediata de emergência.

---

## 📚 Documentação Técnica de Nível Dispositivos Médicos

Consulte a documentação completa e formal de arquitetura do projeto:
- 📄 **Manual Técnico Completo (PDF 17 Páginas)**: [docs/SpotBot_Pro_Documentacao_Tecnica.pdf](docs/SpotBot_Pro_Documentacao_Tecnica.pdf)
- 📝 **Documentação de Código e Módulos (Markdown)**: [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)
- 🎯 **Plano Mestre v3.0**: [docs/MASTER_ROADMAP_V3.md](docs/MASTER_ROADMAP_V3.md)

---

## 📂 Estrutura Modular do Repositório

```text
spotbot/
│
├── config/                  # Configurações centralizadas e leitura do .env
│   └── settings.py
├── core/                    # Núcleo quantitativo de trading
│   ├── engine.py            # Loop principal assíncrono & Telegram Bot
│   ├── decision.py          # Decisão SMC, Orderbook Imbalance, Futures Squeeze e Slots
│   ├── indicators.py        # Hurst Exponent, Orderbook Ratio, Funding Rate, RSI, ADX, MACD
│   ├── patterns.py          # Reconhecimento de 17 padrões de velas (Candlesticks)
│   └── post_trade.py        # Processamento de ordens e estatísticas
├── services/                # Integrações externas
│   ├── binance_client.py    # Cliente assíncrono Binance (Spot & Futures API)
│   ├── database.py          # Banco de Dados Híbrido (SQLite / PostgreSQL)
│   ├── gemini_ai.py         # Conector oficial google-genai (Gemini 2.5-Flash)
│   ├── pdf_generator.py     # Gerador de Relatório Semanal em PDF ReportLab
│   └── telegram_notifier.py # Envio de mensagens e PDFs via Telegram
├── ui/                      # Interface Web Gráfica
│   └── dashboard.py         # Terminal Web Institucional NiceGUI
├── docs/                    # Manuais e Documentação Médica ISO/IEC 25010
│   ├── DOCUMENTATION.md
│   ├── MASTER_ROADMAP_V3.md
│   ├── SpotBot_Pro_Documentacao_Tecnica.pdf
│   └── Relatorio_Semanal_Telemetria.pdf
├── requirements.txt         # Dependências do projeto
└── run.py                   # Ponto de entrada unificado
```

---

## 🚀 Como Rodar o Robô

```powershell
# 1. Clonar o repositório
git clone https://github.com/giovannebotelho/spotbot.git
cd spotbot

# 2. Ativar o ambiente virtual e instalar dependências
.\env_spotbot\Scripts\activate
pip install -r requirements.txt

# 3. Executar o Terminal Web e Robô SpotBot Pro
python run.py --mode dashboard
```

Acesse a interface no navegador em **`http://localhost:8080`**.

---

## 📄 Licença

Este projeto está licenciado sob a licença [MIT](LICENSE).
