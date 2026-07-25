from nicegui import ui, app
import os
import asyncio
from collections import deque
from config.settings import DASHBOARD_CONFIG, RISK_PROFILES, TRADING_CONFIG, RSI_CONFIG, TOP_20_SYMBOLS
import config.settings as settings
from services.database import DatabaseManager
import core.engine as engine
from utils.formatting import remove_ansi_codes

db = DatabaseManager()

log_buffer = deque(maxlen=1000)
log_ui = None
status_ui = None
bot_task = None
candle_chart = None
recent_trades_table = None
scanner_table = None
ai_card = None
ai_signal_label = None
ai_reason_markdown = None
ai_icon_container = None
investment_input = None
symbol_select = None
risk_profile_select = None
paper_trading_switch = None
status_indicator = None

bnb_val = None
bnb_usdt_val = None
usdt_val = None
total_profit_val = None
win_rate_val = None

def log_handler(message):
    print(message)
    clean_msg = remove_ansi_codes(message)
    log_buffer.append(clean_msg)
    if log_ui:
        log_ui.push(clean_msg)

def status_handler(message):
    if status_ui:
        clean_msg = remove_ansi_codes(message)
        status_ui.content = f"**{clean_msg}**"

async def update_data():
    try:
        balances = await engine.get_account_balances()
        if balances:
            if bnb_val: bnb_val.text = f"{balances['bnb']:.4f}"
            if bnb_usdt_val: bnb_usdt_val.text = f"~${balances['bnb_usdt']:.2f}"
            if usdt_val: usdt_val.text = f"${balances['usdt']:.2f}"
        
        stats = db.get_stats()
        if total_profit_val:
            total_profit_val.text = f"${stats['total_net_profit']:.2f}"
            total_profit_val.classes(remove='text-emerald-400 text-rose-400', add='text-[#00F5A0]' if stats['total_net_profit'] >= 0 else 'text-[#FF2E93]')
        if win_rate_val:
            win_rate_val.text = f"{stats['win_rate']:.1f}%"
        
        market_data = engine.shared_market_data
        if market_data['dates'] and candle_chart:
            candle_chart.options['xAxis'][0]['data'] = market_data['dates']
            candle_chart.options['xAxis'][1]['data'] = market_data['dates']
            candle_chart.options['series'][0]['data'] = market_data['klines']
            candle_chart.options['series'][1]['data'] = market_data.get('bb_upper', [])
            candle_chart.options['series'][2]['data'] = market_data.get('bb_lower', [])
            candle_chart.options['series'][3]['data'] = market_data.get('ema200', [])
            candle_chart.options['series'][4]['data'] = market_data.get('volumes', [])
            candle_chart.update()

        update_recent_trades_table()

        insight = engine.shared_market_data.get('gemini_insight')
        if insight and ai_signal_label and ai_reason_markdown:
            signal = insight.get('signal', 'N/A')
            ai_signal_label.text = f"{signal}"
            
            if signal == 'COMPRA':
                ai_card.classes(remove='border-slate-800 border-[#FF2E93]/50', add='border-[#00F5A0]/60 shadow-[0_0_25px_rgba(0,245,160,0.2)]')
                ai_signal_label.classes(remove='text-slate-400 text-[#FF2E93] text-[#FFB800]', add='text-[#00F5A0]')
                if ai_icon_container: ai_icon_container.classes(remove='bg-slate-800 bg-[#FF2E93]/10', add='bg-[#00F5A0]/10 text-[#00F5A0]')
            elif signal == 'VENDA':
                ai_card.classes(remove='border-slate-800 border-[#00F5A0]/50 shadow-[0_0_25px_rgba(0,245,160,0.2)]', add='border-[#FF2E93]/60 shadow-[0_0_25px_rgba(255,46,147,0.2)]')
                ai_signal_label.classes(remove='text-slate-400 text-[#00F5A0] text-[#FFB800]', add='text-[#FF2E93]')
                if ai_icon_container: ai_icon_container.classes(remove='bg-slate-800 bg-[#00F5A0]/10', add='bg-[#FF2E93]/10 text-[#FF2E93]')
            else:
                ai_card.classes(remove='border-[#00F5A0]/50 border-[#FF2E93]/50 shadow-[0_0_25px_rgba(0,245,160,0.2)]', add='border-slate-800')
                ai_signal_label.classes(remove='text-slate-400 text-[#00F5A0] text-[#FF2E93]', add='text-[#FFB800]')
                if ai_icon_container: ai_icon_container.classes(remove='bg-[#00F5A0]/10 bg-[#FF2E93]/10', add='bg-[#FFB800]/10 text-[#FFB800]')
                
            ai_reason_markdown.content = insight.get('justification', '**Sem justificativa disponível.**')

    except Exception as e:
        pass

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
        pnl_val = row.get('Resultado da Ordem OCO')
        if not isinstance(pnl_val, (int, float)):
             pnl_val = row.get('Resultado Parcial da Transação Líquido', 0)
        
        try:
            pnl_float = float(pnl_val)
            pnl_str = f"${pnl_float:.2f}"
        except Exception:
            pnl_str = str(pnl_val)
        
        rows.append({
            'date': str(row.get('Data/Hora da Compra', 'N/A')),
            'pair': str(row.get('Símbolo', 'N/A')),
            'type': 'OCO',
            'result': str(row.get('Resultado da Ordem OCO', '-')),
            'pnl': pnl_str,
        })
        
    recent_trades_table.rows = rows

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
    
    ui.notify('Iniciando Sistema SpotBot Pro...', type='positive')
    engine.bot_running = True
    if status_indicator: 
        status_indicator.classes(remove='bg-[#FF2E93]', add='bg-[#00F5A0] animate-pulse shadow-[0_0_15px_#00F5A0]')
    
    bot_task = asyncio.create_task(engine.run_bot(log_callback=log_handler, investment_amount=investment, selected_symbol=symbol, status_callback=status_handler))
    
    try:
        await bot_task
    except asyncio.CancelledError:
        ui.notify('Sistema Parado.', type='info')
        if status_indicator: 
            status_indicator.classes(remove='bg-[#00F5A0] animate-pulse shadow-[0_0_15px_#00F5A0]', add='bg-[#FF2E93]')
    except Exception as e:
        ui.notify(f'Erro: {e}', type='negative')
        if status_indicator: 
            status_indicator.classes(remove='bg-[#00F5A0] animate-pulse shadow-[0_0_15px_#00F5A0]', add='bg-[#FF2E93]')

def stop_bot():
    global bot_task
    if engine.bot_running:
        engine.bot_running = False
        if bot_task:
            bot_task.cancel()
        ui.notify('Parando Sistema...', type='info')
    else:
        ui.notify('Sistema offline.', type='warning')

def update_timeframe(value):
    engine.TRADING_CONFIG['interval'] = value
    engine.shared_market_data['klines'] = []
    engine.shared_market_data['dates'] = []
    ui.notify(f'Timeframe alterado para: {value}', type='info')

def set_risk_profile(val):
    if val in RISK_PROFILES:
        prof = RISK_PROFILES[val]
        TRADING_CONFIG['min_adx'] = prof['adx_min']
        RSI_CONFIG['dynamic_low'][0] = prof['rsi_threshold']
        ui.notify(f'Perfil alterado: {val} (RSI <= {prof["rsi_threshold"]}, ADX >= {prof["adx_min"]})', type='info')

def toggle_paper_trading(e):
    settings.PAPER_TRADING = e.value
    status_text = "Simulação Ativa 🧪" if e.value else "Conta Real 💰"
    ui.notify(f'Modo: {status_text}', type='positive' if e.value else 'warning')

@ui.page('/login')
def login():
    USER = DASHBOARD_CONFIG['user']
    PASS = DASHBOARD_CONFIG['password']
    
    def try_login():
        if username.value == USER and password.value == PASS:
            app.storage.user['authenticated'] = True
            ui.navigate.to('/')
        else:
            ui.notify('Acesso Negado', type='negative')

    ui.colors(primary='#00E5FF', secondary='#64748b', accent='#00F5A0', positive='#00F5A0', negative='#FF2E93', dark='#0B0E14')
    ui.add_head_html('''
        <style>
            body { background-color: #0B0E14; color: #f8fafc; font-family: 'Inter', sans-serif; }
            .zinc-input .q-field__native { color: white !important; }
            .zinc-input .q-field__label { color: #64748b !important; }
            .zinc-input .q-field__control:before { border-color: #1e293b !important; }
        </style>
    ''')

    with ui.column().classes('w-full h-screen items-center justify-center bg-[#0B0E14]'):
        with ui.card().classes('w-80 p-8 bg-[#121722] border border-cyan-500/20 shadow-[0_0_40px_rgba(0,229,255,0.1)] items-center gap-6 rounded-2xl'):
            with ui.column().classes('items-center gap-2'):
                ui.icon('token', size='2.5rem', color='cyan-400')
                ui.label('SPOTBOT PRO').classes('text-2xl font-bold tracking-wider text-white')
                ui.label('INSTITUTIONAL TERMINAL').classes('text-[0.6rem] font-bold text-cyan-400/70 tracking-[0.25em]')
            
            username = ui.input('Usuário').classes('w-full zinc-input').props('dark outlined dense')
            password = ui.input('Senha', password=True, password_toggle_button=True).classes('w-full zinc-input').props('dark outlined dense').on('keydown.enter', try_login)
            
            ui.button('ENTRAR NO TERMINAL', on_click=try_login).props('unelevated').classes('w-full bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-white font-bold tracking-wider py-2 rounded-lg shadow-lg')

@ui.page('/')
async def index():
    if not app.storage.user.get('authenticated', False):
        return ui.navigate.to('/login')

    global log_ui, status_ui, investment_input, symbol_select, bnb_val, bnb_usdt_val, usdt_val
    global total_profit_val, win_rate_val, recent_trades_table, status_indicator, candle_chart, scanner_table
    global ai_signal_label, ai_reason_markdown, ai_card, ai_icon_container, risk_profile_select, paper_trading_switch
    
    ui.colors(primary='#00E5FF', secondary='#64748b', accent='#00F5A0', positive='#00F5A0', negative='#FF2E93', dark='#0B0E14')
    
    ui.add_head_html('''
        <style>
            :root { --nicegui-default-padding: 0.5rem; }
            body { background-color: #0B0E14; color: #f8fafc; font-family: 'Inter', system-ui, -apple-system, sans-serif; overflow-x: hidden; }
            ::-webkit-scrollbar { width: 6px; height: 6px; }
            ::-webkit-scrollbar-track { background: #0B0E14; }
            ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
            ::-webkit-scrollbar-thumb:hover { background: #334155; }
            .obsidian-card { background: #121722; border: 1px solid rgba(255, 255, 255, 0.07); }
            .input-zinc .q-field__native { color: #f8fafc !important; }
            .input-zinc .q-field__label { color: #64748b !important; }
            .input-zinc .q-field__control:before { border-color: #1e293b !important; }
            .terminal-font { font-family: 'JetBrains Mono', monospace; }

            /* Marquee Ticker CoinMarketCap Style */
            @keyframes ticker {
                0% { transform: translate3d(0, 0, 0); }
                100% { transform: translate3d(-50%, 0, 0); }
            }
            .ticker-wrap {
                width: 100%;
                overflow: hidden;
                white-space: nowrap;
                box-sizing: border-box;
                background: #080B10;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            .ticker-move {
                display: inline-block;
                white-space: nowrap;
                padding-right: 100%;
                box-sizing: content-box;
                animation: ticker 35s linear infinite;
            }
            .ticker-item {
                display: inline-block;
                padding: 0 1.25rem;
                font-size: 0.7rem;
                font-weight: 600;
            }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    ''')

    # Barra Marquee Estilo CoinMarketCap no Topo
    with ui.element('div').classes('ticker-wrap py-1 flex items-center border-b border-slate-800/80'):
        with ui.element('div').classes('ticker-move'):
            ui.html('''
                <span class="ticker-item text-slate-400">Market Cap: <b class="text-white">$2.38T</b> <span class="text-[#00F5A0]">(+0.62%)</span></span>
                <span class="ticker-item text-slate-400">24h Vol: <b class="text-white">$78.4B</b></span>
                <span class="ticker-item text-slate-400">Bitcoin Dominance: <b class="text-cyan-400">54.2%</b></span>
                <span class="ticker-item text-slate-400">BTC: <b class="text-white">$64,340.00</b> <span class="text-[#00F5A0]">(+0.37%)</span></span>
                <span class="ticker-item text-slate-400">ETH: <b class="text-white">$1,873.20</b> <span class="text-[#00F5A0]">(+0.81%)</span></span>
                <span class="ticker-item text-slate-400">BNB: <b class="text-white">$568.49</b> <span class="text-[#00F5A0]">(+0.82%)</span></span>
                <span class="ticker-item text-slate-400">SOL: <b class="text-white">$74.38</b> <span class="text-[#FF2E93]">(-1.44%)</span></span>
                <span class="ticker-item text-slate-400">XRP: <b class="text-white">$1.09</b> <span class="text-[#00F5A0]">(+0.87%)</span></span>
                
                <span class="ticker-item text-slate-400">Market Cap: <b class="text-white">$2.38T</b> <span class="text-[#00F5A0]">(+0.62%)</span></span>
                <span class="ticker-item text-slate-400">24h Vol: <b class="text-white">$78.4B</b></span>
                <span class="ticker-item text-slate-400">Bitcoin Dominance: <b class="text-cyan-400">54.2%</b></span>
                <span class="ticker-item text-slate-400">BTC: <b class="text-white">$64,340.00</b> <span class="text-[#00F5A0]">(+0.37%)</span></span>
                <span class="ticker-item text-slate-400">ETH: <b class="text-white">$1,873.20</b> <span class="text-[#00F5A0]">(+0.81%)</span></span>
                <span class="ticker-item text-slate-400">BNB: <b class="text-white">$568.49</b> <span class="text-[#00F5A0]">(+0.82%)</span></span>
                <span class="ticker-item text-slate-400">SOL: <b class="text-white">$74.38</b> <span class="text-[#FF2E93]">(-1.44%)</span></span>
                <span class="ticker-item text-slate-400">XRP: <b class="text-white">$1.09</b> <span class="text-[#00F5A0]">(+0.87%)</span></span>
            ''')

    # Topbar Header Futurista
    with ui.header().classes('h-14 bg-[#0B0E14]/90 backdrop-blur-md border-b border-slate-800/80 flex items-center px-4 justify-between z-50'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('token', size='1.6em', color='cyan-400').classes('drop-shadow-[0_0_8px_rgba(0,229,255,0.6)]')
            with ui.column().classes('gap-0'):
                ui.label('SPOTBOT PRO').classes('text-sm font-bold tracking-wider text-white leading-none')
                ui.label('QUANTITATIVE ENGINE').classes('text-[0.55rem] font-semibold text-cyan-400/80 tracking-[0.2em] leading-none')
        
        with ui.row().classes('items-center gap-3 bg-[#121722]/80 p-1.5 rounded-xl border border-slate-800'):
            ui.button('START', on_click=start_bot).props('flat dense size=sm').classes('text-[#00F5A0] font-bold px-3 hover:bg-[#00F5A0]/10 rounded-lg')
            with ui.element('div').classes('w-px h-4 bg-slate-800'): pass
            ui.button('STOP', on_click=stop_bot).props('flat dense size=sm').classes('text-[#FF2E93] font-bold px-3 hover:bg-[#FF2E93]/10 rounded-lg')
            with ui.element('div').classes('w-px h-4 bg-slate-800'): pass
            def logout():
                app.storage.user.clear()
                ui.navigate.to('/login')
            ui.button(icon='logout', on_click=logout).props('flat dense size=sm').classes('text-slate-400 hover:text-white px-2 rounded-lg')

        with ui.row().classes('items-center gap-4'):
            with ui.row().classes('items-center gap-2 hidden md:flex bg-[#121722] px-3 py-1 rounded-lg border border-slate-800'):
                ui.label('USDT').classes('text-[0.6rem] font-bold text-slate-500')
                usdt_val = ui.label('$0.00').classes('text-xs font-mono font-bold text-white')
            # Pulso luminoso verde / rosa no cabeçalho
            status_indicator = ui.element('div').classes('w-3 h-3 rounded-full bg-[#FF2E93] shadow-[0_0_10px_#FF2E93]')

    # Layout Principal
    with ui.row().classes('w-full min-h-[calc(100vh-3.5rem)] flex-nowrap gap-0 bg-[#0B0E14]'):
        # Sidebar Esquerda
        with ui.column().classes('w-64 flex-shrink-0 bg-[#0B0E14] border-r border-slate-800/80 h-full p-4 gap-4'):
            with ui.column().classes('w-full gap-2'):
                ui.label('MODO DE MONITORAMENTO').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest')
                symbol_select = ui.select(['⚡ SCANNER TOP 20'] + TOP_20_SYMBOLS, value='⚡ SCANNER TOP 20').props('outlined dense options-dense color=cyan-500').classes('w-full input-zinc font-mono text-xs')
                investment_input = ui.input('Valor USDT por Ordem', value='Dinâmico (Min $10)').props('outlined dense color=cyan-500').classes('w-full input-zinc font-mono text-xs')
                
                ui.label('PERFIL DE RISCO').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest mt-1')
                risk_profile_select = ui.select(['Conservador', 'Moderado', 'Agressivo'], value='Moderado', on_change=lambda e: set_risk_profile(e.value)).props('outlined dense options-dense color=cyan-500').classes('w-full input-zinc text-xs')

                ui.label('PAPER TRADING').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest mt-1')
                paper_trading_switch = ui.switch('Simulação', value=False, on_change=toggle_paper_trading).props('dense color=cyan-500').classes('text-xs text-slate-400')

                ui.label('TIMEFRAME ADAPTATIVO').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest mt-1')
                ui.toggle(['Adaptativo (1h/15m)', '15m (Scalping)', '1h (Swing)'], value='Adaptativo (1h/15m)').props('unelevated dense spread size=xs color=slate-900 text-color=slate-400 toggle-color=cyan-600').classes('w-full border border-slate-800 rounded-lg overflow-hidden text-[0.6rem]')

            with ui.column().classes('w-full gap-2 mt-2'):
                ui.label('PERFORMANCE').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest')
                with ui.row().classes('w-full justify-between items-center p-2.5 rounded-xl bg-[#121722] border border-slate-800'):
                    ui.label('Lucro Total').classes('text-xs text-slate-400')
                    total_profit_val = ui.label('$0.00').classes('font-mono text-sm font-bold text-[#00F5A0]')
                with ui.row().classes('w-full justify-between items-center p-2.5 rounded-xl bg-[#121722] border border-slate-800'):
                    ui.label('Taxa de Vitória').classes('text-xs text-slate-400')
                    win_rate_val = ui.label('0.0%').classes('font-mono text-sm font-bold text-cyan-400')

            with ui.column().classes('w-full gap-1 mt-1'):
                ui.label('STATUS ATUAL').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest')
                status_ui = ui.markdown('**Aguardando...**').classes('text-xs text-slate-300 leading-relaxed w-full break-words')

        # Painel Central de Gráfico e Tabelas
        with ui.column().classes('flex-grow h-screen p-0 overflow-hidden relative bg-[#0B0E14]'):
             with ui.card().classes('w-full h-[65vh] p-0 rounded-none bg-[#0B0E14] border-b border-slate-800 gap-0 shadow-none relative'):
                 # Card IA Holográfico Otimizado
                 ai_card = ui.card().classes('absolute top-4 left-4 w-80 z-20 obsidian-card p-3.5 rounded-2xl shadow-[0_10px_30px_rgba(0,0,0,0.5)] opacity-95 backdrop-blur-md transition-all duration-300')
                 with ai_card:
                     with ui.row().classes('w-full items-center justify-between mb-2'):
                         with ui.row().classes('items-center gap-2'):
                             ai_icon_container = ui.element('div').classes('p-1.5 rounded-lg bg-slate-800/80 text-slate-400')
                             with ai_icon_container: ui.icon('psychology', size='sm')
                             ai_signal_label = ui.label('NEUTRO').classes('text-xs font-bold tracking-wide text-slate-400')
                         
                         def toggle_ai_content():
                             is_visible = ai_reason_scroll.visible
                             ai_reason_scroll.set_visibility(not is_visible)
                             toggle_btn.props(f'icon={"keyboard_arrow_down" if is_visible else "keyboard_arrow_up"}')

                         toggle_btn = ui.button(icon='keyboard_arrow_up', on_click=toggle_ai_content).props('flat dense round size=xs color=slate-400')
                     
                     ai_reason_scroll = ui.scroll_area().classes('h-28')
                     with ai_reason_scroll:
                         ai_reason_markdown = ui.markdown('_IA Gemini monitorando mercado..._').classes('text-[0.68rem] text-slate-300 leading-relaxed')

                 # ECharts com Cores Cyberpunk Neon
                 with ui.element('div').classes('w-full h-full'):
                     candle_chart = ui.echart({
                        'backgroundColor': '#0B0E14',
                        'grid': [{'left': '50', 'right': '25', 'top': '45', 'height': '60%'}, {'left': '50', 'right': '25', 'top': '78%', 'height': '15%'}],
                        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'cross'}, 'backgroundColor': 'rgba(18, 23, 34, 0.95)', 'borderColor': '#00E5FF', 'textStyle': {'color': '#f8fafc'}},
                        'dataZoom': [{'type': 'inside', 'xAxisIndex': [0, 1]}, {'type': 'slider', 'xAxisIndex': [0, 1], 'bottom': 5, 'height': 20, 'borderColor': '#1e293b', 'dataBackground': {'lineStyle': {'color': '#00E5FF'}, 'areaStyle': {'color': '#121722'}}}],
                        'xAxis': [{'type': 'category', 'data': [], 'gridIndex': 0, 'axisLine': {'lineStyle': {'color': '#334155'}}}, {'type': 'category', 'data': [], 'gridIndex': 1, 'axisLabel': {'show': False}, 'axisTick': {'show': False}, 'axisLine': {'show': False}}],
                        'yAxis': [{'type': 'value', 'scale': True, 'gridIndex': 0, 'splitLine': {'lineStyle': {'color': 'rgba(255, 255, 255, 0.05)'}}, 'position': 'right'}, {'type': 'value', 'scale': True, 'gridIndex': 1, 'splitLine': {'show': False}, 'axisLabel': {'show': False}, 'axisTick': {'show': False}}],
                        'series': [
                            {'type': 'candlestick', 'name': 'Preço', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'itemStyle': {'color': '#00F5A0', 'color0': '#FF2E93', 'borderColor': '#00F5A0', 'borderColor0': '#FF2E93'}},
                            {'name': 'BB Upper', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.4, 'color': '#FFB800', 'width': 1.5}},
                            {'name': 'BB Lower', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.4, 'color': '#FFB800', 'width': 1.5}},
                            {'name': 'EMA 200', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'color': '#00E5FF', 'width': 2}},
                            {'name': 'Volume', 'type': 'bar', 'xAxisIndex': 1, 'yAxisIndex': 1, 'data': [], 'itemStyle': {'color': '#00E5FF', 'opacity': 0.25}, 'large': True}
                        ]
                     }).classes('w-full h-full')

             # Painel Inferior (Execuções + Log Terminal)
             with ui.row().classes('w-full flex-grow flex-nowrap gap-0 bg-[#0B0E14]'):
                 with ui.column().classes('w-3/5 h-full border-r border-slate-800/80 bg-[#0B0E14] p-0'):
                     with ui.row().classes('w-full h-8 items-center px-4 border-b border-slate-800 bg-[#121722]/50 justify-between'):
                         ui.label('HISTÓRICO DE EXECUÇÕES').classes('text-[0.6rem] font-bold text-slate-400 tracking-widest')
                         ui.icon('history', size='xs', color='slate-500')
                      
                     recent_trades_table = ui.table(
                         columns=[
                            {'name': 'date', 'label': 'Horário', 'field': 'date', 'align': 'left'},
                            {'name': 'pair', 'label': 'Par', 'field': 'pair', 'align': 'left'},
                            {'name': 'type', 'label': 'Tipo', 'field': 'type', 'align': 'center'},
                            {'name': 'pnl', 'label': 'PnL Líquido', 'field': 'pnl', 'align': 'right'},
                         ],
                         rows=[],
                         pagination={'rowsPerPage': 5}
                     ).classes('w-full h-full no-shadow bg-transparent text-slate-300').props('flat dense square')
                     recent_trades_table.add_slot('header', r'''
                        <q-tr :props="props" class="bg-[#121722] text-slate-400 text-xs font-semibold">
                            <q-th v-for="col in props.cols" :key="col.name" :props="props">
                                {{ col.label }}
                            </q-th>
                        </q-tr>
                     ''')

                 with ui.column().classes('w-2/5 h-full bg-[#0B0E14] p-0'):
                     with ui.row().classes('w-full h-8 items-center px-4 border-b border-slate-800 bg-[#121722]/50 gap-2'):
                        ui.icon('terminal', size='xs', color='cyan-400')
                        ui.label('TERMINAL OUTPUT').classes('text-[0.6rem] font-bold text-slate-400 tracking-widest')
                      
                     log_ui = ui.log(max_lines=500).classes('w-full flex-grow bg-[#080B10] text-[#00F5A0] terminal-font text-[0.72rem] p-3 leading-relaxed border-0')
                     for msg in log_buffer:
                         log_ui.push(msg)

    ui.timer(2.0, update_data)

def start_dashboard():
    port = DASHBOARD_CONFIG['port']
    secret = DASHBOARD_CONFIG['secret_key']
    ui.run(title='SpotBot Pro | Institutional Terminal', dark=True, reload=False, port=port, storage_secret=secret)

if __name__ in {"__main__", "__mp_main__"}:
    start_dashboard()
