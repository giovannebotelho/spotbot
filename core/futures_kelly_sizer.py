async def calculate_optimal_margin(db, total_balance_usdt, log=print):
    """
    Calcula a alocação de margem ótima usando o Critério de Kelly (Half-Kelly).
    Limite máximo de 10% da banca.
    """
    if not db or total_balance_usdt <= 0:
        return 20.0 # Default mínimo
        
    try:
        # Busca estatísticas reais de Futuros
        trades = db.get_recent_trades(limit=100) # Assumindo que db.get_recent_trades retorna os ultimos 100
        
        # Filtra apenas os trades do tipo FUTURES
        futures_trades = [t for t in trades if isinstance(t, dict) and t.get('market_type') == 'FUTURES']
        
        if len(futures_trades) < 10:
            # Sem histórico suficiente, usa 2% da banca conservadoramente
            allocation = total_balance_usdt * 0.02
            return min(max(allocation, 20.0), total_balance_usdt * 0.10)
            
        wins = [float(t.get('total_result_net', 0)) for t in futures_trades if float(t.get('total_result_net', 0)) > 0]
        losses = [abs(float(t.get('total_result_net', 0))) for t in futures_trades if float(t.get('total_result_net', 0)) <= 0]
        
        W = len(wins) / len(futures_trades)
        L = 1 - W
        
        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss = (sum(losses) / len(losses)) if losses else 0.0
        
        if avg_loss == 0:
            # Se não há perdas, aloca o máximo permitido (10%)
            f_half = 0.10
        else:
            R = avg_win / avg_loss
            if R == 0:
                f_star = 0
            else:
                f_star = (W * R - L) / R
            
            f_half = f_star / 2.0
            
        # Proteções contra over-betting (Kelly sugere no máximo 10% para nossa gestão de risco)
        optimal_pct = min(max(f_half, 0.01), 0.10) # Entre 1% e 10%
        
        margin_usdt = total_balance_usdt * optimal_pct
        
        # Garante o mínimo de 20 USDT se a banca permitir
        margin_usdt = max(margin_usdt, 20.0) if total_balance_usdt >= 20.0 else total_balance_usdt
        
        log(f"📊 [KELLY-SIZING] W: {W*100:.1f}%, R: {avg_win/avg_loss if avg_loss else 0:.2f}. Alocando {optimal_pct*100:.1f}% da banca (${margin_usdt:.2f}).")
        return margin_usdt
        
    except Exception as e:
        log(f"⚠️ Erro ao calcular Kelly Criterion: {e}. Usando fallback 2%.")
        allocation = total_balance_usdt * 0.02
        return min(max(allocation, 20.0), total_balance_usdt * 0.10)
