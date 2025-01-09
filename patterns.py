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

def is_piercing_line(candle1, candle2):
    """
     Verifica se um padrão de linha perfurante está presente.
     Args:
        candle1 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela anterior.
        candle2 (list): Uma lista contendo preços de abertura e fechamento da vela atual.
      Returns:
        bool: True se o padrão de velas corresponder a uma linha perfurante, False caso contrário.
      Descrição:
       Um padrão perfurante é um padrão de reversão de alta formado por duas velas em que a primeira é longa de baixa, e a segunda se abre abaixo da mínima da primeira e fecha no mínimo na metade do corpo da primeira
    """
    open1, low1, close1 = float(candle1[1]), float(candle1[3]), float(candle1[4]) #tiramos high1 daqui e colocamos a low1
    open2, close2 = float(candle2[1]), float(candle2[4])

    return (close1 < open1) and (close2 > open1) and (close2 > ((open1 + close1)/2) ) and (open2 < low1) # aqui também não foi necessário trocar nada

def is_dark_cloud_cover(candle1, candle2):
    """
      Verifica se um padrão de nuvem negra está presente.
      Args:
           candle1 (list): Uma lista contendo preços de abertura e fechamento da vela anterior.
            candle2 (list): Uma lista contendo preços de abertura e fechamento da vela atual.
      Returns:
            bool: True se o padrão de velas corresponder a nuvem negra, False caso contrário.
      Descrição:
        Uma nuvem negra ocorre quando, em uma tendência de alta, o 2º candle de baixa se abre com gap de alta e fecha abaixo do ponto médio do corpo do 1º candle (de alta)
    """
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    
    return (close1 > open1) and (close2 < open2) and (open2 > close1) and (close2 < ((close1+open1) / 2 ))

def is_kicker_bullish(candle1, candle2):
     """
    Verifica se um padrão de chute de alta está presente.
    Args:
        candle1 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela anterior.
        candle2 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela atual.
    Returns:
        bool: True se o padrão de velas corresponder a um kicker de alta, False caso contrário.
    Descrição:
        Um kicker de alta ocorre quando a vela atual de alta tem um gap sobre a vela anterior de baixa.
    """
     open1, close1 = float(candle1[1]), float(candle1[4])
     open2, close2 = float(candle2[1]), float(candle2[4])

     return (close1 < open1) and (close2 > open2) and (open2 > close1)

def is_kicker_bearish(candle1, candle2):
    """
    Verifica se um padrão de chute de baixa está presente.
    Args:
        candle1 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela anterior.
        candle2 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela atual.
    Returns:
        bool: True se o padrão de velas corresponder a um kicker de baixa, False caso contrário.
    Descrição:
        Um kicker de baixa ocorre quando a vela atual de baixa tem um gap sobre a vela anterior de alta.
    """
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
     
    return (close1 > open1) and (close2 < open2) and (open2 < close1)

def is_long_day(candle):
    """
    Verifica se o padrão é de Dia longo.
    Args:
        candle (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela atual.
    Returns:
        bool: True se o padrão de velas corresponder a dia longo, False caso contrário.
    Descrição:
        Um padrão de dia longo acontece com um corpo grande, sem uma sombra relevante.
    """
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price
    
    return  candle_body >= candle_high_low * 0.7 # a altura do corpo é 70% ou maior do que a vela completa (incluindo sombras)

def is_short_day(candle):
    """
    Verifica se o padrão é de Dia curto.
    Args:
        candle (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela atual.
    Returns:
        bool: True se o padrão de velas corresponder a dia curto, False caso contrário.
    Descrição:
        Um padrão de dia curto acontece com um corpo pequeno e com poucas ou nenhuma sombras
    """
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price

    return candle_body <= candle_high_low * 0.3 # a altura do corpo é 30% ou menor do que a vela completa (incluindo sombras)
   
def is_doji(candle):
    """
    Verifica se um padrão de doji está presente.
    Args:
        candle (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela atual.
    Returns:
        bool: True se o padrão de velas corresponder a um doji, False caso contrário.
    Descrição:
        Um padrão doji acontece com um corpo nulo (preço de abertura igual ao de fechamento)
    """
    open_price, close_price = float(candle[1]), float(candle[4])
    return abs(close_price - open_price) <= 0.001  # Se a variação do candle for menor que 0.1%, irá identificar ele como doji.
   
def is_doji_dragonfly(candle):
    """
    Verifica se um padrão de doji libélula está presente.
    Args:
        candle (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento de uma vela.
    Returns:
        bool: True se o padrão de velas corresponder a um doji libélula, False caso contrário.
    Descrição:
        Um doji libélula é um candle em que a linha horizontal está no topo, e o preço de abertura, fechamento e máximo são todos iguais (ou muito proximos)
    """
    open_price, high_price, close_price = float(candle[1]), float(candle[2]), float(candle[4])
    
    return  abs(close_price - open_price) <= 0.001 and abs(open_price - high_price) <= 0.001
    
def is_doji_gravestone(candle):
    """
    Verifica se um padrão de doji lápide está presente.
    Args:
        candle (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento de uma vela.
    Returns:
        bool: True se o padrão de velas corresponder a um doji lápide, False caso contrário.
    Descrição:
        Um doji lapide é um candle em que a linha horizontal está no fundo, e o preço de abertura, fechamento e mínimo são todos iguais (ou muito próximos).
    """
    open_price, low_price, close_price = float(candle[1]), float(candle[3]), float(candle[4])
    
    return abs(close_price - open_price) <= 0.001 and abs(open_price - low_price) <= 0.001 # se a variação de open e close é 0 (doji), e se open e low são iguais também (quase sem corpo e sem linha pra baixo)

def is_doji_long_shadows(candle):
    """
    Verifica se um padrão de doji ou peão com sombra longa está presente.
    Args:
        candle (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento de uma vela.
    Returns:
        bool: True se o padrão de velas corresponder a um doji com sombras longas, False caso contrário.
    Descrição:
        Um padrão doji ou peão com sombras longas ocorre quando a vela (que pode ser um doji) tem sombras superior e inferior grandes (pelo menos, 5 vezes do tamanho do seu corpo).
    """
   
    open_price, high_price, low_price, close_price = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])
    candle_body = abs(close_price - open_price)
    candle_high_low = high_price - low_price
    
    return candle_body <= candle_high_low * 0.2 and candle_high_low >= candle_body * 5

def is_rising_three_methods(candle1, candle2, candle3, candle4, candle5):
    """
    Verifica se um padrão de alta de 3 dias (rising three methods) está presente.
    Args:
        candle1 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 1º vela.
        candle2 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 2º vela.
        candle3 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 3º vela.
        candle4 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 4º vela.
        candle5 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 5º vela.
    Returns:
         bool: True se o padrão de velas corresponder a um falling three methods, False caso contrário.
    Descrição:
        O padrão é formado por cinco candles, onde o primeiro é um grande candle de alta, três velas de baixa dentro do corpo do 1º candle, e o ultimo é um candle de alta que passa da máxima da primeira vela.
    """
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    open3, close3 = float(candle3[1]), float(candle3[4])
    open4, close4 = float(candle4[1]), float(candle4[4])
    close5 = float(candle5[4]) #aqui eu tirei o open5 já que ele é desnecessario

    if close1 <= open1:
        return False
        
    # Verifica se as três velas do meio estão dentro da amplitude da primeira e a 5 quebra a maxima da 1
    return (close1 > open1) and (open2>close1 and close2<open1) and (open3>close1 and close3<open1) and (open4>close1 and close4<open1) and (close5>close1 and close5 > open1)
    
def is_falling_three_methods(candle1, candle2, candle3, candle4, candle5):
    """
      Verifica se um padrão de baixa de 3 dias (falling three methods) está presente.
      Args:
          candle1 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 1º vela.
           candle2 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 2º vela.
           candle3 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 3º vela.
           candle4 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 4º vela.
            candle5 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 5º vela.
       Returns:
           bool: True se o padrão de velas corresponder a um falling three methods, False caso contrário.
       Descrição:
          O padrão é formado por cinco candles, onde o primeiro é um grande candle de baixa, três velas de alta dentro do corpo do 1º candle, e o ultimo é um candle de baixa que passa da mínima da primeira vela.
    """
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    open3, close3 = float(candle3[1]), float(candle3[4])
    open4, close4 = float(candle4[1]), float(candle4[4])
    close5 = float(candle5[4])  #aqui eu tirei o open5 já que ele é desnecessario

    if close1 >= open1:
      return False
         
    return (close1 < open1) and (open2<close1 and close2>open1)  and (open3<close1 and close3>open1) and (open4<close1 and close4>open1) and (close5 < close1 and close5 < open1) #verifica se o 1º candle é de baixa e a vela 5 também, quebrando o candle 1

def is_bullish_and_bearish_strike(candle1, candle2):
    """
    Verifica se um padrão de Strike está presente.
    Args:
        candle1 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela anterior.
        candle2 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da vela atual.
    Returns:
        bool: True se o padrão de velas corresponder a um strike, False caso contrário.
    Descrição:
        Um padrão de strike ocorre quando uma grande vela de direção oposta engolfa um grupo pequeno de candles opostos.
    """
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])

    return (close2 > open2 and open1>close1 and open2>open1) or (close2 < open2 and open1<close1 and open2<open1)


def is_stick_sandwich(candle1, candle2, candle3):
    """
    Verifica se um padrão de vela prensada está presente.
    Args:
        candle1 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 1º vela.
        candle2 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 2º vela.
        candle3 (list): Uma lista contendo preços de abertura, máxima, mínima e fechamento da 3º vela.
    Returns:
        bool: True se o padrão de velas corresponder a um stick sandwish, False caso contrário.
    Descrição:
        Um padrão de stick sandwich é composto por uma vela verde cercada por 2 velas vermelhas, tendo seus fechamentos mais ou menos iguais na horizontal
    """
    open1, close1 = float(candle1[1]), float(candle1[4])
    open2, close2 = float(candle2[1]), float(candle2[4])
    open3, close3 = float(candle3[1]), float(candle3[4])
      
    return (close1 < open1) and (close2 > open2) and (close3 < open3) and abs(close1-close3) <= 0.001 and close2 > close1 and close2 > close3
