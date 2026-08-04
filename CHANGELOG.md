# Changelog
Todos os registros de evolução da arquitetura do **SpotBot Pro** estão listados aqui.

## [v6.0]
### Added
- **Trailing Profit Lock (Market Sell):** Nova trava de lucros ao atingir 75% da meta TP, garantindo o fechamento imediato via Market Sell na menor queda, sem risco de expiração da OCO.
- **Sincronização BRT (America/Sao_Paulo):** Padronização integral de todo o relógio lógico da aplicação, logs, banco de dados e relatórios diários em PDF para o horário de Brasília, evitando falhas de virada do dia via horário UTC no Railway.
- **DCA PnL Override:** Lógica que corrige o cálculo de PnL Bruto para englobar de forma correta o capital inserido durante repiques (Smart Recovery DCA).

### Changed
- **Metas Conservadoras (TP/SL):** Parametrização ajustada para TP alvo de 2.0% a 3.0% e SL protetivo de 1.5% a 2.0% garantindo a eficiência de capital a curto prazo.
- Correção no dashboard para re-renderizar baseando-se no maior ID do banco SQLite em vez da quantidade bruta de registros, destravando a contagem.

---

## [v5.0]
### Added
- **Smart Recovery DCA & Flash Dump Protection:** Motor de recompra dinâmica em retrações em níveis institucionais de Suporte Fibonacci (61.8%).
- **Correlation Lead-Lag Alpha Engine:** Algoritmo que rastreia os surtos do BTC (>= 0.25% em 3m) para disparar antecipações nas Altcoins do Top 20.
- **Order Flow CVD Tape Reading:** Leitura contínua dos últimos 500 ticks de mercado, verificando desbalanceamento de `maker` vs `taker` buys >= 60%.
- **Kelly Criterion Position Sizing:** Gestão de lotes com modelo "Half-Kelly" utilizando as taxas de vitória históricas extraídas do SQLite.
- **Cointegration Pair Trading:** Reversão à média através do Z-Score em comparação ao Bitcoin.
