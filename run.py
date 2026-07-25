import argparse
import sys
import os
from pathlib import Path

# Garante suporte UTF-8 no console do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Adiciona a raiz do repositório ao PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DASHBOARD_CONFIG

def main():
    parser = argparse.ArgumentParser(description="SpotBot Pro - Assistente de Trading Spot Binance com IA Gemini")
    parser.add_argument(
        "--mode",
        choices=["dashboard", "cli", "backtest"],
        default="dashboard",
        help="Modo de execução do bot: 'dashboard' (Interface Web), 'cli' (Terminal puro), 'backtest' (Simulador)"
    )
    parser.add_argument("--days", type=int, default=30, help="Número de dias para o modo backtest")

    args = parser.parse_args()

    if args.mode == "dashboard":
        print("Iniciando SpotBot Pro em modo Dashboard Web (NiceGUI)...")
        from ui.dashboard import start_dashboard
        start_dashboard()
    
    elif args.mode == "cli":
        print("Iniciando SpotBot Pro em modo Terminal CLI...")
        from core.engine import run_bot
        asyncio.run(run_bot())

    elif args.mode == "backtest":
        print(f"Iniciando Simulação de Backtest para os últimos {args.days} dias...")
        from backtest.runner import run_backtest
        asyncio.run(run_backtest(days=args.days))

if __name__ == "__main__":
    main()
