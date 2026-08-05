import time

_leaders_cache = {}

async def get_leader_impulse(client, symbol="BTCUSDT"):
    """
    Calcula o impulso percentual do último/atual candle de 1m.
    Usa cache de 10 segundos para não martelar a API em cada altcoin da varredura.
    """
    global _leaders_cache
    now = time.time()
    
    if symbol in _leaders_cache and now - _leaders_cache[symbol]['timestamp'] < 10:
        return _leaders_cache[symbol]['impulse']
        
    try:
        klines = await client.futures_klines(symbol=symbol, interval='1m', limit=2)
        if not klines or len(klines) < 2:
            return 0.0
            
        # Pega o candle atual (klines[-1]) ou anterior (klines[-2]) se o atual acabou de abrir
        # Para ser mais sensível, avaliamos o candle fechado mais recente ou o atual em andamento
        c1_open, c1_close = float(klines[-1][1]), float(klines[-1][4])
        
        impulse = ((c1_close - c1_open) / c1_open) * 100
        
        _leaders_cache[symbol] = {'impulse': impulse, 'timestamp': now}
        return impulse
    except Exception as e:
        print(f"⚠️ Erro ao calcular impulso de {symbol}: {e}")
        return 0.0

async def evaluate_lead_lag(client, symbol):
    """
    Avalia se o símbolo atual está 'lagging' (atrasado) em relação a um 
    forte impulso direcional do BTC ou ETH.
    
    Retorna: (is_lagging, impulse_direction)
    """
    if symbol in ["BTCUSDT", "ETHUSDT"]:
        return False, None
        
    btc_impulse = await get_leader_impulse(client, "BTCUSDT")
    eth_impulse = await get_leader_impulse(client, "ETHUSDT")
    
    # Define a direção baseada nos líderes
    impulse_direction = None
    if btc_impulse >= 0.8 or eth_impulse >= 1.0:
        impulse_direction = 'LONG'
    elif btc_impulse <= -0.8 or eth_impulse <= -1.0:
        impulse_direction = 'SHORT'
        
    if not impulse_direction:
        return False, None
        
    # Verifica o lag do altcoin
    try:
        klines = await client.futures_klines(symbol=symbol, interval='1m', limit=2)
        if not klines or len(klines) < 2:
            return False, None
            
        alt_open, alt_close = float(klines[-1][1]), float(klines[-1][4])
        alt_impulse = ((alt_close - alt_open) / alt_open) * 100
        
        is_lagging = False
        if impulse_direction == 'LONG':
            # Se BTC subiu forte, e a Altcoin subiu pouco ou até caiu (lagging)
            if alt_impulse < (btc_impulse / 1.5):
                is_lagging = True
        else: # SHORT
            # Se BTC caiu forte, e a Altcoin caiu pouco ou até subiu (lagging)
            if alt_impulse > (btc_impulse / 1.5):
                is_lagging = True
                
        return is_lagging, impulse_direction
    except Exception as e:
        print(f"⚠️ Erro ao avaliar lag de {symbol}: {e}")
        return False, None
