import asyncio
import itertools
import json
from backtest import run_backtest
from config import RSI_CONFIG, ATR_CONFIG, OCO_CONFIG

async def run_optimization(days=60):
    print(f"🧪 Iniciando Otimização de Parâmetros ({days} dias)...")
    
    # Define Grid Search Space
    # We will test combinations of:
    # 1. RSI Levels (Standard vs Conservative)
    # 2. ATR Multipliers (Standard vs Tight vs Wide)
    
    rsi_variations = [
        {
            "name": "Standard RSI",
            "config": RSI_CONFIG # Default
        },
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
        {
            "name": "Standard ATR (2.0/3.0)",
            "config": {"period": 14, "sl_multiplier": 2.0, "tp_multiplier": 3.0, "use_atr_stop": True}
        },
        {
            "name": "Tight ATR (1.5/2.0)",
            "config": {"period": 14, "sl_multiplier": 1.5, "tp_multiplier": 2.0, "use_atr_stop": True}
        },
        {
            "name": "Wide ATR (3.0/5.0)",
            "config": {"period": 14, "sl_multiplier": 3.0, "tp_multiplier": 5.0, "use_atr_stop": True}
        }
    ]
    
    results = []
    
    combinations = list(itertools.product(rsi_variations, atr_variations))
    total_combinations = len(combinations)
    
    print(f"🔍 Testando {total_combinations} combinações...")
    
    for i, (rsi_var, atr_var) in enumerate(combinations):
        print(f"\n[{i+1}/{total_combinations}] Testando: {rsi_var['name']} + {atr_var['name']}")
        
        # Construct config override
        config_override = {
            "RSI_CONFIG": rsi_var['config'],
            "ATR_CONFIG": atr_var['config'],
            # Keep OCO default for now, or add to grid
        }
        
        try:
            # Run backtest (suppress output to keep it clean, or redirect)
            # We can't easily suppress print from imported module without redirecting stdout
            # For now, let it print, user can see progress
            result = await run_backtest(days=days, initial_capital=100.0, config_override=config_override)
            
            results.append({
                "rsi_name": rsi_var['name'],
                "atr_name": atr_var['name'],
                "profit": result['profit'],
                "profit_percent": result['profit_percent'],
                "trades": result['trades'],
                "final_balance": result['final_balance']
            })
            
        except Exception as e:
            print(f"❌ Erro na combinação {i+1}: {e}")
            
    # Sort results by profit
    results.sort(key=lambda x: x['profit'], reverse=True)
    
    print("\n" + "="*50)
    print("🏆 RESULTADOS DA OTIMIZAÇÃO")
    print("="*50)
    
    print(f"{'RSI':<20} | {'ATR':<20} | {'Lucro %':<10} | {'Trades':<6}")
    print("-" * 65)
    
    for res in results:
        color = "\033[1;32m" if res['profit'] > 0 else "\033[1;31m"
        print(f"{res['rsi_name']:<20} | {res['atr_name']:<20} | {color}{res['profit_percent']:6.2f}%\033[0m | {res['trades']:<6}")

    best = results[0]
    print(f"\n✅ Melhor Configuração: {best['rsi_name']} + {best['atr_name']} (Lucro: {best['profit_percent']:.2f}%)")
    
    # Save to file
    with open("optimization_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print("💾 Resultados salvos em optimization_results.json")

if __name__ == "__main__":
    try:
        days_input = input("Quantos dias de histórico você quer testar? (Padrão: 60): ").strip()
        days = int(days_input) if days_input else 60
        asyncio.run(run_optimization(days=days))
    except ValueError:
        print("Entrada inválida. Usando padrão de 60 dias.")
        asyncio.run(run_optimization(days=60))
