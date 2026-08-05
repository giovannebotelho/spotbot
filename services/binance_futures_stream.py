import asyncio
import traceback
from binance import BinanceSocketManager
# handle_user_data_stream_event será importado para processar os dados

async def run_futures_user_stream(client, db, log=print):
    """
    Mantém o User Data Stream vivo e responde a execuções de TP/SL.
    """
    from core.futures_order_manager import handle_user_data_stream_event
    log("🔌 Inicializando Futures User Data Stream (WebSocket Autenticado)...")
    bsm = BinanceSocketManager(client)
    
    while True:
        try:
            async with bsm.futures_user_socket() as stream:
                log("📡 Conectado ao Futures User Data Stream!")
                while True:
                    try:
                        res = await asyncio.wait_for(stream.recv(), timeout=60.0)
                        if res:
                            await handle_user_data_stream_event(client, db, res, log)
                    except asyncio.TimeoutError:
                        # Timeout normal do recv apenas para manter vivo, a conexão WebSocket cuida do PING/PONG
                        continue
        except Exception as e:
            log(f"⚠️ Erro no User Data Stream (Futuros): {e}. Tentando reconectar em 5s...")
            await asyncio.sleep(5)
