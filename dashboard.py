from nicegui import ui, app
import asyncio
import main
import sys
from datetime import datetime
from database import DatabaseManager

# Initialize DB
db = DatabaseManager()

# Global State
log_ui = None
status_ui = None
bot_task = None
stats_container = None
charts_container = None
recent_trades_table = None
candle_chart = None
ai_card = None
ai_icon_container = None
ai_signal_label = None
ai_reason_markdown = None

def log_handler(message):
    print(message)
    if log_ui:
        clean_msg = remove_ansi_codes(message)
        log_ui.push(clean_msg)

def status_handler(message):
    if status_ui:
        clean_msg = remove_ansi_codes(message)
        status_ui.content = f"**{clean_msg}**"

def remove_ansi_codes(text):
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

async def update_data():
    """Updates Balances, Stats, and Charts."""
    # 1. Balances
    balances = await main.get_account_balances()
    if balances:
        bnb_val.text = f"{balances['bnb']:.4f}"
        bnb_usdt_val.text = f"~${balances['bnb_usdt']:.2f}"
        usdt_val.text = f"${balances['usdt']:.2f}"
    
    # 2. Database Stats
    stats = db.get_stats()
    total_profit_val.text = f"${stats['total_net_profit']:.2f}"
    total_profit_val.classes(remove='text-green-400 text-red-400', add='text-emerald-400' if stats['total_net_profit'] >= 0 else 'text-rose-400')
    win_rate_val.text = f"{stats['win_rate']:.1f}%"
    
    # 3. Charts Data
    # Equity
    equity_data = db.get_equity_data() 
    if equity_data and equity_chart:
        dates = [d['time'] for d in equity_data]
        balances = [d['balance'] for d in equity_data]
        equity_chart.options['xAxis']['data'] = dates
        equity_chart.options['series'][0]['data'] = balances
        equity_chart.update()

    # Win/Loss
    if win_loss_chart:
        win_loss_chart.options['series'][0]['data'] = [
            {'value': stats['wins'], 'name': 'Win', 'itemStyle': {'color': '#10b981'}}, # emerald-500
            {'value': stats['losses'], 'name': 'Loss', 'itemStyle': {'color': '#f43f5e'}} # rose-500
        ]
        win_loss_chart.update()

    # 4. Market Chart Update (Price + Volume)
    market_data = main.shared_market_data
    
    if market_data['dates'] and candle_chart:
        # Common X Axis
        candle_chart.options['xAxis'][0]['data'] = market_data['dates'] # Price Axis
        candle_chart.options['xAxis'][1]['data'] = market_data['dates'] # Volume Axis
        
        # Series 0: Candle
        candle_chart.options['series'][0]['data'] = market_data['klines'] 
        
        # Series 1-3: Indicators
        candle_chart.options['series'][1]['data'] = market_data.get('bb_upper', [])
        candle_chart.options['series'][2]['data'] = market_data.get('bb_lower', [])
        candle_chart.options['series'][3]['data'] = market_data.get('ema200', [])
        
        # Series 4: Volume (New)
        candle_chart.options['series'][4]['data'] = market_data.get('volumes', [])
        
        candle_chart.update()

    # 5. Recent Trades (Table)
    update_recent_trades_table()
    
    # 6. Logs Scroll
    if log_ui:
        log_ui.run_method('scrollTo', 0, 999999) # Ensure scroll to bottom

    # 7. AI Insight Update
    insight = main.shared_market_data.get('gemini_insight')
    if insight and ai_signal_label and ai_reason_markdown:
        signal = insight.get('signal', 'N/A')
        ai_signal_label.text = f"SINAL: {signal}"
        
        # Color Logic
        if signal == 'COMPRA':
            ai_card.classes(remove='border-slate-700', add='border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.3)]')
            ai_signal_label.classes(remove='text-slate-400 text-rose-500 text-amber-500', add='text-emerald-400')
            ai_icon_container.classes(remove='bg-slate-700', add='bg-emerald-500/20')
        elif signal == 'VENDA':
            ai_card.classes(remove='border-slate-700 border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.3)]', add='border-slate-700') # Remove glow
            ai_signal_label.classes(remove='text-slate-400 text-emerald-400 text-amber-500', add='text-rose-500')
            ai_icon_container.classes(remove='bg-slate-700', add='bg-rose-500/20')
        else:
            ai_card.classes(remove='border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.3)]', add='border-slate-700')
            ai_signal_label.classes(remove='text-slate-400 text-emerald-400 text-rose-500', add='text-amber-500')
            ai_icon_container.classes(remove='bg-slate-700', add='bg-amber-500/20')
            
        ai_reason_markdown.content = insight.get('justification', '**Sem justificativa disponível.**')

def update_recent_trades_table():
    if not recent_trades_table:
        return

    trades_df = db.get_recent_trades(limit=10)
    
    if trades_df.empty:
        recent_trades_table.rows = []
        return

    if 'id' in trades_df.columns:
        trades_df = trades_df.sort_values('id', ascending=False)
    
    rows = []
    for _, row in trades_df.iterrows():
        is_profit = row.get('Resultado da Ordem OCO') == 'profit'
        pnl_val = row.get('Resultado da Ordem OCO')
        if not isinstance(pnl_val, (int, float)):
             pnl_val = row.get('Resultado Parcial da Transação Líquido', 0)
             
        pnl_str = f"${pnl_val:.2f}"
        
        rows.append({
            'date': str(row.get('Data/Hora da Compra', 'N/A')),
            'pair': str(row.get('Símbolo', 'N/A')),
            'type': 'OCO',
            'result': str(row.get('Resultado da Ordem OCO', '-')),
            'pnl': pnl_str,
            '_row_class': 'bg-emerald-900/20' if is_profit else 'bg-rose-900/20' if row.get('Resultado da Ordem OCO') == 'loss' else ''
        })
        
    recent_trades_table.rows = rows

async def start_bot():
    global bot_task
    if bot_task and not bot_task.done():
        ui.notify('Bot já está rodando!', type='warning')
        return

    investment = investment_input.value
    symbol = symbol_select.value
    
    if not investment:
        ui.notify('Por favor, defina o valor do investimento.', type='warning')
        return
    
    if not symbol:
        ui.notify('Por favor, selecione um par de moedas.', type='warning')
        return

    # Check minimum balance
    if hasattr(main, 'usdt_balance') and main.usdt_balance < 10:
        ui.notify('⚠ Saldo insuficiente para operar na Binance (Mínimo $10 USDT).', type='negative', close_button=True)
        return

    ui.notify('Iniciando Bot...')
    main.bot_running = True
    status_indicator.classes('bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.7)]') # Glowing green
    
    bot_task = asyncio.create_task(main.run_bot(log_callback=log_handler, investment_amount=investment, selected_symbol=symbol, status_callback=status_handler))
    
    try:
        await bot_task
    except asyncio.CancelledError:
        ui.notify('Bot parado pelo usuário.', type='info')
        status_indicator.classes('bg-red-500 shadow-none')
    except Exception as e:
        ui.notify(f'Erro no bot: {e}', type='negative')
        status_indicator.classes('bg-red-500 shadow-none')
        print(f"Erro crítico: {e}")

def update_timeframe(value):
    if main.bot_running:
        ui.notify(f"Alterando tempo gráfico para {value}...", type='info')
    # Update the config in main memory
    # Assuming main imports TRADING_CONFIG and we can modify it.
    # main.TRADING_CONFIG is a dict.
    if hasattr(main, 'TRADING_CONFIG'):
        main.TRADING_CONFIG['interval'] = value
        # Optional: Clear shared data to avoid mixing timeframes visually until new data arrives
        main.shared_market_data['klines'] = []
        main.shared_market_data['dates'] = []
    else:
        ui.notify("Erro: Não foi possível acessar a configuração.", type='negative')

def stop_bot():
    global bot_task
    if main.bot_running:
        main.bot_running = False
        if bot_task:
            bot_task.cancel()
        ui.notify('Sinal de parada enviado.', type='info')
        status_indicator.classes('bg-red-500 shadow-none')
    else:
        ui.notify('Bot não está rodando.', type='warning')

# --- UI Application ---
@ui.page('/')
async def index():
    global log_ui, status_ui, investment_input, symbol_select, bnb_val, bnb_usdt_val, usdt_val
    global total_profit_val, win_rate_val, equity_chart, win_loss_chart, recent_trades_table, status_indicator, candle_chart
    global ai_signal_label, ai_reason_markdown, ai_card, ai_icon_container
    
    # Theme Colors
    ui.colors(primary='#3b82f6', secondary='#64748b', accent='#f59e0b', positive='#10b981', negative='#f43f5e', dark='#0f172a')
    
    # Global Custom CSS
    ui.add_head_html('''
        <style>
            :root { --nicegui-default-padding: 0.5rem; }
            body { background-color: #020617; color: #f8fafc; font-family: 'Inter', system-ui, sans-serif; }
            
            /* Custom Scrollbar for "Terminal" feel */
            ::-webkit-scrollbar { width: 8px; height: 8px; }
            ::-webkit-scrollbar-track { background: #0f172a; }
            ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
            ::-webkit-scrollbar-thumb:hover { background: #475569; }
            
            /* Glassmorphism Utilities */
            .glass-panel {
                background: rgba(30, 41, 59, 0.7);
                backdrop-filter: blur(8px);
                border: 1px solid rgba(255, 255, 255, 0.05);
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }
            .nicegui-card { background: transparent; box-shadow: none; border: none; }
            
            /* Inputs */
            .q-field__native { color: #f1f5f9 !important; }
            .q-field__label { color: #94a3b8 !important; }
            
            /* Terminal Log */
            .terminal-box { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.8rem; background-color: #000; color: #4ade80; }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    ''')

    # --- Header (Sticky) ---
    with ui.header().classes('h-16 bg-slate-900/90 backdrop-blur border-b border-slate-800 flex items-center px-6 justify-between z-50'):
        # Branding
        with ui.row().classes('items-center gap-3'):
            with ui.element('div').classes('relative'):
                ui.icon('smart_toy', size='2em', color='blue-500')
                status_indicator = ui.element('div').classes('absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-red-500 border-2 border-slate-900 transition-all duration-300 shadow-[0_0_8px_rgba(239,68,68,0.6)]')
            
            with ui.column().classes('gap-0'):
                ui.label('SPOTBOT').classes('text-xl font-black tracking-tighter text-white leading-none')
                ui.label('PRO TERMINAL').classes('text-[0.65rem] font-bold text-blue-400 tracking-[0.2em] leading-none')

        # KPI Summary (Top Bar)
        with ui.row().classes('gap-6 hidden md:flex'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('account_balance_wallet', size='xs', color='slate-500')
                usdt_val = ui.label('$0.00').classes('font-mono font-bold text-lg text-white')
            with ui.row().classes('items-center gap-2'):
                ui.icon('local_gas_station', size='xs', color='slate-500')
                bnb_val = ui.label('0.0000').classes('font-mono font-bold text-sm text-amber-500')
                bnb_usdt_val = ui.label('~$0.00').classes('text-xs text-slate-500')

        # Actions
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='refresh', on_click=update_data).props('round flat color=slate-400 size=sm').tooltip('Atualizar Dados')
            ui.button(icon='settings', on_click=lambda: ui.notify('Configurações em breve')).props('round flat color=slate-400 size=sm')

    # --- Main Layout ---
    with ui.row().classes('w-full min-h-[calc(100vh-4rem)] p-4 gap-4 flex-nowrap items-start'):
        
        # --- LEFT SIDEBAR (Controls) ---
        with ui.column().classes('w-72 flex-shrink-0 gap-4'):
            
            # 1. Controls Card
            with ui.card().classes('glass-panel w-full p-4 flex flex-col gap-4 rounded-xl'):
                ui.label('COMANDO').classes('text-xs font-bold text-slate-500 tracking-wider mb-2')
                
                symbol_select = ui.select(
                    ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'XRPUSDT', 'DOTUSDT'],
                    label='Par de Negociação', value='BTCUSDT'
                ).props('outlined dense options-dense behavior="menu"').classes('w-full font-mono text-sm')
                
                investment_input = ui.input(
                    'Investimento (USDT/%)', value='100%'
                ).props('outlined dense').classes('w-full font-mono text-sm')
                
                ui.label('TIMEFRAME').classes('text-[0.6rem] font-bold text-slate-600 tracking-wider mt-2')
                ui.toggle(['1m', '5m', '15m', '1h', '4h'], value='1h', on_change=lambda e: update_timeframe(e.value)).props('unelevated dense spread size=sm color=slate-700 text-color=slate-400 toggle-color=blue-600').classes('w-full border border-slate-700/50 rounded-lg overflow-hidden')

                with ui.row().classes('w-full gap-2 mt-2'):
                    ui.button('START', on_click=start_bot).props('unelevated color=emerald-600').classes('flex-1 font-bold tracking-wide shadow-lg shadow-emerald-900/20')
                    ui.button('STOP', on_click=stop_bot).props('outline color=rose-500').classes('flex-1 font-bold tracking-wide')

            # 2. Mini Stats Card
            with ui.card().classes('glass-panel w-full p-4 flex flex-col gap-3 rounded-xl'):
                ui.label('PERFORMANCE').classes('text-xs font-bold text-slate-500 tracking-wider')
                
                with ui.row().classes('justify-between items-center border-b border-slate-800 pb-2'):
                    ui.label('Lucro Líquido').classes('text-xs text-slate-400')
                    total_profit_val = ui.label('$0.00').classes('font-mono font-bold text-white')
                
                with ui.row().classes('justify-between items-center'):
                    ui.label('Win Rate').classes('text-xs text-slate-400')
                    win_rate_val = ui.label('0.0%').classes('font-mono font-bold text-blue-400')
                    
                # Win/Loss Mini Chart
                win_loss_chart = ui.echart({
                    'backgroundColor': 'transparent',
                    'series': [{'type': 'pie', 'radius': ['60%', '80%'], 'center': ['50%', '50%'], 
                                'label': {'show': False}, 'data': [{'value': 0}, {'value': 0}]}]
                }).classes('h-24 w-full mt-2')

            # 3. Status Log
            with ui.card().classes('glass-panel w-full p-0 flex flex-col flex-grow rounded-xl overflow-hidden min-h-[200px]'):
                ui.label('BOT STATUS').classes('px-4 py-2 text-[0.6rem] font-bold bg-slate-800/50 text-slate-500 tracking-wider border-b border-slate-800')
                with ui.column().classes('p-4 items-center justify-center flex-grow text-center w-full relative'):
                    ui.spinner('bars', size='1.5em', color='blue-500').classes('absolute top-4 right-4').bind_visibility_from(main, 'bot_running')
                    status_ui = ui.markdown('**Pronto.**').classes('text-xs text-slate-300 w-full break-words')

        # --- CENTER/RIGHT CONTENT ---
        with ui.column().classes('flex-grow gap-4 min-w-0'):
            
            # 1. Charts & AI Row
            with ui.row().classes('w-full h-[500px] gap-4 flex-nowrap'):
                
                # Chart Area (Flex Grow)
                with ui.card().classes('glass-panel flex-grow h-full p-0 flex flex-col rounded-xl overflow-hidden'):
                    with ui.tabs().classes('w-full text-slate-400 bg-slate-800/30 border-b border-slate-800') as tabs:
                        tab_market = ui.tab('MARKET').classes('text-xs')
                        tab_equity = ui.tab('EQUITY').classes('text-xs')
                    
                    with ui.tab_panels(tabs, value=tab_market).classes('w-full h-full bg-transparent p-0'):
                        with ui.tab_panel(tab_market).classes('w-full h-full p-2'):
                            # Advanced EChart configuration with Volume
                            candle_chart = ui.echart({
                                'backgroundColor': 'transparent',
                                'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'cross'}, 'backgroundColor': 'rgba(15, 23, 42, 0.9)', 'borderColor': '#334155', 'textStyle': {'color': '#f8fafc'}},
                                'axisPointer': {'link': [{'xAxisIndex': 'all'}]},
                                'grid': [
                                    {'left': '3%', 'right': '1%', 'height': '65%'}, # Price Grid
                                    {'left': '3%', 'right': '1%', 'top': '75%', 'height': '15%'} # Volume Grid
                                ],
                                'xAxis': [
                                    {'type': 'category', 'data': [], 'axisLine': {'lineStyle': {'color': '#475569'}}, 'axisLabel': {'color': '#94a3b8'}},
                                    {'type': 'category', 'gridIndex': 1, 'data': [], 'axisLabel': {'show': False}, 'axisTick': {'show': False}}
                                ],
                                'yAxis': [
                                    {'scale': True, 'splitLine': {'lineStyle': {'color': '#1e293b'}}, 'axisLabel': {'color': '#64748b'}},
                                    {'scale': True, 'gridIndex': 1, 'splitLine': {'show': False}, 'axisLabel': {'show': False}, 'axisTick': {'show': False}}
                                ],
                                'dataZoom': [{'type': 'inside', 'xAxisIndex': [0, 1]}, {'show': True, 'type': 'slider', 'xAxisIndex': [0, 1], 'top': '92%', 'height': 20, 'borderColor': '#334155', 'fillerColor': 'rgba(59, 130, 246, 0.2)'}],
                                'series': [
                                    {
                                        'type': 'candlestick', 'name': 'Price', 'data': [],
                                        'itemStyle': {'color': '#10b981', 'color0': '#f43f5e', 'borderColor': '#10b981', 'borderColor0': '#f43f5e'}
                                    },
                                    {'name': 'BB Upper', 'type': 'line', 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.3, 'color': '#f59e0b', 'width': 1}},
                                    {'name': 'BB Lower', 'type': 'line', 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.3, 'color': '#f59e0b', 'width': 1}},
                                    {'name': 'EMA 200', 'type': 'line', 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'color': '#3b82f6', 'width': 2}},
                                    {'name': 'Volume', 'type': 'bar', 'xAxisIndex': 1, 'yAxisIndex': 1, 'data': [], 'itemStyle': {'color': '#3b82f6', 'opacity': 0.5}}
                                ]
                            }).classes('w-full h-full')

                        with ui.tab_panel(tab_equity).classes('w-full h-full p-2'):
                            equity_chart = ui.echart({
                                'backgroundColor': 'transparent', 'tooltip': {'trigger': 'axis'},
                                'grid': {'left': '3%', 'right': '3%', 'bottom': '3%', 'containLabel': True},
                                'xAxis': {'type': 'category', 'data': [], 'axisLine': {'lineStyle': {'color': '#475569'}}},
                                'yAxis': {'type': 'value', 'splitLine': {'lineStyle': {'color': '#1e293b'}}},
                                'series': [{'data': [], 'type': 'line', 'smooth': True, 'areaStyle': {'color': '#3b82f6', 'opacity': 0.1}, 'lineStyle': {'color': '#3b82f6'}}]
                            }).classes('w-full h-full')

                # AI Insight Panel (Fixed Width)
                ai_card = ui.card().classes('glass-panel w-80 flex-shrink-0 h-full p-0 flex flex-col rounded-xl border-slate-700 transition-all duration-500 overflow-hidden')
                with ai_card:
                    # Header
                    with ui.row().classes('w-full p-4 items-center gap-3 border-b border-white/5 bg-slate-800/30'):
                        ai_icon_container = ui.element('div').classes('p-2 rounded-lg bg-slate-700 transition-colors duration-500')
                        with ai_icon_container:
                            ui.icon('psychology', size='1.5em', color='white')
                        with ui.column().classes('gap-0'):
                            ui.label('GEMINI AI').classes('text-[0.65rem] font-bold text-slate-500 tracking-widest')
                            ai_signal_label = ui.label('AGUARDANDO').classes('text-lg font-black text-slate-400 leading-none')
                    
                    # Content
                    with ui.scroll_area().classes('flex-grow p-4 bg-slate-900/30'):
                        ai_reason_markdown = ui.markdown('_Ocioso. Aguardando dados de mercado..._').classes('text-slate-300 text-xs leading-relaxed font-sans')

            # 2. Bottom Row: Trades Table & Logs
            with ui.row().classes('w-full flex-grow gap-4 min-h-[300px]'):
                
                # Recent Trades Table
                with ui.card().classes('glass-panel flex-1 h-full p-0 flex flex-col rounded-xl overflow-hidden'):
                    ui.label('EXECUÇÕES RECENTES').classes('px-4 py-3 text-[0.65rem] font-bold bg-slate-800/50 text-slate-400 tracking-wider border-b border-slate-800')
                    
                    recent_trades_table = ui.table(
                        columns=[
                            {'name': 'date', 'label': 'HORA', 'field': 'date', 'align': 'left'},
                            {'name': 'pair', 'label': 'PAR', 'field': 'pair', 'align': 'left'},
                            {'name': 'type', 'label': 'TIPO', 'field': 'type', 'align': 'center'},
                            {'name': 'result', 'label': 'RESULTADO', 'field': 'result', 'align': 'center'},
                            {'name': 'pnl', 'label': 'P/L', 'field': 'pnl', 'align': 'right'},
                        ],
                        rows=[],
                        pagination={'rowsPerPage': 10}
                    ).classes('w-full h-full no-shadow bg-transparent text-slate-300').props('flat dense square')
                    
                    # Custom Styling for Table
                    recent_trades_table.add_slot('header', r'''
                        <q-tr :props="props" class="bg-slate-800/50 text-slate-500 text-xs uppercase font-bold tracking-wider">
                            <q-th v-for="col in props.cols" :key="col.name" :props="props" class="text-slate-500">
                                {{ col.label }}
                            </q-th>
                        </q-tr>
                    ''')

                # System Log
                with ui.card().classes('glass-panel w-96 flex-shrink-0 h-full p-0 flex flex-col rounded-xl overflow-hidden border border-slate-800'):
                    with ui.row().classes('px-3 py-2 border-b border-slate-800 justify-between items-center bg-black'):
                        ui.label('TERMINAL_C:/LOGS').classes('text-xs font-mono text-green-500/80')
                        ui.icon('terminal', size='xs', color='green-500')
                    
                    log_ui = ui.log(max_lines=500).classes('w-full h-full bg-black text-green-400 terminal-box p-3 overflow-auto text-xs leading-tight')

    # Initial Data Load
    await update_data()
    ui.timer(2.0, update_data)

ui.run(title='SpotBot Pro | Terminal', dark=True, reload=False, port=8080)
