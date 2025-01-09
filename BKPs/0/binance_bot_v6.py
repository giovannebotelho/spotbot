import asyncio
import math
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from config import my_api_key, my_secret_key

api_key = my_api_key
api_secret = my_secret_key

async def main():
    client = await AsyncClient.create(api_key, api_secret, testnet=True)
    symbol = 'BTCUSDT'
    
    # Obter informações do símbolo para extrair o filtro de preço
    symbol_info = await client.get_symbol_info(symbol)
    price_filter = next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'PRICE_FILTER')
    tick_size = float(price_filter['tickSize'])
    
    def adjust_price_to_tick_size(price, tick_size):
        """Ajusta o preço para estar em conformidade com o tick size do filtro de preço."""
        return math.floor(price / tick_size) * tick_size
    
    try:
        saldo_usdt_inicial = float((await client.get_asset_balance(asset='USDT'))['free'])
        print(f"Saldo inicial em USDT: {saldo_usdt_inicial}")
        
        quantia_usdt_para_compra = float(input("Quantia de USDT para investir: "))
        if quantia_usdt_para_compra > saldo_usdt_inicial:
            print("Saldo insuficiente.")
            return

        # Realizar compra a mercado
        compra = await client.order_market_buy(symbol=symbol, quoteOrderQty=quantia_usdt_para_compra)
        executed_qty = float(compra['executedQty'])
        print(f"Compra realizada: symbol: {symbol}, executedQty: {executed_qty}, price: {compra['fills'][0]['price']}")

        # Calcular preço alvo de venda e stop loss
        preco_compra = float(compra['fills'][0]['price'])
        lucro_alvo_percentual = 0.003
        stop_loss_percentual = 0.003

        # Ajustar os preços de acordo com o tick size
        lucro_alvo = adjust_price_to_tick_size(preco_compra * (1 + lucro_alvo_percentual), tick_size)
        stop_loss = adjust_price_to_tick_size(preco_compra * (1 - stop_loss_percentual), tick_size)
        stop_limit_price = adjust_price_to_tick_size(stop_loss, tick_size)  # Ajuste conforme necessário

        # Para vender 100% do BTC, usaremos a quantia executada da compra
        try:
            oco_order = await client.create_oco_order(
                symbol=symbol,
                side="SELL",
                quantity="{:.8f}".format(executed_qty),
                price="{:.8f}".format(lucro_alvo),
                stopPrice="{:.8f}".format(stop_loss),
                stopLimitPrice="{:.8f}".format(stop_limit_price),  # Ajuste conforme necessário
                stopLimitTimeInForce='GTC'
            )
            print(f"Ordem OCO enviada - Preço de lucro alvo: {lucro_alvo:.2f} USDT, Preço de stop loss: {stop_loss:.2f} USDT")
        except BinanceAPIException as e:
            print(e)

        # Aqui você pode adicionar a lógica para ajustar a quantia_usdt_para_compra com base no resultado da operação anterior
        # e repetir o processo de compra e venda em um loop.

    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())