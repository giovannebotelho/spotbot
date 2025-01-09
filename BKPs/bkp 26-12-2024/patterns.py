def is_hammer(candle):
    """
    Determina se um padrão de vela específico é um martelo.
    Args:
        candle (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento de uma vela.
    Returns:
        bool: True se o padrão da vela corresponder a um martelo, False caso contrário.
    Descrição:
        Um martelo é identificado por um corpo pequeno, pouca ou nenhuma sombra superior e uma sombra inferior longa.
    """
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price
    
    return candle_body <= candle_high_low * 0.3 and min(open_price, close_price) - low_price >= candle_body * 2 and high_price - max(open_price, close_price) <= candle_body * 0.1

def is_shooting_star(candle):
    """
    Determina se um padrão de vela específico é uma estrela cadente.
    Args:
        candle (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento de uma vela.
    Returns:
        bool: True se o padrão da vela corresponder a uma estrela cadente, False caso contrário.
    Descrição:
        Uma estrela cadente é identificada por um corpo pequeno, uma longa sombra superior e pouca ou nenhuma sombra inferior.
    """
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price
    
    return candle_body <= candle_high_low * 0.3 and high_price - max(open_price, close_price) >= candle_body * 2 and min(open_price, close_price) - low_price <= candle_body * 0.1

def is_bullish_engulfing(candle1, candle2):
    """
    Verifica se um padrão de engolfo de alta está presente.
    Args:
        candle1 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela anterior.
        candle2 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela atual.
    Returns:
        bool: True se o padrão de velas corresponder a um engolfo de alta, False caso contrário.
    Descrição:
        Um engolfo de alta ocorre quando a vela atual de alta engolfa completamente o corpo da vela anterior de baixa.
    """
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])

    return (close1 < open1) and (close2 > open2) and (close2 > open1) and (open2 < close1)
