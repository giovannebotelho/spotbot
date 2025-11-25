import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from binance import AsyncClient
from config import API_KEYS, TRADING_CONFIG, RSI_CONFIG, ATR_CONFIG
from trading_functions import (
    calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_vwap,
    calculate_ema, check_trend, check_candle_patterns, calculate_atr
)
# Import decision logic (ensure decision.py has silent=True support)
from decision import should_buy, adjust_and_place_oco_order
import decision

# Mock Gemini to avoid API calls and costs
async def mock_get_gemini_analysis(*args, **kwargs):
    return None
decision.get_gemini_analysis = mock_get_gemini_analysis

# Mock client for backtesting
class MockClient:
    def __init__(self):
        pass
    
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
        return {'free': '100000.0'} # Infinite money for checks
    
    async def get_order_book(self, symbol, **kwargs):
        # This is tricky. We don't have historical order books.
        # We'll mock it using the current candle close price as the ask price.
        return {'asks': [[str(self.current_price), '1.0']]}

    def set_current_price(self, price):
        self.current_price = price

async def run_backtest(symbol='BTCUSDT', days=60, initial_capital=100.0):
    print(f"🚀 Iniciando Backtest para {symbol} nos últimos {days} dias...")
    
    client = await AsyncClient.create(api_key=API_KEYS['mainnet']['key'], api_secret=API_KEYS['mainnet']['secret'])
    
    # 1. Fetch Historical Data
    print("📥 Baixando dados históricos...")
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    klines = await client.get_historical_klines(symbol, TRADING_CONFIG['interval'], start_time.strftime("%d %b %Y %H:%M:%S"), end_time.strftime("%d %b %Y %H:%M:%S"))
    
    print(f"📊 Total de candles baixados: {len(klines)}")
    
    # 2. Simulation Loop
    balance = initial_capital
    trades = []
    active_trade = None
    
    # Need a window for indicators
    window_size = 300
    
    for i in range(window_size, len(klines)):
        # Slice klines to simulate "current time"
        current_klines = klines[i-window_size:i+1]
        current_candle = klines[i]
        
        # Parse candle data
        open_time = datetime.fromtimestamp(current_candle[0]/1000)
        open_price = float(current_candle[1])
        high_price = float(current_candle[2])
        low_price = float(current_candle[3])
        close_price = float(current_candle[4])
        volume = float(current_candle[5])
        
        # Prepare data for indicators
        closes = [float(k[4]) for k in current_klines]
        volumes = [float(k[5]) for k in current_klines]
        
        # Calculate Indicators
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
        
        # Mock Client Update
        mock_client = MockClient()
        mock_client.set_current_price(close_price)
        
        # Check Exits (if in trade)
        if active_trade:
            # Check Stop Loss
            if low_price <= active_trade['stop_loss']:
                # Stopped out
                exit_price = active_trade['stop_loss'] # Assume filled at SL
                # Slippage could be added here
                pnl = (exit_price - active_trade['entry_price']) * active_trade['quantity']
                balance += (active_trade['quantity'] * exit_price)
                
                trades.append({
                    'type': 'SELL',
                    'reason': 'STOP_LOSS',
                    'price': exit_price,
                    'time': open_time,
                    'pnl': pnl,
                    'balance': balance
                })
                active_trade = None
                continue # Next candle
            
            # Check Take Profit
            elif high_price >= active_trade['take_profit']:
                # Take Profit hit
                exit_price = active_trade['take_profit']
                pnl = (exit_price - active_trade['entry_price']) * active_trade['quantity']
                balance += (active_trade['quantity'] * exit_price)
                
                trades.append({
                    'type': 'SELL',
                    'reason': 'TAKE_PROFIT',
                    'price': exit_price,
                    'time': open_time,
                    'pnl': pnl,
                    'balance': balance
                })
                active_trade = None
                continue
                
            # Trailing Stop Logic (Simulated)
            # ... (Implement if needed, for now stick to OCO)
        
        # Check Entries (if not in trade)
        if not active_trade:
            # Calculate variations
            variation_24h = 0 # Simplified
            candle_variation = ((close_price - open_price) / open_price) * 100
            
            # Call decision logic
            try:
                decision = await should_buy(
                    rsi, trend_is_up, macd, signal, close_price, lower, middle, upper, vwap,
                    candle_patterns, open_price, high_price, low_price, close_price, volume,
                    variation_24h, candle_variation, ema7, ema15, ema25, ema50, ema100, ema200,
                    mock_client, symbol, current_klines, silent=True
                )
                
                if decision['buy']:
                    # Execute Buy
                    quantity = balance / close_price # All in
                    
                    # Calculate OCO targets using the real logic
                    # We need to mock get_order_book in mock_client to return current close_price
                    
                    _, _, _, tp, sl, _ = await adjust_and_place_oco_order(
                        mock_client, symbol, quantity, 0.01, 0.01, current_klines, silent=True
                    )
                    
                    active_trade = {
                        'entry_price': close_price,
                        'quantity': quantity,
                        'stop_loss': sl,
                        'take_profit': tp,
                        'time': open_time
                    }
                    
                    balance -= (quantity * close_price) # Deduct cash
                    
                    trades.append({
                        'type': 'BUY',
                        'price': close_price,
                        'time': open_time,
                        'sl': sl,
                        'tp': tp,
                        'reason': decision['message']
                    })
                    
            except Exception as e:
                print(f"Erro na simulação: {e}")
                pass

    await client.close_connection()
    
    # Report
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
    
    print("\n📜 Histórico de Trades:")
    for t in trades:
        if t['type'] == 'BUY':
            print(f"🟢 COMPRA em {t['time']} @ ${t['price']:.2f} | Alvo: ${t['tp']:.2f} | Stop: ${t['sl']:.2f} | Motivo: {t['reason']}")
        else:
            pnl_color = "\033[1;32m" if t['pnl'] > 0 else "\033[1;31m"
            print(f"🔴 VENDA  em {t['time']} @ ${t['price']:.2f} | PnL: {pnl_color}${t['pnl']:.2f}\033[0m | Motivo: {t['reason']}")

if __name__ == "__main__":
    try:
        days_input = input("Quantos dias de histórico você quer testar? (Padrão: 30): ").strip()
        days = int(days_input) if days_input else 30
        asyncio.run(run_backtest(days=days))
    except ValueError:
        print("Entrada inválida. Usando padrão de 30 dias.")
        asyncio.run(run_backtest(days=30))
