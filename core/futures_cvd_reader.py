async def evaluate_cvd(client, symbol, limit=500):
    """
    Analisa os últimos negócios agredidos (AggTrades) para calcular o CVD 
    (Cumulative Volume Delta) e a agressão direcional.
    
    Retorna: (cvd_delta_usdt, buy_ratio, confirmed_direction)
    """
    try:
        agg_trades = await client.futures_aggregate_trades(symbol=symbol, limit=limit)
        if not agg_trades:
            return 0.0, 0.5, None
            
        buy_volume = 0.0
        sell_volume = 0.0
        
        for trade in agg_trades:
            price = float(trade['p'])
            qty = float(trade['q'])
            volume = price * qty
            is_buyer_maker = trade['m']
            
            # Se o comprador é o maker, a agressão (taker) foi de venda.
            if not is_buyer_maker:
                buy_volume += volume
            else:
                sell_volume += volume
                
        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return 0.0, 0.5, None
            
        cvd_delta_usdt = buy_volume - sell_volume
        buy_ratio = buy_volume / total_volume
        sell_ratio = sell_volume / total_volume
        
        confirmed_direction = None
        # Condições do Plano Mestre: Delta >= 50k e Ratio >= 60%
        if cvd_delta_usdt >= 50000 and buy_ratio >= 0.60:
            confirmed_direction = 'LONG'
        elif cvd_delta_usdt <= -50000 and sell_ratio >= 0.60:
            confirmed_direction = 'SHORT'
            
        return cvd_delta_usdt, buy_ratio, confirmed_direction
    except Exception as e:
        print(f"⚠️ Erro ao avaliar CVD de {symbol}: {e}")
        return 0.0, 0.5, None
