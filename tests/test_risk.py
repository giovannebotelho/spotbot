import pytest
import math
from core.decision import calculate_kelly_position_size
from services.database import DatabaseManager
import os

class MockDB:
    def __init__(self, win_rate, total_trades, avg_win, avg_loss):
        self.stats = {
            'win_rate': win_rate,
            'total_trades': total_trades,
            'average_win': avg_win,
            'average_loss': avg_loss
        }
    def get_stats(self):
        return self.stats

def test_calculate_kelly_position_size():
    # 60% win rate, win/loss ratio 1.5
    # Kelly = W - ((1 - W) / R)
    # W = 0.60
    # R = 1.5
    # Kelly = 0.60 - (0.40 / 1.5) = 0.60 - 0.2666 = 0.3333 (33.33% total kelly)
    # Half-Kelly = 16.66%
    
    mock_db = MockDB(win_rate=60.0, total_trades=100, avg_win=1.5, avg_loss=-1.0)
    usdt_balance = 1000.0
    default_slot = 100.0 # 10%
    
    k_val, k_pct, is_active = calculate_kelly_position_size(mock_db, usdt_balance, default_slot_value=default_slot)
    
    # Kelly should be positive, so is_active is True
    assert is_active == True
    # Half Kelly calculation from the function should cap at certain values or return the exact percentage.
    # The function caps max position to 25% of the balance
    assert k_pct > 0.0
    assert k_val <= usdt_balance * 0.25
    
def test_calculate_kelly_negative():
    # Win rate 30%, b=2.0
    # p = 0.3, q = 0.7, b = 2.0
    # f_kelly = (0.3 * 2.0 - 0.7) / 2.0 = -0.05
    # half_kelly = max(0.10, min(0.40, -0.025)) = 0.10
    mock_db = MockDB(win_rate=30.0, total_trades=100, avg_win=0.5, avg_loss=-1.0)
    usdt_balance = 1000.0
    
    k_val, k_pct, is_active = calculate_kelly_position_size(mock_db, usdt_balance, default_slot_value=100.0)
    
    # Kelly should be capped at 0.10 minimum
    assert is_active == True
    assert k_pct == 0.10
    assert k_val == 100.0 # 1000 * 0.10
