"""
Ponto de entrada legado para o bot no modo CLI.
Delegando para o novo módulo core.engine.
"""
import asyncio
from core.engine import run_bot

if __name__ == "__main__":
    asyncio.run(run_bot())
