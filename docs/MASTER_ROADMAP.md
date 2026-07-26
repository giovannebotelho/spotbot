# 🏛️ Plano Diretor Mestre: Arquitetura Quantitativa de Élite (SpotBot Pro)

Este documento registra o **Roteiro Mestre em 5 Fases** para a evolução do **SpotBot Pro** em um sistema de inteligência quantitativa institucional.

---

## 🧭 Roteiro Mestre de Implementação em 5 Fases

```text
 🟢 FASE 1: Motor de Detecção de Regimes de Mercado (Hurst Exponent & Regime Switcher)
    ↓
 🔵 FASE 2: Caçador de Varredura de Liquidez (Smart Money Liquidity Sweeps - SMC)
    ↓
 🟣 FASE 3: Scanner 2.0 com Ranker de Força Relativa (Relative Strength vs BTC)
    ↓
 🟡 FASE 4: IA Gemini Score Quantitativo (Pontuação de Confiança 0 a 100)
    ↓
 🔴 FASE 5: Gestor de Saídas Dinâmicas (Realização Parcial Scalp Locking + Breakeven)
```

---

## 📋 Resumo Detalhado por Fase

### 🔹 FASE 1: Motor de Detecção de Regimes de Mercado (Market Regime Switcher)
- **Cálculo de Hurst Exponent ($H$)**:
  - $H > 0.55$: Regime Tendencial de Alta (`REGIME_BULL_TREND`) -> Ativa Breakout & Trend Following.
  - $H < 0.45$: Regime de Reversão à Média (`REGIME_RANGE_BOUND`) -> Ativa Reversão por RSI/Bollinger.
  - Queda $> 3.5\%$ em 4h: Regime de Pânico (`REGIME_CRASH_PANIC`) -> Pausa compras convencionais.

### 🔹 FASE 2: Caçador de Varreduras de Liquidez (Smart Money Concepts - SMC)
- Mapeia mínima de 24h (`low_24h`).
- Detecta quando o preço espeta abaixo da mínima e fecha acima com vela de rejeição (pinbar) + volume $> 1.8\times$.
- Envia sinal de COMPRA INSTITUCIONAL com Win Rate $> 75\%$.

### 🔹 FASE 3: Scanner 2.0 com Ranker de Força Relativa (Relative Strength vs BTC)
- Calcula a Força Relativa ($RS\_Ratio = \text{Retorno 24h Ativo} / \text{Retorno 24h BTC}$).
- Aloca a banca nas moedas com maior força relativa acumulada do dia.

### 🔹 FASE 4: IA Gemini Score Quantitativo (Pontuação 0 a 100)
- **Score 80 a 100**: Aloca **2 Slots (Dobra a mão)**.
- **Score 50 a 79**: Aloca **1 Slot Normal**.
- **Score < 50**: Descarta a ordem.

### 🔹 FASE 5: Gestor de Saídas Dinâmicas (Realização Parcial Scalp Locking + Breakeven)
- Ao atingir **+1.5% de lucro**, executa venda parcial de **50% da posição**.
- Move o Stop Loss do restante para o **Zero a Zero (Breakeven)**.
- Conduz os 50% restantes com Trailing Stop por ATR.
