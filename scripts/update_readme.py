import re

with open('c:\\Py\\spotbot\\README.md', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'# SpotBot Pro 🤖📈 — Institutional Quantitative AI Engine \(v5\.0-WALL_STREET_QUANT\)', '# SpotBot Pro 🤖📈 — Institutional Quantitative AI Engine (v6.0)', content)
content = content.replace('**SpotBot Pro v5.0**', '**SpotBot Pro v6.0**')
content = content.replace('## 🏛️ Arquitetura Quantitativa v5.0 (Wall Street Edition)', '## 🏛️ Arquitetura Quantitativa v6.0')
content = content.replace('subgraph Quant_Engine_v5 ["🚀 SpotBot Pro v5.0 Wall Street Architecture"]', 'subgraph Quant_Engine_v6 ["🚀 SpotBot Pro v6.0 Architecture"]')
content = content.replace('## 🚀 Armas Quantitativas da Versão v5.0', '## 🚀 Armas Quantitativas da Versão v6.0')
content = content.replace('Robô SpotBot Pro v5.0', 'Robô SpotBot Pro v6.0')
content = content.replace('núcleo quantitativo de trading v5.0', 'núcleo quantitativo de trading v6.0')

mermaid_v6 = """        F5["📰 FASE 5 (v4.0): AI Panic News Scanner<br/>CryptoPanic + IA Gemini 2.5 Flash (Score 0-100)"] --> F1
        F1["🧪 FASE 1 (v5.0): Smart Recovery DCA & Flash Dump Protection<br/>Recompra em Suporte Fibonacci 61.8% e Override de PnL"] --> F2
        F2["⚡ FASE 2 (v5.0): Correlation Lead-Lag Alpha Engine<br/>Antecipação de impulso do BTC 1m em Altcoins (1.5x)"] --> F3
        F3["📊 FASE 3 (v5.0): Order Flow CVD Tape Reading<br/>Análise de agressão a mercado em 500 trades (Buys >= 60%)"] --> F4
        F4["🔒 FASE 4 (v6.0): Trailing Profit Lock (Market Sell)<br/>Trava de lucro aos 75% da meta TP com Market Sell"] --> KC
        KC["🏆 FASE 5 (v5.0): Kelly Criterion Position Sizing<br/>Dimensionamento ótimo (Half-Kelly) via estatísticas do SQLite"] --> OCO["🎯 Ordem OCO Enviada para a Binance (BRT Timezone)"]"""

content = re.sub(r'        F5\["📰 FASE 5 \(v4\.0\).*?OCO\["🎯 Ordem OCO Institucional Enviada para a Binance"\]', mermaid_v6, content, flags=re.DOTALL)

v6_features = """
### 6. 🔒 Trailing Profit Lock (Market Sell Direto)
- **Trava de Segurança (v6.0)**: Diferente do trailing clássico, a v6.0 aguarda o preço atingir 75% do alvo de Take Profit (TP Conservador 2~3%).
- **Liquidação a Mercado (v6.0)**: Ao atingir a trava e apresentar uma queda de 0.2% a partir do pico, o bot cancela a OCO e manda uma Market Sell para assegurar os lucros imediatos.

### 7. ⏱️ Sincronização Absoluta de Fuso Horário (BRT)
- **Horário de Brasília (v6.0)**: Todo o ciclo de operação, logs, inserções de banco de dados e relatórios (Diários e Telemetria em PDF) utilizam estritamente o fuso `America/Sao_Paulo`, prevenindo distorções de *roll-over* diário causadas pelo relógio UTC dos servidores na nuvem.

---
"""

content = content.replace('- **Half-Kelly Safety**: Aplica 50% de $f^*$ para manter a banca totalmente imune ao risco de ruína.\n\n---', 
                          '- **Half-Kelly Safety**: Aplica 50% de $f^*$ para manter a banca totalmente imune ao risco de ruína.\n' + v6_features)

with open('c:\\Py\\spotbot\\README.md', 'w', encoding='utf-8') as f:
    f.write(content)
