import numpy as np

# Definindo os parâmetros
capital_inicial = 100  # USD
lucro_por_operacao = 0.0025  # % de lucro por operação
perda_por_operacao = 0.0020  # % de perda por operação
taxa_de_acerto = 0.65  # % de acerto
operacoes_por_dia = 18 # Qtd. de operações
dias = [30, 90, 180, 365, 730]  # 1 mês, 3 meses, 6 meses, 12 meses, 24 meses.

def calcular_lucro_final(capital_inicial, lucro_por_operacao, perda_por_operacao, taxa_de_acerto, operacoes_por_dia, dias):
    resultados = {}
    for dias_no_periodo in dias:
        capital_final = capital_inicial
        for _ in range(dias_no_periodo * operacoes_por_dia):
            if np.random.random() < taxa_de_acerto:
                capital_final += capital_final * lucro_por_operacao
            else:
                capital_final -= capital_final * perda_por_operacao
        resultados[dias_no_periodo] = capital_final
    return resultados

# Calculando o lucro final
resultados = calcular_lucro_final(capital_inicial, lucro_por_operacao, perda_por_operacao, taxa_de_acerto, operacoes_por_dia, dias)

for dias, valor in resultados.items():
    valor_arredondado_real = valor * 5
    valor_arredondado_dol = "${:,.2f}".format(valor)
    valor_arredondado_real = "R${:,.2f}".format(valor_arredondado_real).replace(",", "X").replace(".", ",").replace("X", ".")
    
    print(f"{dias} dias: {valor_arredondado_dol} USDT ou {valor_arredondado_real} reais")