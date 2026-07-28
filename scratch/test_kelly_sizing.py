import sys
sys.path.insert(0, '.')
from services.database import DatabaseManager
from core.decision import calculate_kelly_position_size

def test_live_kelly():
    db = DatabaseManager()
    db.create_tables()
    
    stats = db.get_stats()
    usdt_test_balance = 50.0
    
    slot_val, kelly_pct, is_active = calculate_kelly_position_size(db, usdt_test_balance, default_slot_value=20.0)
    
    print("==================================================")
    print("TESTE EM TEMPO REAL: KELLY CRITERION POSITION SIZING")
    print("==================================================")
    print(f"Etatisticas do Banco SQLite:")
    print(f"  - Total de Trades: {stats['total_trades']}")
    print(f"  - Win Rate Acumulado: {stats['win_rate']:.1f}%")
    print(f"  - Lucro Liquido Total: ${stats['total_net_profit']:.2f} USDT")
    print(f"\nResultado do Dimensionamento Matematico (Banca: ${usdt_test_balance:.2f} USDT):")
    print(f"  - Kelly Ativo: {is_active}")
    print(f"  - Alocacao Otima (Half-Kelly): {kelly_pct*100:.1f}% da banca")
    print(f"  - Tamanho do Lote Recomendado: ${slot_val:.2f} USDT")

if __name__ == "__main__":
    test_live_kelly()
