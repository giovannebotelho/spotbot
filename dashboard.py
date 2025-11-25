from nicegui import ui, app
import asyncio
import main
import sys
from datetime import datetime

# Redirect stdout/stderr to capture prints if needed, but we rely on callback
# main.run_bot accepts a log_callback

log_ui = None
status_ui = None
bot_task = None

def log_handler(message):
    if log_ui:
        clean_msg = remove_ansi_codes(message)
        log_ui.push(clean_msg)

def status_handler(message):
    if status_ui:
        # Format the status message nicely
        clean_msg = remove_ansi_codes(message)
        # Just bold the message, don't use H3
        status_ui.content = f"**{clean_msg}**"

def remove_ansi_codes(text):
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

async def update_balances():
    ui.notify('Atualizando saldos...')
    balances = await main.get_account_balances()
    if balances:
        bnb_val.text = f"{balances['bnb']:.4f}"
        bnb_usdt_val.text = f"~${balances['bnb_usdt']:.2f}"
        usdt_val.text = f"${balances['usdt']:.2f}"
    else:
        ui.notify('Erro ao buscar saldos.', type='negative')

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

    ui.notify('Iniciando Bot...')
    main.bot_running = True
    
    # Run the bot in the background
    bot_task = asyncio.create_task(main.run_bot(log_callback=log_handler, investment_amount=investment, selected_symbol=symbol, status_callback=status_handler))
    
    try:
        await bot_task
    except asyncio.CancelledError:
        ui.notify('Bot parado pelo usuário.', type='info')
    except Exception as e:
        ui.notify(f'Erro no bot: {e}', type='negative')
        log_handler(f"Erro crítico: {e}")

def stop_bot():
    global bot_task
    if main.bot_running:
        main.bot_running = False
        if bot_task:
            bot_task.cancel()
        ui.notify('Sinal de parada enviado.', type='info')
    else:
        ui.notify('Bot não está rodando.', type='warning')

# --- UI Layout ---

@ui.page('/')
async def index():
    global log_ui, status_ui, investment_input, symbol_select, bnb_val, bnb_usdt_val, usdt_val
    
    # Custom CSS for a darker, more professional look
    ui.add_head_html('''
        <style>
            body { background-color: #1a1a1a; color: #e0e0e0; }
            .nicegui-card { background-color: #2d2d2d; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            .status-card { background-color: #333; border-left: 5px solid #3b82f6; }
            .log-container { background-color: #000; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; }
        </style>
    ''')

    with ui.column().classes('w-full max-w-6xl mx-auto p-4 gap-6'):
        
        # Header
        with ui.row().classes('w-full items-center justify-between'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('smart_toy', size='3em', color='blue-500')
                ui.label('SpotBot Pro').classes('text-3xl font-bold text-blue-400')
            ui.badge('Online', color='green').props('outline')

        # Top Panel: Balances
        with ui.row().classes('w-full gap-4'):
            with ui.card().classes('flex-1 p-4 items-center nicegui-card'):
                ui.label('Saldo BNB').classes('text-sm text-gray-400')
                with ui.row().classes('items-baseline gap-2'):
                    bnb_val = ui.label('...').classes('text-2xl font-bold text-yellow-500')
                    bnb_usdt_val = ui.label('...').classes('text-sm text-gray-500')
            
            with ui.card().classes('flex-1 p-4 items-center nicegui-card'):
                ui.label('Saldo USDT').classes('text-sm text-gray-400')
                usdt_val = ui.label('...').classes('text-2xl font-bold text-green-500')
            
            with ui.card().classes('p-4 items-center justify-center nicegui-card cursor-pointer hover:bg-gray-700 transition-colors'):
                ui.button(icon='refresh', on_click=update_balances).props('flat round color=white')
                ui.label('Atualizar').classes('text-xs text-gray-400')

        # Control Panel
        with ui.card().classes('w-full p-6 nicegui-card'):
            ui.label('Controles de Operação').classes('text-lg font-bold mb-4 text-gray-300')
            with ui.row().classes('w-full gap-6 items-end'):
                symbol_select = ui.select(['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'XRPUSDT', 'DOTUSDT', 'LTCUSDT', 'AVAXUSDT'], label='Par de Moedas', value='BTCUSDT').classes('w-48').props('outlined dark')
                investment_input = ui.input('Investimento (USDT ou %)', value='100%').classes('w-48').props('outlined dark')
                
                with ui.row().classes('ml-auto gap-4'):
                    ui.button('INICIAR', on_click=start_bot).props('color=green-600 icon=play_arrow unelevated').classes('px-6')
                    ui.button('PARAR', on_click=stop_bot).props('color=red-600 icon=stop unelevated').classes('px-6')

        # Main Content Area (Split View)
        # Using no-wrap to prevent wrapping, and flex-grow to handle gap correctly
        with ui.row().classes('w-full gap-6 h-[600px] no-wrap items-stretch'):
            
            # Left: Live Status
            with ui.card().classes('flex-1 p-0 flex flex-col nicegui-card status-card min-w-[300px]'):
                ui.label('Monitoramento em Tempo Real').classes('p-4 text-sm font-bold text-blue-400 border-b border-gray-700 w-full')
                with ui.column().classes('p-6 flex-grow justify-center items-center text-center'):
                    # Reduced font size from text-xl to text-md/lg and removed H3 from handler
                    status_ui = ui.markdown('Aguardando início...').classes('text-lg text-gray-200')
                    ui.spinner('dots', size='lg', color='blue-500').bind_visibility_from(main, 'bot_running')

            # Right: Execution Log
            with ui.card().classes('flex-[2] p-0 flex flex-col nicegui-card min-w-[400px]'):
                with ui.row().classes('p-4 border-b border-gray-700 w-full justify-between items-center'):
                    ui.label('Logs de Execução').classes('text-sm font-bold text-green-400')
                    ui.button(icon='delete', on_click=lambda: log_ui.clear()).props('flat round dense color=gray')
                
                # Log container to ensure it stays inside
                with ui.element('div').classes('w-full flex-grow log-container relative overflow-hidden'):
                    log_ui = ui.log(max_lines=1000).classes('w-full h-full bg-black text-green-400 font-mono p-4 text-xs overflow-auto absolute top-0 left-0')

        # Footer
        with ui.row().classes('w-full justify-center mt-8'):
            ui.label(f'Feito por Giovanne Botelho | Python {sys.version.split()[0]}').classes('text-xs text-gray-600')

    # Initial balance fetch
    await update_balances()

# Run the app
ui.run(title='SpotBot Pro', dark=True, reload=False)
