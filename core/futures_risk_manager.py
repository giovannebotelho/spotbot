async def validate_trade_safety(symbol, entry_price, sl_price, initial_leverage, direction, log=print):
    """
    Verifica se a distância entre o Stop Loss e o Preço de Liquidação é segura (mínimo de 15% de buffer).
    Caso não seja, tenta reduzir a alavancagem até um nível seguro.
    Retorna a alavancagem aprovada ou 0 se rejeitado.
    """
    leverage_steps = [initial_leverage, 15, 10, 5, 3, 2, 1]
    # Remove duplicates and keep descending order
    leverage_steps = sorted(list(set(leverage_steps + [initial_leverage])), reverse=True)
    
    maintenance_margin_rate = 0.004 # Estimativa padrão conservadora na Binance (0.4%)
    
    for lev in leverage_steps:
        if lev > initial_leverage: continue
        
        # Cálculo aproximado do preço de liquidação isolada
        if direction == 'LONG':
            liq_price = entry_price * (1 - (1/lev) + maintenance_margin_rate)
            # Se a liquidação for maior que o preço de entrada (impossível em long normal, erro matemático)
            if liq_price >= entry_price:
                liq_price = entry_price * 0.99
        else: # SHORT
            liq_price = entry_price * (1 + (1/lev) - maintenance_margin_rate)
            if liq_price <= entry_price:
                liq_price = entry_price * 1.01
                
        # Calcula o espaço total do preço até a liquidação
        dist_to_liq = abs(entry_price - liq_price)
        dist_to_sl = abs(entry_price - sl_price)
        dist_sl_to_liq = abs(sl_price - liq_price)
        
        if dist_to_liq == 0:
            continue
            
        # O SL não pode ficar "espremido" contra a liquidação. Ele precisa estar antes.
        # Em LONG, o SL precisa ser MAIOR que o Liq. Em SHORT, MENOR.
        is_sl_before_liq = (sl_price > liq_price) if direction == 'LONG' else (sl_price < liq_price)
        
        buffer_ratio = dist_sl_to_liq / dist_to_liq
        
        if is_sl_before_liq and buffer_ratio >= 0.15:
            if lev != initial_leverage:
                log(f"🛡️ [RISK-BUFFER] Reduzindo alavancagem de {initial_leverage}x para {lev}x para proteger contra liquidação em {symbol}.")
            return lev
            
    log(f"⚠️ [RISK-BUFFER] Trade rejeitado em {symbol}: Preço de liquidação muito perto do Stop Loss mesmo em 1x.")
    return 0
