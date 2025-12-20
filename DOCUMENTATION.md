# Documentação do Projeto: SpotBot Pro 🤖📈

## 1. Visão Geral
O **SpotBot Pro** é um assistente automatizado de negociação (robô de trading) desenvolvido para operar no mercado de criptomoedas da Binance. Seu objetivo principal é identificar oportunidades de compra e venda de ativos (como Bitcoin) de forma autônoma, buscando lucro e protegendo o capital investido.

Diferente de robôs simples, o SpotBot Pro utiliza uma abordagem **híbrida**: ele combina matemática financeira (indicadores técnicos) com a "intuição" de uma Inteligência Artificial avançada (Google Gemini).

## 2. Como o Robô Pensa? 🧠

O processo de decisão do robô segue três etapas principais:

### Passo 1: O Filtro Matemático (Indicadores Técnicos)
O robô monitora o mercado 24 horas por dia. Ele usa indicadores clássicos para filtrar o "ruído" e encontrar momentos interessantes. O principal indicador é o **RSI (Índice de Força Relativa)**.
*   **O que ele busca?** Momentos em que o preço caiu demais e muito rápido (o mercado está "sobrevendido"). Isso geralmente indica uma chance de recuperação (rebote).
*   **Configuração Atual**: O robô é conservador. Ele só olha para oportunidades quando o RSI está muito baixo (abaixo de 30), o que aumenta a segurança.

### Passo 2: A Validação da IA (Google Gemini)
Quando o filtro matemático encontra uma oportunidade, ele não compra imediatamente. Ele "chama" a Inteligência Artificial e envia uma foto do momento atual do mercado (preços, tendências, volume).
*   **A Pergunta**: "IA, com base nestes dados, isso é uma oportunidade real ou uma armadilha?"
*   **A Resposta**: A IA analisa o contexto e dá um veredito. Se ela aprovar, o robô segue para a compra.

### Passo 3: Proteção de Capital (Gerenciamento de Risco)
Assim que compra, o robô define imediatamente três preços de saída para se proteger:
1.  **Lucro Alvo (Take Profit)**: O preço onde ele venderá para garantir o lucro.
2.  **Limite de Perda (Stop Loss)**: O preço onde ele venderá para evitar prejuízos maiores caso o mercado caia.
3.  **Trailing Stop (Stop Móvel)**: Se o preço subir, o robô "sobe" o Limite de Perda junto. Assim, se o preço cair depois de subir, ele garante que você saia com algum lucro, em vez de devolver tudo.

## 3. Funcionalidades Principais 🛠️

### 🖥️ Dashboard de Controle
Uma interface web moderna (acessível pelo navegador) onde você pode:
*   Ver o saldo da sua carteira em tempo real (USDT e BNB).
*   Escolher qual moeda operar (ex: BTCUSDT, ETHUSDT).
*   Iniciar e Parar o robô com um clique.

*   Acompanhar logs detalhados do que o robô está fazendo.
*   **Visualização Limpa**: O Card de Insight da IA agora pode ser minimizado para liberar a visão do gráfico, garantindo que você não perca nenhum detalhe da ação do preço.

### 📱 Controle via Telegram
Você não precisa ficar na frente do computador. O robô envia mensagens para o seu celular:
*   **Notificações**: Avisa quando comprou, vendeu ou teve lucro.
*   **Comandos**: Você pode digitar `/saldo` para ver quanto dinheiro tem ou `/stop` para desligar o robô de onde estiver.

### 💾 Banco de Dados Seguro
Todas as operações são salvas em um banco de dados seguro (`SQLite`). Isso significa que mesmo se o computador desligar ou reiniciar, o histórico de suas operações não é perdido.

### 🧪 Simulador de Estratégia (Backtest)
Antes de arriscar dinheiro real, o sistema permite testar suas configurações com dados do passado. Você pode ver como o robô teria se comportado nos últimos meses para ajustar a estratégia.

## 4. Estrutura Técnica (Resumo)

*   **Linguagem**: Python (robusto e rápido).
*   **Interface**: NiceGUI (moderna e responsiva).
*   **Conexão**: API Oficial da Binance (segurança bancária).
*   **Inteligência**: Google Gemini 1.5 Flash (rápida e eficiente).

## 5. Conclusão
O SpotBot Pro é uma ferramenta poderosa que tira a emoção da negociação. Ele não se cansa, não sente medo e segue a estratégia à risca. Com a otimização recente, ele foi ajustado para ser **conservador**, priorizando a proteção do seu dinheiro em vez de fazer apostas arriscadas a todo momento.
