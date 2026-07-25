import asyncio
from datetime import datetime, timedelta
from binance import AsyncClient
from config.settings import API_KEYS, TRADING_CONFIG
from core.indicators import (
    calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_vwap,
    calculate_ema, check_trend, check_candle_patterns
)
from core.decision import should_buy, adjust_and_place_oco_order
import core.decision as decision

async def mock_get_gemini_analysis(*args, **kwargs):
    return None
decision.get_gemini_analysis = mock_get_gemini_analysis

class MockClient:
    def __init__(self, current_price=100.0):
        self.current_price = current_price
    
    async def get_symbol_info(self, symbol):
        return {
            'baseAsset': 'BTC',
            'filters': [
                {'filterType': 'LOT_SIZE', 'stepSize': '0.00001', 'minQty': '0.00001'},
                {'filterType': 'NOTIONAL', 'minNotional': '5.0'},
                {'filterType': 'MIN_NOTIONAL', 'minNotional': '5.0'}
            ]
        }
    
    async def get_asset_balance(self, asset):
        return {'free': '100000.0'}
    
    async def get_order_book(self, symbol, **kwargs):
        return {'asks': [[str(self.current_price), '1.0']]}

    def set_current_price(self, price):
        self.current_price = price

async def run_backtest(symbol='BTCUSDT', days=30, initial_capital=100.0, config_override=None):
    print(f"🚀 Iniciando Backtest para {symbol} nos últimos {days} dias...")
    
    api_k = API_KEYS['mainnet']['key']
    api_s = API_KEYS['mainnet']['secret']
    client = await AsyncClient.create(api_key=api_k, api_secret=api_s)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    klines = await client.get_historical_klines(symbol, TRADING_CONFIG['interval'], start_time.strftime("%d %b %Y %H:%M:%S"), end_time.strftime("%d %b %Y %H:%M:%S"))
    print(f"📊 Total de candles baixados: {len(klines)}")
    
    balance = initial_capital
    trades = []
    active_trade = None
    window_size = 300
    
    for i in range(window_size, len(klines)):
        current_klines = klines[i-window_size:i+1]
        current_candle = klines[i]
        
        open_time = datetime.fromtimestamp(current_candle[0]/1000)
        open_price = float(current_candle[1])
        high_price = float(current_candle[2])
        low_price = float(current_candle[3])
        close_price = float(current_candle[4])
        volume = float(current_candle[5])
        
        closes = [float(k[4]) for k in current_klines]
        volumes = [float(k[5]) for k in current_klines]
        
        rsi = calculate_rsi(closes)
        macd, signal = calculate_macd(closes)
        lower, middle, upper = calculate_bollinger_bands(closes)
        vwap = calculate_vwap(closes, volumes)
        ema7 = calculate_ema(closes, 7)
        ema15 = calculate_ema(closes, 15)
        ema25 = calculate_ema(closes, 25)
        ema50 = calculate_ema(closes, 50)
        ema100 = calculate_ema(closes, 100)
        ema200 = calculate_ema(closes, 200)
        trend_is_up = check_trend(current_klines)
        candle_patterns = check_candle_patterns(current_klines)
        
        mock_client = MockClient(current_price=close_price)
        
        if active_trade:
            if low_price <= active_trade['stop_loss']:
                exit_price = active_trade['stop_loss']
                pnl = (exit_price - active_trade['entry_price']) * active_trade['quantity']
                balance += (active_trade['quantity'] * exit_price)
                trades.append({'type': 'SELL', 'reason': 'STOP_LOSS', 'price': exit_price, 'time': open_time, 'pnl': pnl, 'balance': balance})
                active_trade = None
                continue
            elif high_price >= active_trade['take_profit']:
                exit_price = active_trade['take_profit']
                pnl = (exit_price - active_trade['entry_price']) * active_trade['quantity']
                balance += (active_trade['quantity'] * exit_price)
                trades.append({'type': 'SELL', 'reason': 'TAKE_PROFIT', 'price': exit_price, 'time': open_time, 'pnl': pnl, 'balance': balance})
                active_trade = None
                continue
        
        if not active_trade:
            candle_variation = ((close_price - open_price) / open_price) * 100
            try:
                dec = await should_buy(
                    rsi, trend_is_up, macd, signal, close_price, lower, middle, upper, vwap,
                    candle_patterns, open_price, high_price, low_price, close_price, volume,
                    0, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200,
                    mock_client, symbol, current_klines, silent=True, config_override=config_override
                )
                
                if dec['buy']:
                    quantity = balance / close_price
                    _, _, _, tp, sl, _ = await adjust_and_place_oco_order(
                        mock_client, symbol, quantity, 0.01, 0.01, current_klines, silent=True, config_override=config_override
                    )
                    active_trade = {'entry_price': close_price, 'quantity': quantity, 'stop_loss': sl, 'take_profit': tp, 'time': open_time}
                    balance -= (quantity * close_price)
                    trades.append({'type': 'BUY', 'price': close_price, 'time': open_time, 'sl': sl, 'tp': tp, 'reason': dec['message']})
            except Exception:
                pass

    await client.close_connection()
    
    print("\n" + "="*30)
    print("🏁 RESULTADO DO BACKTEST")
    print("="*30)
    print(f"Saldo Inicial: ${initial_capital:.2f}")
    print(f"Saldo Final:   ${balance:.2f}")
    profit = balance - initial_capital
    profit_percent = (profit / initial_capital) * 100
    color = "\033[1;32m" if profit > 0 else "\033[1;31m"
    print(f"Lucro/Prejuízo: {color}${profit:.2f} ({profit_percent:.2f}%)\033[0m")
    print(f"Total de Trades: {len([t for t in trades if t['type'] == 'BUY'])}")
    
    return {
        "profit": profit,
        "profit_percent": profit_percent,
        "trades": len([t for t in trades if t['type'] == 'BUY']),
        "final_balance": balance
    }
