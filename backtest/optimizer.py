import asyncio
import itertools
import json
from backtest.runner import run_backtest
from config.settings import RSI_CONFIG, ATR_CONFIG

async def run_optimization(days=60):
    print(f"🧪 Iniciando Otimização de Parâmetros ({days} dias)...")
    
    rsi_variations = [
        {"name": "Standard RSI", "config": RSI_CONFIG},
        {
            "name": "Conservative RSI",
            "config": {
                "levels": {0: 15, 1: 20, 2: 25, 3: 30, 4: 35, 5: 40},
                "high": 65,
                "dynamic_low": {0: 15, 1: 20, 2: 25, 3: 30, 4: 35, 5: 40},
                "min": {0: 10, 1: 15, 2: 20, 3: 25, 4: 30, 5: 35}
            }
        }
    ]
    
    atr_variations = [
        {"name": "Standard ATR (2.0/3.0)", "config": {"period": 14, "sl_multiplier": 2.0, "tp_multiplier": 3.0, "use_atr_stop": True}},
        {"name": "Tight ATR (1.5/2.0)", "config": {"period": 14, "sl_multiplier": 1.5, "tp_multiplier": 2.0, "use_atr_stop": True}},
        {"name": "Wide ATR (3.0/5.0)", "config": {"period": 14, "sl_multiplier": 3.0, "tp_multiplier": 5.0, "use_atr_stop": True}}
    ]

    ema_variations = [True, False]
    results = []
    combinations = list(itertools.product(rsi_variations, atr_variations, ema_variations))
    total_combinations = len(combinations)
    
    print(f"🔍 Testando {total_combinations} combinações...")
    
    for i, (rsi_var, atr_var, use_ema) in enumerate(combinations):
        ema_name = "EMA On" if use_ema else "EMA Off"
        print(f"\n[{i+1}/{total_combinations}] Testando: {rsi_var['name']} + {atr_var['name']} + {ema_name}")
        
        config_override = {
            "RSI_CONFIG": rsi_var['config'],
            "ATR_CONFIG": atr_var['config'],
            "TRADING_CONFIG": {"use_ema_filter": use_ema}
        }
        
        try:
            result = await run_backtest(days=days, initial_capital=100.0, config_override=config_override)
            results.append({
                "rsi_name": rsi_var['name'],
                "atr_name": atr_var['name'],
                "ema_status": ema_name,
                "profit": result['profit'],
                "profit_percent": result['profit_percent'],
                "trades": result['trades'],
                "final_balance": result['final_balance']
            })
        except Exception as e:
            print(f"❌ Erro na combinação {i+1}: {e}")
            
    results.sort(key=lambda x: x['profit'], reverse=True)
    
    print("\n" + "="*60)
    print("🏆 RESULTADOS DA OTIMIZAÇÃO")
    print("="*60)
    
    for res in results:
        color = "\033[1;32m" if res['profit'] > 0 else "\033[1;31m"
        print(f"{res['rsi_name']:<20} | {res['atr_name']:<20} | {res['ema_status']:<8} | {color}{res['profit_percent']:6.2f}%\033[0m | {res['trades']:<6}")

    best = results[0]
    print(f"\n✅ Melhor Configuração: {best['rsi_name']} + {best['atr_name']} + {best['ema_status']} (Lucro: {best['profit_percent']:.2f}%)")
    
    with open("optimization_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print("💾 Resultados salvos em optimization_results.json")

if __name__ == "__main__":
    days_input = input("Quantos dias de histórico você quer testar? (Padrão: 60): ").strip()
    days = int(days_input) if days_input and days_input.isdigit() else 60
    asyncio.run(run_optimization(days=days))
