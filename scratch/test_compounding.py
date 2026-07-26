import sys
sys.path.insert(0, '.')
from core.decision import calculate_dynamic_position_slots

def test_compounding():
    print("Testing Snowball Compounding Slot Calculator:")
    print("---------------------------------------------")
    
    # Case 1: Initial $20 USDT balance, $0 profit
    s1, v1 = calculate_dynamic_position_slots(20.0, accumulated_net_profit=0.0)
    print(f"Initial Balance $20.00 | Profit $0.00   --> Slots: {s1} | Slot Value: ${v1:.2f}")
    
    # Case 2: $20 USDT balance + $15 accumulated profit
    s2, v2 = calculate_dynamic_position_slots(20.0, accumulated_net_profit=15.0)
    print(f"Current Balance $20.00 | Profit $15.00  --> Slots: {s2} | Slot Value: ${v2:.2f}")
    
    # Case 3: $100 USDT balance + $50 accumulated profit
    s3, v3 = calculate_dynamic_position_slots(100.0, accumulated_net_profit=50.0)
    print(f"Current Balance $100.00| Profit $50.00  --> Slots: {s3} | Slot Value: ${v3:.2f}")

if __name__ == "__main__":
    test_compounding()
