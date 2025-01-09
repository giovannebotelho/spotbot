import asyncio
import math  # Importando math para cálculos
from binance import AsyncClient, BinanceSocketManager

from config import real_api_key, real_secret_key

async def print_balance(client, asset='USDT'):
    balance = await client.get_asset_balance(asset=asset)
    saldo_disponivel = float(balance['free'])
    print(f"Saldo de {asset}: {saldo_disponivel} disponível")
    return saldo_disponivel

async def adjust_quantity_based_on_lot_size(client, symbol, quantity, side):
    info = await client.get_symbol_info(symbol)
    for filter in info['filters']:
        if filter['filterType'] == 'LOT_SIZE':
            step_size = float(filter['stepSize'])
            quantity = math.floor(quantity / step_size) * step_size
            break
    if side.upper() == 'SELL':
        return quantity  # Ajuste necessário somente para vendas
    # Para compras, a quantidade é tratada em USDT e não precisa de ajuste aqui
    return quantity

async def place_order_async(client, symbol, quantity, side):
    try:
        if side.upper() == 'BUY':
            # Utiliza 'quoteOrderQty' para especificar a quantia em USDT para a compra
            order = await client.order_market_buy(symbol=symbol, quoteOrderQty=quantity)
        elif side.upper() == 'SELL':
            # Para vendas, ajusta a quantidade de BTC com base no LOT_SIZE
            quantity_adjusted = await adjust_quantity_based_on_lot_size(client, symbol, quantity, side)
            order = await client.order_market_sell(symbol=symbol, quantity=quantity_adjusted)
        print(f"Ordem {side} executada: {order}")
    except Exception as e:
        print(f"Erro ao executar {side}: {e}")

async def monitor_price_and_decide(client, saldo_usdt_inicial):
    bsm = BinanceSocketManager(client)
    preco_compra_desejado = float(input("Informe o preço de compra desejado para BTC/USDT: "))
    quantia_usdt_para_compra = float(input(f"Informe a quantia de USDT que deseja usar para comprar BTC (Saldo disponível: {saldo_usdt_inicial} USDT): "))

    lucro_alvo_percentual = 0.001  # 0.02%
    stop_loss_percentual = -0.001  # -0.02%

    async with bsm.trade_socket('BTCUSDT') as ts:
        while True:
            res = await ts.recv()
            if res['e'] == 'error':
                print(res['m'])
            elif 'p' in res:
                preco_atual = float(res['p'])
                print(f"\rPreço atual de BTC/USDT: {preco_atual:.2f}", end='', flush=True)
                
                # Verifica se o preço atual atende ao preço desejado e se a quantia de USDT atende ao mínimo
                if preco_atual <= preco_compra_desejado and quantia_usdt_para_compra >= 10:  # Assumindo 10 USD como mínimo
                    quantia_btc_para_compra = quantia_usdt_para_compra / preco_atual
                    # Inclua aqui a lógica para ajustar a quantia_btc_para_compra conforme necessário
                    await place_order_async(client, 'BTCUSDT', quantia_usdt_para_compra, 'BUY')
                    preco_venda_alvo = preco_atual * (1 + lucro_alvo_percentual)
                    preco_stop_loss = preco_atual * (1 + stop_loss_percentual)
                    print(f"\nCompra realizada com sucesso. Preço de compra: {preco_atual:.2f} USDT")
                    print(f"Preço alvo para venda: {preco_venda_alvo:.2f} USDT")
                    print(f"Stop loss configurado em: {preco_stop_loss:.2f} USDT")
                    break
            else:
                print("Dados incompletos recebidos, aguardando próxima atualização.")

    # Monitorar preço para venda ou stop loss
    while True:
        res = await ts.recv()
        preco_atual = float(res['p'])
        
        if preco_atual >= preco_venda_alvo:
            # Calcula a quantidade de BTC a ser vendida, baseada na compra anterior
            await place_order_async(client, 'BTCUSDT', quantia_btc_para_compra, 'SELL')
            print(f"\nVenda concluída com sucesso. Vendido a {preco_atual:.2f} USDT.")
            break
        elif preco_atual <= preco_stop_loss:
            # Executa a venda em caso de atingir o stop loss, usando a quantidade de BTC comprada anteriormente
            await place_order_async(client, 'BTCUSDT', quantia_btc_para_compra, 'SELL')
            print(f"\nStop loss atingido. Vendido a {preco_atual:.2f} USDT.")
            break

async def main():
    client = await AsyncClient.create(real_api_key, real_secret_key, testnet=False)
    saldo_usdt_inicial = await print_balance(client, 'USDT')
    await monitor_price_and_decide(client, saldo_usdt_inicial)
    await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())