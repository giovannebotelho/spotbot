"""
Ponto de entrada legado para o simulador de backtest.
Delegando para o novo módulo backtest.runner.
"""
import asyncio
from backtest.runner import run_backtest

if __name__ == "__main__":
    days_input = input("Quantos dias de histórico você quer testar? (Padrão: 30): ").strip()
    days = int(days_input) if days_input and days_input.isdigit() else 30
    asyncio.run(run_backtest(days=days))
