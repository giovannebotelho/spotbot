import asyncio
from binance import AsyncClient, BinanceSocketManager
from config import my_api_key, my_secret_key

async def print_balance(client, asset='BTC'):
    """Imprime o saldo atual do ativo e retorna o saldo disponível."""
    balance = await client.get_asset_balance(asset=asset)
    saldo_disponivel = float(balance['free'])
    print(f"Saldo de {asset}: {saldo_disponivel} disponível")
    return saldo_disponivel

async def monitor_price_and_place_orders(client, saldo_btc_inicial):
    """Monitora o preço e gerencia ordens de compra, venda e stop loss, incluindo a lógica de reserva de saldo."""
    bsm = BinanceSocketManager(client)
    quantia_compra = float(input("Informe a quantia de BTC que deseja comprar: "))
    preco_compra = float(input("Informe o preço de compra desejado: "))
    
    if quantia_compra > saldo_btc_inicial:
        print("Quantia desejada para compra excede o saldo disponível.")
        return

    print(f"Quantia de {quantia_compra} BTC reservada para compra, total disponível na carteira agora: {saldo_btc_inicial - quantia_compra}")
    lucro_alvo_percentual = 0.001  # +0.1%
    stop_loss_percentual = -0.003  # -0.3%

    print("Monitorando preço de BTCUSDT...")
    async with bsm.trade_socket('BTCUSDT') as ts:
        while True:
            res = await ts.recv()
            if res['e'] == 'error':
                print(res['m'])
            else:
                preco_atual = float(res['p'])
                print(f"\rPreço atual: {preco_atual:.2f} USDT", end='', flush=True)

                if preco_atual <= preco_compra:
                    print(f"\nCompra de {quantia_compra} BTC ao preço de {preco_atual:.2f} USDT com sucesso.")
                    preco_venda_alvo = preco_atual * (1 + lucro_alvo_percentual)
                    preco_stop_loss = preco_atual * (1 + stop_loss_percentual)
                    print(f"Preço alvo para venda: {preco_venda_alvo:.2f} USDT")
                    print(f"Stop loss configurado em: {preco_stop_loss:.2f} USDT")
                    break
    
    while True:
        res = await ts.recv()
        preco_atual = float(res['p'])

        if preco_atual >= preco_venda_alvo:
            print(f"\nVenda concluída com sucesso. Vendido a {preco_atual:.2f} USDT.")
            break
        elif preco_atual <= preco_stop_loss:
            print(f"\nStop loss atingido. Preço atual: {preco_atual:.2f} USDT. A ordem foi cancelada.")
            break

    await print_balance(client, 'BTC')

async def main():
    client = await AsyncClient.create(my_api_key, my_secret_key, testnet=True)
    
    saldo_btc_inicial = await print_balance(client, 'BTC')
    await monitor_price_and_place_orders(client, saldo_btc_inicial)

    await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())