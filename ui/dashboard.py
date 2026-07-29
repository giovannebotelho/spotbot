import asyncio
import os
import collections
from nicegui import ui, app
import pandas as pd
from datetime import datetime

from config.settings import DASHBOARD_CONFIG, TRADING_CONFIG, RSI_CONFIG, RISK_PROFILES
import config.settings as settings
from services.database import DatabaseManager
from utils.formatting import remove_ansi_codes
import core.engine as engine

db = DatabaseManager()

# Registro de arquivos estáticos (Favicon e Logo)
assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
if os.path.exists(assets_dir):
    app.add_static_files('/assets', assets_dir)

# Buffer de Logs Global (guarda os últimos 50 logs para novos visitantes/dispositivos)
logs_buffer = collections.deque(maxlen=50)
_last_chart_sig = None
_last_trades_sig = None

log_ui = None
status_ui = None
investment_input = None
symbol_select = None
status_indicator = None

start_btn = None
stop_btn = None
cancel_btn = None

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
ai_reason_container = None

risk_profile_select = None
paper_trading_switch = None

chart_symbol_badge = None

bot_task = None

def log_handler(message):
    clean_msg = remove_ansi_codes(message)
    logs_buffer.append(clean_msg)
    if log_ui:
        try:
            log_ui.push(clean_msg)
        except Exception:
            pass

def status_handler(message):
    if status_ui:
        try:
            clean_msg = remove_ansi_codes(message)
            status_ui.content = f"**{clean_msg}**"
        except Exception:
            pass

async def update_data():
    global start_btn, stop_btn, status_indicator, _last_chart_sig
    try:
        # Sincronização de Estado dos Botões entre Dispositivos (PC / Celular)
        is_running = engine.bot_running or (bot_task is not None and not bot_task.done())
        
        if is_running:
            if start_btn:
                start_btn.props('disable')
                start_btn.classes(remove='bg-[#059669] hover:bg-[#10B981] text-white shadow-md', add='bg-slate-800 text-emerald-400 border border-emerald-500/30 opacity-90')
            if stop_btn:
                stop_btn.props(remove='disable')
                stop_btn.classes(remove='bg-slate-800 text-slate-500 opacity-50', add='bg-[#BE123C] hover:bg-rose-700 text-white shadow-lg animate-pulse')
            if status_indicator:
                status_indicator.classes(remove='bg-[#BE123C] bg-[#D97706]', add='bg-[#10B981] animate-pulse shadow-[0_0_15px_#10B981]')
        else:
            if start_btn:
                start_btn.props(remove='disable')
                start_btn.classes(remove='bg-slate-800 text-emerald-400 border border-emerald-500/30 opacity-90', add='bg-[#059669] hover:bg-[#10B981] text-white font-bold shadow-md')
            if stop_btn:
                stop_btn.props('disable')
                stop_btn.classes(remove='bg-[#BE123C] hover:bg-rose-700 text-white shadow-lg animate-pulse', add='bg-slate-800 text-slate-500 opacity-50')
            if status_indicator:
                status_indicator.classes(remove='bg-[#10B981] animate-pulse shadow-[0_0_15px_#10B981]', add='bg-[#BE123C]')

        # Consulta de Saldos e Estatísticas
        balances = await engine.get_account_balances()
        if balances:
            if bnb_val: bnb_val.text = f"{balances['bnb']:.4f}"
            if bnb_usdt_val: bnb_usdt_val.text = f"~${balances['bnb_usdt']:.2f}"
            if usdt_val: usdt_val.text = f"${balances['usdt']:.2f}"
        
        stats = await asyncio.to_thread(db.get_stats)
        if total_profit_val:
            total_profit_val.text = f"${stats['total_net_profit']:.2f}"
            total_profit_val.classes(remove='text-emerald-400 text-rose-400', add='text-[#10B981]' if stats['total_net_profit'] >= 0 else 'text-[#F43F5E]')
        if win_rate_val:
            win_rate_val.text = f"{stats['win_rate']:.1f}%"
        
        active_symbols = engine.bot_status_data.get('active_symbols', [])
        active_symbol = engine.bot_status_data.get('target_asset', 'BTCUSDT')
        current_price = engine.bot_status_data.get('price', 0.0)
        price_str = f"${current_price:.4f}" if (current_price > 0 and current_price < 1.0) else f"${current_price:.2f}"

        if chart_symbol_badge:
            if active_symbols:
                active_str = " | ".join([f"{s}" for s in active_symbols])
                chart_symbol_badge.text = f"⚡ VAGAS ATIVAS ({len(active_symbols)}/{engine.MAX_CONCURRENT_POSITIONS}): [{active_str}]"
            else:
                chart_symbol_badge.text = f"🪙 {active_symbol} ({price_str})"

        tp_price = engine.bot_status_data.get('tp_price', 0.0)
        sl_price = engine.bot_status_data.get('sl_price', 0.0)
        entry_price = engine.bot_status_data.get('entry_price', 0.0)

        market_data = engine.shared_market_data
        if market_data['dates'] and candle_chart:
            current_sig = (active_symbol, price_str, len(market_data['dates']), market_data['dates'][-1] if market_data['dates'] else '', tp_price, sl_price, entry_price)
            if current_sig != _last_chart_sig:
                _last_chart_sig = current_sig
                candle_chart.options['title'] = {
                    'text': f'📈 {active_symbol}',
                    'subtext': 'Binance WebSockets & Scanner Quantitativo',
                    'left': 15,
                    'top': 8,
                    'textStyle': {'color': '#38BDF8', 'fontSize': 13, 'fontWeight': 'bold'},
                    'subtextStyle': {'color': '#64748b', 'fontSize': 9}
                }
                candle_chart.options['xAxis'][0]['data'] = market_data['dates']
                candle_chart.options['xAxis'][1]['data'] = market_data['dates']
                candle_chart.options['series'][0]['data'] = market_data['klines']

                # Desanha as Linhas OCO ativas (TP, SL e Preço de Entrada) Estilo Binance
                mark_lines = []
                if entry_price > 0:
                    mark_lines.append({'yAxis': entry_price, 'lineStyle': {'color': '#38BDF8', 'type': 'dashed', 'width': 1.5}, 'label': {'formatter': f' Entrada: ${entry_price:.4f}', 'position': 'insideStartTop', 'color': '#38BDF8'}})
                if tp_price > 0:
                    mark_lines.append({'yAxis': tp_price, 'lineStyle': {'color': '#10B981', 'type': 'dashed', 'width': 2}, 'label': {'formatter': f'🎯 TP: ${tp_price:.4f}', 'position': 'insideEndTop', 'color': '#10B981'}})
                if sl_price > 0:
                    mark_lines.append({'yAxis': sl_price, 'lineStyle': {'color': '#F43F5E', 'type': 'dashed', 'width': 2}, 'label': {'formatter': f'🛑 SL: ${sl_price:.4f}', 'position': 'insideEndBottom', 'color': '#F43F5E'}})
                
                candle_chart.options['series'][0]['markLine'] = {'symbol': ['none', 'none'], 'data': mark_lines}

                candle_chart.options['series'][1]['data'] = market_data.get('bb_upper', [])
                candle_chart.options['series'][2]['data'] = market_data.get('bb_lower', [])
                candle_chart.options['series'][3]['data'] = market_data.get('ema200', [])
                candle_chart.options['series'][4]['data'] = market_data.get('volumes', [])
                candle_chart.update()

        await update_recent_trades_table()

        insight = engine.shared_market_data.get('gemini_insight')
        if insight and ai_signal_label and ai_reason_markdown:
            signal = insight.get('signal', 'N/A')
            ai_signal_label.text = f"{signal}"
            
            if signal == 'COMPRA':
                if ai_card: ai_card.classes(remove='border-slate-800 border-rose-500/50', add='border-emerald-500/60')
                ai_signal_label.classes(remove='text-slate-400 text-rose-400 text-amber-400', add='text-emerald-400')
            elif signal == 'VENDA':
                if ai_card: ai_card.classes(remove='border-slate-800 border-emerald-500/50', add='border-rose-500/60')
                ai_signal_label.classes(remove='text-slate-400 text-emerald-400 text-amber-400', add='text-rose-400')
            else:
                if ai_card: ai_card.classes(remove='border-emerald-500/50 border-rose-500/50', add='border-slate-800')
                ai_signal_label.classes(remove='text-slate-400 text-emerald-400 text-rose-400', add='text-amber-400')
                
            ai_reason_markdown.content = insight.get('justification', '**Sem justificativa disponível.**')

    except Exception:
        pass

async def update_recent_trades_table():
    global _last_trades_sig
    if not recent_trades_table:
        return

    trades_df = await asyncio.to_thread(db.get_recent_trades, 10)
    if trades_df.empty:
        if _last_trades_sig != 0:
            _last_trades_sig = 0
            recent_trades_table.rows = []
        return

    if 'id' in trades_df.columns:
        trades_df = trades_df.sort_values('id', ascending=False)
    
    current_sig = len(trades_df)
    if current_sig != _last_trades_sig:
        _last_trades_sig = current_sig
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
        status_indicator.classes(remove='bg-[#BE123C] bg-[#D97706]', add='bg-[#10B981] animate-pulse shadow-[0_0_15px_#10B981]')
    
    bot_task = asyncio.create_task(engine.run_bot(log_callback=log_handler, investment_amount=investment, selected_symbol=symbol, status_callback=status_handler))
    
    try:
        await bot_task
    except asyncio.CancelledError:
        try:
            ui.notify('Sistema Parado.', type='info')
        except Exception:
            pass
        if status_indicator: 
            status_indicator.classes(remove='bg-[#10B981] animate-pulse shadow-[0_0_15px_#10B981]', add='bg-[#BE123C]')
    except Exception as e:
        try:
            ui.notify(f'Erro: {e}', type='negative')
        except Exception:
            pass
        if status_indicator: 
            status_indicator.classes(remove='bg-[#10B981] animate-pulse shadow-[0_0_15px_#10B981]', add='bg-[#BE123C]')

def stop_bot():
    global bot_task
    engine.bot_running = False
    engine.bot_status_data['is_running'] = False
    if bot_task and not bot_task.done():
        bot_task.cancel()
    ui.notify('🛑 Parando Sistema com segurança...', type='info')
    if status_indicator: 
        status_indicator.classes(remove='bg-[#10B981] animate-pulse shadow-[0_0_15px_#10B981]', add='bg-[#BE123C]')

def cancel_bot():
    global bot_task
    engine.bot_running = False
    engine.bot_status_data['is_running'] = False
    if bot_task and not bot_task.done():
        bot_task.cancel()
    ui.notify('🚨 EMERGÊNCIA: Execução abortada via Cancel!', type='negative')
    if status_indicator: 
        status_indicator.classes(remove='bg-[#10B981] animate-pulse shadow-[0_0_15px_#10B981]', add='bg-[#D97706]')

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

    ui.colors(primary='#0284C7', secondary='#64748b', accent='#10B981', positive='#10B981', negative='#F43F5E', dark='#0B0E14')
    ui.add_head_html('''
        <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
        <link rel="shortcut icon" href="/assets/favicon.ico">
        <link rel="apple-touch-icon" href="/assets/logo.png">
        <style>
            body { background-color: #0B0E14; color: #f8fafc; font-family: 'Inter', sans-serif; }
            .zinc-input .q-field__native { color: white !important; }
            .zinc-input .q-field__label { color: #64748b !important; }
            .zinc-input .q-field__control:before { border-color: #1e293b !important; }
        </style>
    ''')

    with ui.column().classes('w-full h-screen items-center justify-center bg-[#0B0E14] px-4'):
        with ui.card().classes('w-full max-w-sm p-6 lg:p-8 bg-[#121722] border border-sky-500/20 shadow-[0_0_40px_rgba(2,132,199,0.1)] items-center gap-6 rounded-2xl'):
            with ui.column().classes('items-center gap-2'):
                ui.image('/assets/logo.png').classes('w-12 h-12 rounded-xl shadow-lg border border-sky-500/30')
                ui.label('SPOTBOT PRO').classes('text-2xl font-bold tracking-wider text-white')
                ui.label('INSTITUTIONAL TERMINAL').classes('text-[0.6rem] font-bold text-sky-400/70 tracking-[0.25em]')
            
            username = ui.input('Usuário').classes('w-full zinc-input').props('dark outlined dense')
            password = ui.input('Senha', password=True, password_toggle_button=True).classes('w-full zinc-input').props('dark outlined dense').on('keydown.enter', try_login)
            
            ui.button('ENTRAR NO TERMINAL', on_click=try_login).props('unelevated').classes('w-full bg-gradient-to-r from-sky-700 to-sky-600 hover:from-sky-600 hover:to-sky-500 text-white font-bold tracking-wider py-2 rounded-lg shadow-lg')

@ui.page('/')
async def index():
    if not app.storage.user.get('authenticated', False):
        return ui.navigate.to('/login')

    global log_ui, status_ui, investment_input, symbol_select, bnb_val, bnb_usdt_val, usdt_val
    global total_profit_val, win_rate_val, recent_trades_table, status_indicator, candle_chart, scanner_table
    global ai_signal_label, ai_reason_markdown, ai_reason_container, ai_card, risk_profile_select, paper_trading_switch
    global chart_symbol_badge, start_btn, stop_btn, cancel_btn
    
    ui.colors(primary='#0284C7', secondary='#64748b', accent='#10B981', positive='#10B981', negative='#F43F5E', dark='#0B0E14')
    
    ui.add_head_html('''
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
        <link rel="shortcut icon" href="/assets/favicon.ico">
        <link rel="apple-touch-icon" href="/assets/logo.png">
        <style>
            :root { --nicegui-default-padding: 0.5rem; }
            body { background-color: #0B0E14; color: #f8fafc; font-family: 'Inter', system-ui, -apple-system, sans-serif; overflow-x: hidden; }
            ::-webkit-scrollbar { width: 6px; height: 6px; }
            ::-webkit-scrollbar-track { background: #0B0E14; }
            ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
            ::-webkit-scrollbar-thumb:hover { background: #334155; }
            .obsidian-card { background: #121722; border: 1px solid rgba(255, 255, 255, 0.08); }
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

    # Container Principal Responsivo com Scroll Vertical Liberado no PC e Mobile
    with ui.row().classes('w-full min-h-screen overflow-x-hidden overflow-y-auto flex-col lg:flex-row flex-wrap lg:flex-nowrap gap-0 bg-[#0B0E14]'):
        
        # Painel Esquerdo de Configurações & Métricas
        with ui.column().classes('w-full lg:w-64 h-auto lg:h-full border-b lg:border-b-0 lg:border-r border-slate-800 bg-[#0E121B] p-3 gap-2.5 flex-shrink-0 text-slate-300 overflow-y-auto'):
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
                paper_trading_switch = ui.switch('Simulação', value=False, on_change=toggle_paper_trading).props('dense color=sky-600').classes('text-xs text-slate-400')

                ui.label('TIMEFRAME ADAPTATIVO').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest mt-1')
                ui.toggle(['Adaptativo (1h/15m)', '15m (Scalping)', '1h (Swing)'], value='Adaptativo (1h/15m)').props('unelevated dense spread size=xs color=slate-900 text-color=slate-400 toggle-color=sky-700').classes('w-full border border-slate-800 rounded-lg overflow-hidden text-[0.6rem]')

            with ui.column().classes('w-full gap-2 mt-1'):
                ui.label('PERFORMANCE').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest')
                with ui.row().classes('w-full justify-between items-center p-2 rounded-xl bg-[#121722] border border-slate-800'):
                    ui.label('Lucro Total').classes('text-xs text-slate-400')
                    total_profit_val = ui.label('$0.00').classes('font-mono text-sm font-bold text-[#10B981]')
                with ui.row().classes('w-full justify-between items-center p-2 rounded-xl bg-[#121722] border border-slate-800'):
                    ui.label('Taxa de Vitória').classes('text-xs text-slate-400')
                    win_rate_val = ui.label('0.0%').classes('font-mono text-sm font-bold text-sky-400')

            with ui.column().classes('w-full gap-1 mt-1'):
                ui.label('STATUS ATUAL').classes('text-[0.6rem] font-bold text-slate-500 tracking-widest')
                status_ui = ui.markdown('**Aguardando...**').classes('text-xs text-slate-300 leading-relaxed w-full break-words')

        # Área Principal (Direita com Scroll Vertical Habilitado)
        with ui.column().classes('w-full lg:flex-1 h-auto lg:h-full overflow-y-auto p-0 bg-[#0B0E14] flex-col gap-0 min-w-0'):
            
            # Header Ticker Neon com Botoes de Acao Sincronizados e Logo PNG
            with ui.row().classes('w-full h-10 bg-[#080B10] border-b border-slate-800 items-center px-3 justify-between flex-shrink-0 relative text-xs flex-nowrap'):
                with ui.row().classes('items-center gap-2 z-10 bg-[#080B10] pr-3 border-r border-slate-800 flex-shrink-0'):
                    ui.image('/assets/logo.png').classes('w-6 h-6 rounded-md shadow-md')
                    ui.label('SPOTBOT PRO').classes('font-bold tracking-wider text-white text-xs')
                    ui.label('QUANT').classes('text-[0.55rem] font-bold text-sky-400/80 tracking-widest hidden sm:inline')
                
                # Container do Marquee
                with ui.element('div').classes('hidden md:flex flex-1 mx-3 overflow-hidden relative h-full items-center min-w-0'):
                    with ui.element('div').classes('animate-marquee items-center gap-8 text-[0.7rem] font-mono text-slate-300 whitespace-nowrap'):
                        ui.label('🔥 MARKET TICKER').classes('font-bold text-sky-400')
                        ui.label('BTC: $64,340.00 (+0.37%)').classes('text-emerald-400 font-semibold')
                        ui.label('ETH: $1,873.20 (+0.81%)').classes('text-emerald-400 font-semibold')
                        ui.label('BNB: $568.49 (+0.82%)').classes('text-emerald-400 font-semibold')
                        ui.label('SOL: $74.38 (-1.44%)').classes('text-rose-400 font-semibold')
                        ui.label('XRP: $1.09 (+0.87%)').classes('text-emerald-400 font-semibold')
                        ui.label('Market Cap: $2.38T (+1.2%)').classes('text-slate-400')
                        ui.label('24h Vol: $78.4B').classes('text-slate-400')

                # Botoes de Acao Touch-Friendly (START, STOP, CANCEL, LOGOUT)
                with ui.row().classes('items-center gap-1.5 sm:gap-2 z-10 bg-[#080B10] ml-auto flex-shrink-0'):
                    start_btn = ui.button(on_click=start_bot).props('unelevated dense').classes('bg-[#059669] hover:bg-[#10B981] text-white font-bold px-2 sm:px-3 py-1 text-xs rounded-md tracking-wider transition-all shadow-md')
                    with start_btn:
                        ui.label('▶️').classes('text-xs')
                        ui.label('START').classes('hidden sm:inline text-xs font-bold ml-1')

                    stop_btn = ui.button(on_click=stop_bot).props('unelevated dense').classes('bg-slate-800 text-slate-500 opacity-50 font-bold px-2 sm:px-3 py-1 text-xs rounded-md tracking-wider transition-all shadow-md')
                    with stop_btn:
                        ui.label('🛑').classes('text-xs')
                        ui.label('STOP').classes('hidden sm:inline text-xs font-bold ml-1')

                    cancel_btn = ui.button(on_click=cancel_bot).props('unelevated dense').classes('bg-[#0284C7] hover:bg-sky-600 text-white font-bold px-2 sm:px-3 py-1 text-xs rounded-md tracking-wider transition-all shadow-md').tooltip('Abortar Emergência')
                    with cancel_btn:
                        ui.label('🚨').classes('text-xs')
                        ui.label('CANCEL').classes('hidden sm:inline text-xs font-bold ml-1')
                    
                    status_indicator = ui.element('div').classes('w-2.5 h-2.5 rounded-full bg-[#BE123C] transition-all')
                    
                    def logout():
                        app.storage.user['authenticated'] = False
                        ui.navigate.to('/login')
                    ui.button(icon='logout', on_click=logout).props('flat dense size=sm color=slate-400')

            # Barra Superior Estilo Binance com Botao Drawer da IA Gemini (100% Limpo Sem Sobrepor o Grafico!)
            with ui.row().classes('w-full h-8 bg-[#121722] border-b border-slate-800 px-3 items-center justify-between flex-shrink-0 z-20'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('psychology', size='xs', color='sky-400')
                    ui.label('ANÁLISE IA GEMINI:').classes('text-[0.65rem] font-bold text-slate-400 tracking-wider')
                    ai_signal_label = ui.label('NEUTRO').classes('text-[0.65rem] font-bold text-slate-400')
                
                def toggle_ai_drawer():
                    if ai_reason_container:
                        is_vis = ai_reason_container.visible
                        ai_reason_container.set_visibility(not is_vis)
                        ai_toggle_btn.text = '🧠 Ocultar IA ❮' if not is_vis else '🧠 Ver Análise IA ❯'

                ai_toggle_btn = ui.button('🧠 Ver Análise IA ❯', on_click=toggle_ai_drawer).props('flat dense size=xs color=sky-400').classes('text-[0.65rem] font-semibold')

            # Conteúdo Expansível do Painel IA Gemini
            ai_reason_container = ui.card().classes('w-full p-3 bg-[#121722] border-b border-slate-800 text-xs text-slate-300 transition-all flex-shrink-0')
            ai_reason_container.set_visibility(False)
            with ai_reason_container:
                ai_reason_markdown = ui.markdown('_IA Gemini monitorando mercado..._').classes('text-xs text-slate-300 leading-relaxed')

            # Seção Central do Gráfico (+30% de Altura Explicita)
            with ui.element('div').classes('w-full h-[470px] lg:h-[64vh] min-h-[420px] relative border-b border-slate-800 flex-shrink-0 bg-[#0B0E14]'):
                # Badge Flutuante no Canto Superior Direito
                chart_symbol_badge = ui.label('🪙 BTCUSDT').classes('absolute top-3 right-4 z-20 obsidian-card px-3 py-1 rounded-xl text-xs font-bold font-mono text-sky-400 border border-sky-500/30 backdrop-blur-md shadow-lg')

                # ECharts 100% Visível e Nítido com Titulo Alinhado a Esquerda (Sem colidir com a Badge da Direita!)
                with ui.element('div').classes('w-full h-full'):
                    candle_chart = ui.echart({
                       'backgroundColor': '#0B0E14',
                       'title': {
                           'text': '📈 BTCUSDT',
                           'subtext': 'Binance WebSockets & Scanner Quantitativo',
                           'left': 15,
                           'top': 8,
                           'textStyle': {'color': '#38BDF8', 'fontSize': 13, 'fontWeight': 'bold'},
                           'subtextStyle': {'color': '#64748b', 'fontSize': 9}
                       },
                       'grid': [{'left': '45', 'right': '15', 'top': '60', 'height': '55%'}, {'left': '45', 'right': '15', 'top': '82%', 'height': '14%'}],
                       'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'cross'}, 'backgroundColor': 'rgba(18, 23, 34, 0.95)', 'borderColor': '#0284C7', 'textStyle': {'color': '#f8fafc'}},
                       'dataZoom': [{'type': 'inside', 'xAxisIndex': [0, 1]}, {'type': 'slider', 'xAxisIndex': [0, 1], 'bottom': 3, 'height': 16, 'borderColor': '#1e293b', 'dataBackground': {'lineStyle': {'color': '#38BDF8'}, 'areaStyle': {'color': '#121722'}}}],
                       'xAxis': [{'type': 'category', 'data': [], 'gridIndex': 0, 'axisLine': {'lineStyle': {'color': '#334155'}}}, {'type': 'category', 'data': [], 'gridIndex': 1, 'axisLabel': {'show': False}, 'axisTick': {'show': False}, 'axisLine': {'show': False}}],
                       'yAxis': [{'type': 'value', 'scale': True, 'gridIndex': 0, 'splitLine': {'lineStyle': {'color': 'rgba(255, 255, 255, 0.05)'}}, 'position': 'right'}, {'type': 'value', 'scale': True, 'gridIndex': 1, 'splitLine': {'show': False}, 'axisLabel': {'show': False}, 'axisTick': {'show': False}}],
                       'series': [
                           {'type': 'candlestick', 'name': 'Preço', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'itemStyle': {'color': '#10B981', 'color0': '#F43F5E', 'borderColor': '#10B981', 'borderColor0': '#F43F5E'}},
                           {'name': 'BB Upper', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.4, 'color': '#F59E0B', 'width': 1.5}},
                           {'name': 'BB Lower', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.4, 'color': '#F59E0B', 'width': 1.5}},
                           {'name': 'EMA 200', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'color': '#38BDF8', 'width': 2}},
                           {'name': 'Volume', 'type': 'bar', 'xAxisIndex': 1, 'yAxisIndex': 1, 'data': [], 'itemStyle': {'color': '#38BDF8', 'opacity': 0.25}, 'large': True}
                       ]
                    }).classes('w-full h-full')

            # Painel Inferior (Execuções + Terminal Output Sincronizado)
            with ui.row().classes('w-full flex-shrink-0 flex-col lg:flex-row gap-0 bg-[#0B0E14] min-h-[280px]'):
                with ui.column().classes('w-full lg:w-3/5 h-64 lg:h-72 border-b lg:border-b-0 lg:border-r border-slate-800/80 bg-[#0B0E14] p-0 flex-col'):
                    with ui.row().classes('w-full h-8 items-center px-4 border-b border-slate-800 bg-[#121722]/50 justify-between flex-shrink-0'):
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

                with ui.column().classes('w-full lg:w-2/5 h-64 lg:h-72 bg-[#0B0E14] p-0 flex-col'):
                    with ui.row().classes('w-full h-8 items-center px-4 border-b border-slate-800 bg-[#121722]/50 gap-2 flex-shrink-0'):
                       ui.icon('terminal', size='xs', color='sky-400')
                       ui.label('TERMINAL OUTPUT (SINCRONIZADO)').classes('text-[0.6rem] font-bold text-slate-400 tracking-widest')
                     
                    log_ui = ui.log(max_lines=300).classes('w-full h-[calc(100%-2rem)] font-mono text-[0.65rem] bg-[#080B10] text-emerald-400 p-3 rounded-none border-none leading-tight overflow-y-auto')
                    
                    # Popula com os logs recentes sincronizados do buffer
                    for past_msg in list(logs_buffer):
                        log_ui.push(past_msg)

    ui.timer(8.0, update_data)

def start_dashboard():
    port = DASHBOARD_CONFIG['port']
    secret = DASHBOARD_CONFIG['secret_key']
    print(f"Iniciando SpotBot Pro em modo Dashboard Web (NiceGUI)...")
    ui.run(title='SpotBot Pro | Institutional Terminal', host='0.0.0.0', dark=True, reload=False, port=port, storage_secret=secret)

if __name__ in {"__main__", "__mp_main__"}:
    start_dashboard()
