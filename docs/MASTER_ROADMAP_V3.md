# 🚀 SPOTBOT PRO v3.0-HEDGE_FUND — MASTER ROADMAP

Este documento registra permanentemente os planos de implementação para a evolução do **SpotBot Pro v3.0**, introduzindo 4 armas quantitativas de alta precisão inspiradas em fundos quantitativos (*Hedge Funds*).

---

## 📌 FASES DO MASTER ROADMAP v3.0

### 🟢 FASE A: Módulo de Futures Analytics (Funding Rate & Open Interest Squeeze Hunter)
- **Objetivo**: Escanear o *Funding Rate* e o *Open Interest* dos contratos futuros da Binance para identificar potenciais *Short Squeezes* explosivos.
- **Lógica Quantitativa**:
  - Se $Funding\ Rate < -0.01\%$ (maioria do mercado apostando na queda) + surto de $Open\ Interest$ + $SMC\ Sweep$, probabilidade de *Short Squeeze* $> 85\%$.
- **Arquivos Impactados**: `services/binance_client.py`, `core/indicators.py`, `core/decision.py`.

---

### 🔵 FASE B: Orderbook Imbalance Scanner (Profundidade de Livro & Muros de Baleia)
- **Objetivo**: Analisar o desequilíbrio entre ofertas de compra e venda (*Bid/Ask Imbalance*) nos 20 primeiros níveis do livro de ofertas.
- **Lógica Quantitativa**:
  - $Imbalance\ Ratio = \frac{\sum Qty_{Bids}}{\sum Qty_{Asks}}$.
  - Se $Imbalance\ Ratio \ge 2.0$, confirma suporte de baleias (*Buy Walls*) protegendo a entrada.
- **Arquivos Impactados**: `services/binance_client.py`, `core/indicators.py`, `core/decision.py`.

---

### 🟣 FASE C: Gestor Dinâmico de Juros Compostos (Snowball Compounding Engine)
- **Objetivo**: Reinvestir automaticamente os lucros acumulados recalculando a alocação dos slots de capital.
- **Lógica Quantitativa**:
  - $Capital_{Total} = Saldo_{Inicial} + \sum Lucro_{Líquido}$.
  - $Slot_{Value} = \max(10.0, \frac{Capital_{Total}}{Slots_{Ativos}})$.
- **Arquivos Impactados**: `core/decision.py`, `core/engine.py`, `services/database.py`.

---

### 🟡 FASE D: Relatório Semanal de Telemetria com PDF Automático no Telegram
- **Objetivo**: Gerar e enviar todo domingo à noite um relatório de performance executivo em PDF com o *Sharpe Ratio*, *Profit Factor*, *Win Rate* e histórico de curva de capital.
- **Lógica Quantitativa**:
  - $Sharpe\ Ratio = \frac{R_p - R_f}{\sigma_p}$.
  - $Profit\ Factor = \frac{\sum Lucros}{\sum Perdas}$.
- **Arquivos Impactados**: `services/database.py`, `services/telegram_notifier.py`, `core/engine.py`.
