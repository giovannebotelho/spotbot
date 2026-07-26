import asyncio
import os
from nicegui import ui, app
import pandas as pd
from datetime import datetime

from config.settings import DASHBOARD_CONFIG, TRADING_CONFIG, RSI_CONFIG, RISK_PROFILES
import config.settings as settings
from services.database import DatabaseManager
from utils.formatting import remove_ansi_codes
import core.engine as engine

db = DatabaseManager()

log_ui = None
status_ui = None
investment_input = None
symbol_select = None
status_indicator = None

bnb_val = None
bnb_usdt_val = None
usdt_val = None

total_profit_val = None
win_rate_val = None
recent_trades_table = None

candle_chart = None
scanner_table = None

ai_card = None
ai_signal_label = None
ai_reason_markdown = None
ai_icon_container = None

risk_profile_select = None
paper_trading_switch = None

chart_symbol_badge = None

bot_task = None

def log_handler(message):
    clean_msg = remove_ansi_codes(message)
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
        
        active_symbol = engine.bot_status_data.get('target_asset', 'BTCUSDT')
        current_price = engine.bot_status_data.get('price', 0.0)
        price_str = f"${current_price:.4f}" if (current_price > 0 and current_price < 1.0) else f"${current_price:.2f}"

        if chart_symbol_badge:
            chart_symbol_badge.text = f"🪙 {active_symbol} ({price_str})"

        market_data = engine.shared_market_data
        if market_data['dates'] and candle_chart:
            candle_chart.options['title'] = {
                'text': f'📈 {active_symbol} — Gráfico em Tempo Real ({price_str})',
                'subtext': 'Alimentado por Binance WebSockets & Scanner 2.0 Quantitativo',
                'left': 'center',
                'top': 10,
                'textStyle': {'color': '#00E5FF', 'fontSize': 14, 'fontWeight': 'bold'},
                'subtextStyle': {'color': '#64748b', 'fontSize': 9.5}
            }
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
        status_indicator.classes(remove='bg-[#FF2E93] bg-[#FFB800]', add='bg-[#00F5A0] animate-pulse shadow-[0_0_15px_#00F5A0]')
    
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
        ui.notify('Parando Sistema com segurança...', type='info')
    else:
        ui.notify('Sistema offline.', type='warning')

def cancel_bot():
    global bot_task
    engine.bot_running = False
    if bot_task and not bot_task.done():
        bot_task.cancel()
    ui.notify('🚨 EMERGÊNCIA: Execução abortada via Cancel (CTRL+C)!', type='negative')
    if status_indicator: 
        status_indicator.classes(remove='bg-[#00F5A0] animate-pulse shadow-[0_0_15px_#00F5A0]', add='bg-[#FFB800]')

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
    global chart_symbol_badge
    
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

            @keyframes marquee {
                0% { transform: translateX(0%); }
                100% { transform: translateX(-50%); }
            }
            .animate-marquee {
                display: flex;
                width: 200%;
                animation: marquee 30s linear infinite;
            }
            .animate-marquee:hover {
                animation-play-state: paused;
            }
        </style>
    ''')

    with ui.column().classes('w-full h-screen gap-0 bg-[#0B0E14] overflow-hidden'):
        
        # Header Ticker Neon Estilo CoinMarketCap com Botoes Acao Fixos
        with ui.row().classes('w-full h-10 bg-[#080B10] border-b border-slate-800/80 items-center px-4 justify-between overflow-hidden relative text-xs flex-nowrap'):
            with ui.row().classes('items-center gap-2 z-10 bg-[#080B10] pr-4 border-r border-slate-800 flex-shrink-0'):
                ui.icon('token', size='sm', color='cyan-400')
                ui.label('SPOTBOT PRO').classes('font-bold tracking-wider text-white text-xs')
                ui.label('QUANTITATIVE ENGINE').classes('text-[0.55rem] font-bold text-cyan-400/80 tracking-widest')
            
            # Container do Marquee com largura controlada (max-w-[40%]) para NUNCA empurrar os botoes
            with ui.element('div').classes('w-1/3 max-w-[40%] overflow-hidden relative h-full flex items-center flex-shrink'):
                with ui.element('div').classes('animate-marquee items-center gap-8 text-[0.7rem] font-mono text-slate-300 whitespace-nowrap'):
                    ui.label('🔥 MARKET TICKER').classes('font-bold text-cyan-400')
                    ui.label('BTC: $64,340.00 (+0.37%)').classes('text-emerald-400 font-semibold')
                    ui.label('ETH: $1,873.20 (+0.81%)').classes('text-emerald-400 font-semibold')
                    ui.label('BNB: $568.49 (+0.82%)').classes('text-emerald-400 font-semibold')
                    ui.label('SOL: $74.38 (-1.44%)').classes('text-rose-400 font-semibold')
                    ui.label('XRP: $1.09 (+0.87%)').classes('text-emerald-400 font-semibold')
                    ui.label('Market Cap: $2.38T (+1.2%)').classes('text-slate-400')
                    ui.label('24h Vol: $78.4B').classes('text-slate-400')
                    
                    ui.label('🔥 MARKET TICKER').classes('font-bold text-cyan-400')
                    ui.label('BTC: $64,340.00 (+0.37%)').classes('text-emerald-400 font-semibold')
                    ui.label('ETH: $1,873.20 (+0.81%)').classes('text-emerald-400 font-semibold')
                    ui.label('BNB: $568.49 (+0.82%)').classes('text-emerald-400 font-semibold')
                    ui.label('SOL: $74.38 (-1.44%)').classes('text-rose-400 font-semibold')
                    ui.label('XRP: $1.09 (+0.87%)').classes('text-emerald-400 font-semibold')
                    ui.label('Market Cap: $2.38T (+1.2%)').classes('text-slate-400')
                    ui.label('24h Vol: $78.4B').classes('text-slate-400')

            # Botoes de Acao (START, STOP, CANCEL, LOGOUT) Fixos no Canto Superior Direito
            with ui.row().classes('items-center gap-2.5 z-10 bg-[#080B10] pl-4 border-l border-slate-800 flex-shrink-0'):
                ui.button('START', on_click=start_bot).props('unelevated dense').classes('bg-[#00F5A0] hover:bg-[#00E5FF] text-slate-950 font-bold px-3 py-1 text-xs rounded-md tracking-wider transition-all shadow-md')
                ui.button('STOP', on_click=stop_bot).props('unelevated dense').classes('bg-[#FF2E93] hover:bg-rose-600 text-white font-bold px-3 py-1 text-xs rounded-md tracking-wider transition-all shadow-md')
                ui.button('CANCEL', on_click=cancel_bot).props('unelevated dense').classes('bg-[#FFB800] hover:bg-amber-600 text-slate-950 font-bold px-3 py-1 text-xs rounded-md tracking-wider transition-all shadow-md').tooltip('Abortar Emergência (CTRL+C)')
                
                status_indicator = ui.element('div').classes('w-2.5 h-2.5 rounded-full bg-[#FF2E93] transition-all')
                
                def logout():
                    app.storage.user['authenticated'] = False
                    ui.navigate.to('/login')
                ui.button(icon='logout', on_click=logout).props('flat dense size=sm color=slate-400')

        # Layout Principal Dashboard
        with ui.row().classes('w-full flex-grow flex-nowrap gap-0 overflow-hidden'):
            
            # Painel Esquerdo de Configurações
            with ui.column().classes('w-64 h-screen border-r border-slate-800 bg-[#0E121B] p-3 gap-3 flex-shrink-0 text-slate-300'):
                with ui.column().classes('w-full gap-1'):
                    ui.label('MODO DE MONITORAMENTO').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest')
                    symbol_select = ui.select(
                        options=['⚡ SCANNER TOP 20', 'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'NEARUSDT'],
                        value='⚡ SCANNER TOP 20'
                    ).classes('w-full input-zinc bg-[#121722] rounded-lg').props('dark outlined dense')

                with ui.column().classes('w-full gap-1'):
                    ui.label('VALOR USDT POR ORDEM').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest')
                    investment_input = ui.input(value='Dinâmico (Min $10)').classes('w-full input-zinc bg-[#121722] rounded-lg').props('dark outlined dense readonly')

                with ui.column().classes('w-full gap-1'):
                    ui.label('PERFIL DE RISCO').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest')
                    risk_profile_select = ui.select(
                        options=list(RISK_PROFILES.keys()),
                        value=settings.ACTIVE_RISK_PROFILE,
                        on_change=lambda e: set_risk_profile(e.value)
                    ).classes('w-full input-zinc bg-[#121722] rounded-lg').props('dark outlined dense')

                with ui.column().classes('w-full gap-1'):
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
                     # Badge Flutuante no Canto Superior Direito indicando o Ativo em Foco Atual
                     chart_symbol_badge = ui.label('🪙 BTCUSDT').classes('absolute top-4 right-6 z-20 obsidian-card px-4 py-2 rounded-xl text-xs font-bold font-mono text-[#00E5FF] border border-cyan-500/30 backdrop-blur-md shadow-lg')

                     # Card IA Holográfico Otimizado (Posicionado levemente mais para baixo/esquerda sem cobrir o título centralizado)
                     ai_card = ui.card().classes('absolute top-4 left-4 w-72 z-20 obsidian-card p-3 rounded-2xl shadow-[0_10px_30px_rgba(0,0,0,0.5)] opacity-95 backdrop-blur-md transition-all duration-300')
                     with ai_card:
                         with ui.row().classes('w-full items-center justify-between mb-1.5'):
                             with ui.row().classes('items-center gap-2'):
                                 ai_icon_container = ui.element('div').classes('p-1 rounded-lg bg-slate-800/80 text-slate-400')
                                 with ai_icon_container: ui.icon('psychology', size='xs')
                                 ai_signal_label = ui.label('NEUTRO').classes('text-[0.7rem] font-bold tracking-wide text-slate-400')
                             
                             def toggle_ai_content():
                                 is_visible = ai_reason_scroll.visible
                                 ai_reason_scroll.set_visibility(not is_visible)
                                 toggle_btn.props(f'icon={"keyboard_arrow_down" if is_visible else "keyboard_arrow_up"}')

                             toggle_btn = ui.button(icon='keyboard_arrow_up', on_click=toggle_ai_content).props('flat dense round size=xs color=slate-400')
                         
                         ai_reason_scroll = ui.scroll_area().classes('h-24')
                         with ai_reason_scroll:
                             ai_reason_markdown = ui.markdown('_IA Gemini monitorando mercado..._').classes('text-[0.65rem] text-slate-300 leading-relaxed')

                     # ECharts com Cores Cyberpunk Neon e Título Perfeitamente Centralizado
                     with ui.element('div').classes('w-full h-full'):
                         candle_chart = ui.echart({
                            'backgroundColor': '#0B0E14',
                            'title': {
                                'text': '📈 BTCUSDT — Gráfico em Tempo Real',
                                'subtext': 'Alimentado por Binance WebSockets & Scanner 2.0 Quantitativo',
                                'left': 'center',
                                'top': 12,
                                'textStyle': {'color': '#00E5FF', 'fontSize': 14, 'fontWeight': 'bold'},
                                'subtextStyle': {'color': '#64748b', 'fontSize': 9.5}
                            },
                            'grid': [{'left': '50', 'right': '25', 'top': '65', 'height': '52%'}, {'left': '50', 'right': '25', 'top': '80%', 'height': '15%'}],
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
                          
                         log_ui = ui.log().classes('w-full h-full font-mono text-[0.65rem] bg-[#080B10] text-emerald-400 p-3 rounded-none border-none leading-tight')

        ui.timer(2.0, update_data)

def start_dashboard():
    port = DASHBOARD_CONFIG['port']
    secret = DASHBOARD_CONFIG['secret_key']
    print(f"Iniciando SpotBot Pro em modo Dashboard Web (NiceGUI)...")
    ui.run(title='SpotBot Pro | Institutional Terminal', dark=True, reload=False, port=port, storage_secret=secret)

if __name__ in {"__main__", "__mp_main__"}:
    start_dashboard()
