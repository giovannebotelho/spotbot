import asyncio
import time

async def run_trailing_lock_monitor(client, active_futures_positions, log=print):
    """
    Monitora posições ativas de futuros a cada 1 segundo.
    Se o preço atingir 75% da meta (TP), engatilha a Trava Trailing.
    Se, após engatilhar, o preço recuar 0.25% a partir do pico, fecha a mercado.
    """
    log("🛡️ Trailing Lock Monitor iniciado...")
    while True:
        try:
            symbols_to_check = list(active_futures_positions.keys())
            if not symbols_to_check:
                await asyncio.sleep(2)
                continue
                
            # Busca o preço atual de todos os tickers de uma vez
            tickers = await client.futures_symbol_ticker()
            price_map = {t['symbol']: float(t['price']) for t in tickers}
            
            for symbol in symbols_to_check:
                if symbol not in active_futures_positions:
                    continue
                    
                pos = active_futures_positions[symbol]
                direction = pos['direction']
                entry_price = pos['entry']
                tp_price = pos['tp']
                qty = pos.get('qty', 0)
                
                cur_price = price_map.get(symbol)
                if not cur_price:
                    continue
                
                # Inicializa trackers de trailing se não existirem
                if 'trailing_active' not in pos:
                    pos['trailing_active'] = False
                    pos['peak_price'] = cur_price
                    
                # Atualiza o pico
                if direction == 'LONG':
                    if cur_price > pos['peak_price']:
                        pos['peak_price'] = cur_price
                else: # SHORT
                    if cur_price < pos['peak_price'] or pos['peak_price'] == 0:
                        pos['peak_price'] = cur_price
                        
                # Verifica distâncias
                total_target_dist = abs(tp_price - entry_price)
                if total_target_dist == 0: continue
                
                cur_dist = abs(cur_price - entry_price)
                
                # Regra: Passou de 75% da meta
                is_in_profit = (cur_price > entry_price) if direction == 'LONG' else (cur_price < entry_price)
                
                if is_in_profit and cur_dist >= (total_target_dist * 0.75):
                    if not pos['trailing_active']:
                        pos['trailing_active'] = True
                        log(f"🎯 [TRAILING-LOCK] Ativado para {symbol}! Garantindo lucro no pico.")
                        
                # Se estiver ativo, verificar recuo de 0.25%
                if pos['trailing_active']:
                    peak = pos['peak_price']
                    if direction == 'LONG':
                        drawdown_price = peak * 0.9975
                        if cur_price <= drawdown_price:
                            log(f"⚡ [TRAILING-LOCK] Recuo detectado em {symbol} (Pico: {peak:.4f}, Atual: {cur_price:.4f}). Fechando a mercado!")
                            await execute_trailing_close(client, symbol, direction, qty, log)
                            # Remove localmente para não disparar de novo
                            active_futures_positions.pop(symbol, None)
                    else: # SHORT
                        drawdown_price = peak * 1.0025
                        if cur_price >= drawdown_price:
                            log(f"⚡ [TRAILING-LOCK] Recuo detectado em {symbol} (Pico: {peak:.4f}, Atual: {cur_price:.4f}). Fechando a mercado!")
                            await execute_trailing_close(client, symbol, direction, qty, log)
                            active_futures_positions.pop(symbol, None)
                            
        except Exception as e:
            log(f"⚠️ Erro no Trailing Lock Monitor: {e}")
            
        await asyncio.sleep(1)

async def execute_trailing_close(client, symbol, direction, qty, log):
    try:
        side_exit = 'SELL' if direction == 'LONG' else 'BUY'
        
        # 1. Envia a mercado
        from core.futures_order_manager import place_futures_order
        await place_futures_order(client, symbol, side_exit, 'MARKET', qty, reduce_only=True)
        
        # 2. Cancela TP/SL antigos para evitar órfãs
        await client.futures_cancel_all_open_orders(symbol=symbol)
        
        log(f"✅ [TRAILING-LOCK] Posição de {symbol} fechada com sucesso em segurança.")
    except Exception as e:
        log(f"❌ Erro ao fechar Trailing Lock de {symbol}: {e}")
