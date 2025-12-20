from nicegui import ui, app
import asyncio
from collections import deque
import main
from database import DatabaseManager

# Initialize DB
db = DatabaseManager()

# Global State
log_buffer = deque(maxlen=1000)
log_ui = None
status_ui = None
bot_task = None
candle_chart = None
recent_trades_table = None
ai_card = None
ai_signal_label = None
ai_reason_markdown = None
ai_icon_container = None
investment_input = None
symbol_select = None
status_indicator = None

# KPI Labels
bnb_val = None
bnb_usdt_val = None
usdt_val = None
total_profit_val = None
win_rate_val = None

# --- Handlers ---
def log_handler(message):
    print(message)
    log_buffer.append(message)
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
        if bnb_val: bnb_val.text = f"{balances['bnb']:.4f}"
        if bnb_usdt_val: bnb_usdt_val.text = f"~${balances['bnb_usdt']:.2f}"
        if usdt_val: usdt_val.text = f"${balances['usdt']:.2f}"
    
    # 2. Database Stats
    stats = db.get_stats()
    if total_profit_val:
        total_profit_val.text = f"${stats['total_net_profit']:.2f}"
        total_profit_val.classes(remove='text-emerald-400 text-rose-400', add='text-emerald-400' if stats['total_net_profit'] >= 0 else 'text-rose-400')
    if win_rate_val:
        win_rate_val.text = f"{stats['win_rate']:.1f}%"
    
    # 3. Market Chart Update (Price + Volume)
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
        
        # Series 4: Volume
        candle_chart.options['series'][4]['data'] = market_data.get('volumes', [])
        
        # Series 4: Volume
        candle_chart.options['series'][4]['data'] = market_data.get('volumes', [])
        
        candle_chart.update()
        candle_chart.run_method('resize')

    # 4. Recent Trades (Table)
    update_recent_trades_table()
    
    # 5. Logs Scroll
    if log_ui:
        log_ui.run_method('scrollTo', 0, 999999)

    # 6. AI Insight Update
    insight = main.shared_market_data.get('gemini_insight')
    if insight and ai_signal_label and ai_reason_markdown:
        signal = insight.get('signal', 'N/A')
        ai_signal_label.text = f"{signal}"
        
        # Color Logic
        if signal == 'COMPRA':
            ai_card.classes(remove='border-zinc-800', add='border-emerald-500/50 shadow-[0_0_20px_rgba(16,185,129,0.1)]')
            ai_signal_label.classes(remove='text-zinc-500 text-rose-500 text-amber-500', add='text-emerald-400')
            ai_icon_container.classes(remove='bg-zinc-800', add='bg-emerald-500/10 text-emerald-400')
        elif signal == 'VENDA':
            ai_card.classes(remove='border-zinc-800 border-emerald-500/50 shadow-[0_0_20px_rgba(16,185,129,0.1)]', add='border-rose-500/50')
            ai_signal_label.classes(remove='text-zinc-500 text-emerald-400 text-amber-500', add='text-rose-500')
            ai_icon_container.classes(remove='bg-zinc-800', add='bg-rose-500/10 text-rose-400')
        else:
            ai_card.classes(remove='border-emerald-500/50 border-rose-500/50 shadow-[0_0_20px_rgba(16,185,129,0.1)]', add='border-zinc-800')
            ai_signal_label.classes(remove='text-zinc-500 text-emerald-400 text-rose-500', add='text-amber-500')
            ai_icon_container.classes(remove='bg-zinc-800', add='bg-amber-500/10 text-amber-400')
            
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
        
        try:
            pnl_float = float(pnl_val)
            pnl_str = f"${pnl_float:.2f}"
            pnl_class = 'text-emerald-400' if pnl_float >= 0 else 'text-rose-400'
        except:
            pnl_str = str(pnl_val)
            pnl_class = 'text-zinc-400'
        
        rows.append({
            'date': str(row.get('Data/Hora da Compra', 'N/A')),
            'pair': str(row.get('Símbolo', 'N/A')),
            'type': 'OCO',
            'result': str(row.get('Resultado da Ordem OCO', '-')),
            'pnl': pnl_str,
            '_row_class': '' # Clean look
        })
        
    recent_trades_table.rows = rows

# --- Bot Controls ---
async def start_bot():
    global bot_task
    if bot_task and not bot_task.done():
        ui.notify('Bot já está rodando!', type='warning')
        return

    investment = investment_input.value if investment_input else None
    symbol = symbol_select.value if symbol_select else None
    
    if not investment:
        ui.notify('Investimento não definido.', type='warning')
        return
    
    ui.notify('Iniciando Sistema...')
    main.bot_running = True
    if status_indicator: status_indicator.classes(remove='bg-rose-500', add='bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.7)]')
    
    bot_task = asyncio.create_task(main.run_bot(log_callback=log_handler, investment_amount=investment, selected_symbol=symbol, status_callback=status_handler))
    
    try:
        await bot_task
    except asyncio.CancelledError:
        ui.notify('Sistema Parado.', type='info')
        if status_indicator: status_indicator.classes(remove='bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.7)]', add='bg-rose-500')
    except Exception as e:
        ui.notify(f'Erro: {e}', type='negative')
        if status_indicator: status_indicator.classes(remove='bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.7)]', add='bg-rose-500')

def stop_bot():
    global bot_task
    if main.bot_running:
        main.bot_running = False
        if bot_task:
            bot_task.cancel()
        ui.notify('Parando Sistema...', type='info')
    else:
        ui.notify('Sistema offline.', type='warning')

def update_timeframe(value):
    if hasattr(main, 'TRADING_CONFIG'):
        main.TRADING_CONFIG['interval'] = value
        main.shared_market_data['klines'] = []
        main.shared_market_data['dates'] = []
        ui.notify(f'Timeframe: {value}')

# --- UI Layout ---
@ui.page('/')
async def index():
    global log_ui, status_ui, investment_input, symbol_select, bnb_val, bnb_usdt_val, usdt_val
    global total_profit_val, win_rate_val, recent_trades_table, status_indicator, candle_chart
    global ai_signal_label, ai_reason_markdown, ai_card, ai_icon_container
    
    # Premium Theme
    ui.colors(primary='#22d3ee', secondary='#94a3b8', accent='#f472b6', positive='#34d399', negative='#fb7185', dark='#000000')
    
    ui.add_head_html('''
        <style>
            :root { --nicegui-default-padding: 0.5rem; }
            body { background-color: #000000; color: #e2e8f0; font-family: 'Inter', system-ui, -apple-system, sans-serif; }
            
            /* Custom Scrollbar */
            ::-webkit-scrollbar { width: 6px; height: 6px; }
            ::-webkit-scrollbar-track { background: #09090b; }
            ::-webkit-scrollbar-thumb { background: #27272a; border-radius: 3px; }
            ::-webkit-scrollbar-thumb:hover { background: #3f3f46; }
            
            /* Zinc Panel */
            .zinc-panel {
                background: #09090b; /* zinc-950 */
                border: 1px solid #27272a; /* zinc-800 */
            }
            
            .input-zinc .q-field__native { color: #f4f4f5 !important; }
            .input-zinc .q-field__label { color: #71717a !important; }
            .input-zinc .q-field__control:before { border-color: #27272a !important; }
            
            /* Terminal */
            .terminal-font { font-family: 'JetBrains Mono', monospace; }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    ''')

    # --- Header ---
    with ui.header().classes('h-14 bg-black/80 backdrop-blur border-b border-zinc-800 flex items-center px-4 justify-between z-50'):
        # Logo
        with ui.row().classes('items-center gap-2'):
            ui.icon('token', size='1.5em', color='cyan-400')
            with ui.column().classes('gap-0'):
                ui.label('SPOTBOT').classes('text-sm font-bold tracking-tight text-white leading-none')
                ui.label('TERMINAL').classes('text-[0.6rem] font-medium text-zinc-500 tracking-[0.2em] leading-none')
        
        # Center Controls
        with ui.row().classes('items-center gap-2 bg-zinc-900/50 p-1 rounded-lg border border-zinc-800/50'):
            ui.button('START', on_click=start_bot).props('flat dense size=sm').classes('text-emerald-400 font-bold px-3 hover:bg-emerald-500/10 rounded')
            with ui.element('div').classes('w-px h-4 bg-zinc-800'): pass
            ui.button('STOP', on_click=stop_bot).props('flat dense size=sm').classes('text-rose-400 font-bold px-3 hover:bg-rose-500/10 rounded')

        # KPI & Actions
        with ui.row().classes('items-center gap-4'):
            with ui.row().classes('items-center gap-2 hidden md:flex'):
                ui.label('USDT').classes('text-[0.65rem] font-bold text-zinc-600')
                usdt_val = ui.label('$0.00').classes('text-sm font-mono text-white')
            
            status_indicator = ui.element('div').classes('w-2 h-2 rounded-full bg-rose-500')

    # --- Main Content ---
    with ui.row().classes('w-full min-h-[calc(100vh-3.5rem)] flex-nowrap gap-0'):
        
        # --- SIDEBAR (Compact) ---
        with ui.column().classes('w-64 flex-shrink-0 bg-black border-r border-zinc-800 h-full p-4 gap-6'):
            
            # Config
            with ui.column().classes('w-full gap-3'):
                ui.label('CONFIGURAÇÃO').classes('text-[0.6rem] font-bold text-zinc-600 tracking-wider')
                
                symbol_select = ui.select(
                    ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'], value='BTCUSDT'
                ).props('outlined dense options-dense color=cyan-500').classes('w-full input-zinc font-mono text-xs')
                
                investment_input = ui.input(
                    'Valor (USDT)', value='100%'
                ).props('outlined dense color=cyan-500').classes('w-full input-zinc font-mono text-xs')
                
                ui.label('TIMEFRAME').classes('text-[0.6rem] font-bold text-zinc-600 tracking-wider mt-2')
                ui.toggle(['1m', '15m', '1h', '4h'], value='1h', on_change=lambda e: update_timeframe(e.value)).props('unelevated dense spread size=xs color=zinc-800 text-color=zinc-400 toggle-color=cyan-600').classes('w-full border border-zinc-800 rounded')

            # Mini Perf
            with ui.column().classes('w-full gap-3 mt-4'):
                ui.label('PERFORMANCE').classes('text-[0.6rem] font-bold text-zinc-600 tracking-wider')
                
                with ui.row().classes('w-full justify-between items-center p-2 rounded bg-zinc-900 border border-zinc-800'):
                    ui.label('Profit').classes('text-xs text-zinc-400')
                    total_profit_val = ui.label('$0.00').classes('font-mono text-sm text-emerald-400')
                    
                with ui.row().classes('w-full justify-between items-center p-2 rounded bg-zinc-900 border border-zinc-800'):
                    ui.label('Win Rate').classes('text-xs text-zinc-400')
                    win_rate_val = ui.label('0.0%').classes('font-mono text-sm text-cyan-400')


            
            # Bot Status Text
            with ui.column().classes('w-full gap-1'):
                ui.label('STATUS ATUAL').classes('text-[0.6rem] font-bold text-zinc-600 tracking-wider')
                status_ui = ui.markdown('**Aguardando...**').classes('text-xs text-zinc-300 leading-tight w-full break-words')

        # --- CENTER AREA (Graphs & AI) ---
        with ui.column().classes('flex-grow h-screen p-0 overflow-hidden relative'):
             
             # Chart Container (Fixed Height)
             with ui.card().classes('w-full h-[65vh] p-0 rounded-none bg-black border-b border-zinc-800 gap-0 shadow-none relative'):
                 
                 # Overlay AI Card (Floating Top Left)
                 ai_card = ui.card().classes('absolute top-4 left-4 w-72 z-20 zinc-panel p-3 rounded-lg shadow-xl opacity-90 backdrop-blur-sm')
                 with ai_card:
                     with ui.row().classes('w-full items-center justify-between mb-2'):
                         with ui.row().classes('items-center gap-2'):
                             ai_icon_container = ui.element('div').classes('p-1 rounded bg-zinc-800 text-zinc-400')
                             with ai_icon_container: ui.icon('psychology', size='xs')
                             ai_signal_label = ui.label('NEUTRO').classes('text-sm font-bold text-zinc-400')
                         
                         def toggle_ai_content():
                             is_visible = ai_reason_scroll.visible
                             ai_reason_scroll.set_visibility(not is_visible)
                             # Update icon: Arrow Down (to expand) if hidden, Arrow Up (to collapse) if visible
                             toggle_btn.props(f'icon={"keyboard_arrow_down" if is_visible else "keyboard_arrow_up"}')

                         toggle_btn = ui.button(icon='keyboard_arrow_up', on_click=toggle_ai_content).props('flat dense round size=xs color=zinc-500')
                     
                     ai_reason_scroll = ui.scroll_area().classes('h-24')
                     with ai_reason_scroll:
                         ai_reason_markdown = ui.markdown('_IA analisando mercado..._').classes('text-[0.65rem] text-zinc-400 leading-relaxed')

                 # CHART (Direct Child, No Tabs)
                 with ui.element('div').classes('w-full h-full'):
                     candle_chart = ui.echart({
                        'backgroundColor': '#000000',
                        'grid': [
                            {'left': '50', 'right': '20', 'top': '40', 'height': '60%'},
                            {'left': '50', 'right': '20', 'top': '75%', 'height': '15%'}
                        ],
                        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'cross'}, 'backgroundColor': 'rgba(24, 24, 27, 0.9)', 'borderColor': '#3f3f46', 'textStyle': {'color': '#e4e4e7'}},
                        'dataZoom': [{'type': 'inside', 'xAxisIndex': [0, 1]}, {'type': 'slider', 'xAxisIndex': [0, 1], 'bottom': 5, 'height': 20, 'borderColor': '#27272a', 'dataBackground': {'lineStyle': {'color': '#71717a'}, 'areaStyle': {'color': '#27272a'}}}],
                        'xAxis': [
                            {'type': 'category', 'data': [], 'gridIndex': 0, 'axisLine': {'lineStyle': {'color': '#52525b'}}},
                            {'type': 'category', 'data': [], 'gridIndex': 1, 'axisLabel': {'show': False}, 'axisTick': {'show': False}, 'axisLine': {'show': False}}
                        ],
                        'yAxis': [
                            {'type': 'value', 'scale': True, 'gridIndex': 0, 'splitLine': {'lineStyle': {'color': '#18181b'}}, 'position': 'right'},
                            {'type': 'value', 'scale': True, 'gridIndex': 1, 'splitLine': {'show': False}, 'axisLabel': {'show': False}, 'axisTick': {'show': False}}
                        ],
                        'series': [
                            {'type': 'candlestick', 'name': 'Price', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'itemStyle': {'color': '#34d399', 'color0': '#fb7185', 'borderColor': '#34d399', 'borderColor0': '#fb7185'}},
                            {'name': 'BB Upper', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.3, 'color': '#f59e0b', 'width': 1}},
                            {'name': 'BB Lower', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.3, 'color': '#f59e0b', 'width': 1}},
                            {'name': 'EMA 200', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'color': '#3b82f6', 'width': 2}},
                            {'name': 'Volume', 'type': 'bar', 'xAxisIndex': 1, 'yAxisIndex': 1, 'data': [], 'itemStyle': {'color': '#3b82f6', 'opacity': 0.3}, 'large': True}
                        ]
                     }).classes('w-full h-full')

             # --- BOTTOM AREA (Table & Logs) ---
             with ui.row().classes('w-full flex-grow flex-nowrap gap-0'):
                 
                 # Table (Left, 60%)
                 with ui.column().classes('w-3/5 h-full border-r border-zinc-800 bg-black p-0'):
                     with ui.row().classes('w-full h-8 items-center px-4 border-b border-zinc-800 bg-zinc-950'):
                         ui.label('EXECUÇÕES').classes('text-[0.6rem] font-bold text-zinc-500 tracking-wider')
                     
                     recent_trades_table = ui.table(
                         columns=[
                            {'name': 'date', 'label': 'Time', 'field': 'date', 'align': 'left'},
                            {'name': 'pair', 'label': 'Pair', 'field': 'pair', 'align': 'left'},
                            {'name': 'type', 'label': 'Type', 'field': 'type', 'align': 'center'},
                            {'name': 'pnl', 'label': 'PnL', 'field': 'pnl', 'align': 'right'},
                         ],
                         rows=[],
                         pagination={'rowsPerPage': 5}
                     ).classes('w-full h-full no-shadow bg-transparent text-zinc-300').props('flat dense square')
                     # Table slots for styling
                     recent_trades_table.add_slot('header', r'''
                        <q-tr :props="props" class="bg-zinc-900 text-zinc-500 text-xs font-medium">
                            <q-th v-for="col in props.cols" :key="col.name" :props="props">
                                {{ col.label }}
                            </q-th>
                        </q-tr>
                     ''')

                 # Logs (Right, 40%)
                 with ui.column().classes('w-2/5 h-full bg-black p-0'):
                     with ui.row().classes('w-full h-8 items-center px-4 border-b border-zinc-800 bg-zinc-950'):
                        ui.icon('terminal', size='xs', color='zinc-600')
                        ui.label('OUTPUT').classes('text-[0.6rem] font-bold text-zinc-500 tracking-wider')
                     
                     log_ui = ui.log(max_lines=500).classes('w-full flex-grow bg-zinc-950 text-emerald-500 terminal-font text-[0.7rem] p-2 leading-tight')
                     for msg in log_buffer:
                         log_ui.push(remove_ansi_codes(msg))

    # Init
    ui.timer(2.0, update_data)

ui.run(title='SpotBot Pro | Terminal', dark=True, reload=False, port=8080)
