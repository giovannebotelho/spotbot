from database import DatabaseManager
import pandas as pd
from pathlib import Path

# Create a dummy CSV if it doesn't exist
csv_path = Path("results.csv")
if not csv_path.exists():
    print("Creating dummy CSV...")
    df = pd.DataFrame([{
        "Índice da Ordem": 1,
        "Símbolo": "BTCUSDT",
        "Preço de Compra": 50000.0,
        "Resultado da Ordem OCO": "profit",
        "Tendência de Alta": True
    }])
    df.to_csv(csv_path, index=False)

print("Initializing DB...")
db = DatabaseManager("test_spotbot.db")
db.create_tables()

print("Migrating...")
db.migrate_from_csv("results.csv")

print("Checking DB content...")
trades = db.get_recent_trades()
print(trades)

if not trades.empty:
    print("Migration SUCCESS!")
else:
    print("Migration FAILED!")

# Clean up
if Path("test_spotbot.db").exists():
    Path("test_spotbot.db").unlink()
# Don't delete results.csv as it might be the real one or the backup
