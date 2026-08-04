def get_main_chart_options():
    return {
       'backgroundColor': '#0B0E14',
       'title': {
           'text': '📈 BTCUSDT',
           'subtext': 'Binance WebSockets & Scanner Quantitativo',
           'left': 15,
           'top': 8,
           'textStyle': {'color': '#38BDF8', 'fontSize': 13, 'fontWeight': 'bold'},
           'subtextStyle': {'color': '#64748b', 'fontSize': 9}
       },
       'grid': [{'left': '45', 'right': '15', 'top': '70', 'height': '65%'}, {'left': '45', 'right': '15', 'top': '85%', 'height': '10%'}],
       'legend': {'data': ['Preço', 'BB Upper', 'BB Lower', 'EMA 200', 'TP', 'SL', 'Entrada'], 'top': 48, 'left': 15, 'textStyle': {'color': '#94a3b8', 'fontSize': 10}},
       'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'cross'}, 'backgroundColor': 'rgba(18, 23, 34, 0.95)', 'borderColor': '#0284C7', 'textStyle': {'color': '#f8fafc'}},
       'dataZoom': [
           {'type': 'inside', 'xAxisIndex': [0, 1]},
           {'type': 'inside', 'yAxisIndex': [0]},
           {'type': 'slider', 'xAxisIndex': [0, 1], 'bottom': 3, 'height': 16, 'borderColor': '#1e293b', 'dataBackground': {'lineStyle': {'color': '#38BDF8'}, 'areaStyle': {'color': '#121722'}}}
       ],
       'xAxis': [{'type': 'category', 'data': [], 'gridIndex': 0, 'axisLine': {'lineStyle': {'color': '#334155'}}}, {'type': 'category', 'data': [], 'gridIndex': 1, 'axisLabel': {'show': False}, 'axisTick': {'show': False}, 'axisLine': {'show': False}}],
       'yAxis': [{'type': 'value', 'scale': True, 'gridIndex': 0, 'splitLine': {'lineStyle': {'color': 'rgba(255, 255, 255, 0.05)'}}, 'position': 'right'}, {'type': 'value', 'scale': True, 'gridIndex': 1, 'splitLine': {'show': False}, 'axisLabel': {'show': False}, 'axisTick': {'show': False}}],
       'series': [
           {'type': 'candlestick', 'name': 'Preço', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'itemStyle': {'color': '#10B981', 'color0': '#F43F5E', 'borderColor': '#10B981', 'borderColor0': '#F43F5E'}},
           {'name': 'BB Upper', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.4, 'color': '#F59E0B', 'width': 1.5}},
           {'name': 'BB Lower', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'opacity': 0.4, 'color': '#F59E0B', 'width': 1.5}},
           {'name': 'EMA 200', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'smooth': True, 'symbol': 'none', 'lineStyle': {'color': '#38BDF8', 'width': 2}},
           {'name': 'TP', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'symbol': 'none', 'lineStyle': {'color': '#10B981', 'type': 'dashed', 'width': 2}},
           {'name': 'SL', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'symbol': 'none', 'lineStyle': {'color': '#F43F5E', 'type': 'dashed', 'width': 2}},
           {'name': 'Entrada', 'type': 'line', 'xAxisIndex': 0, 'yAxisIndex': 0, 'data': [], 'symbol': 'none', 'lineStyle': {'color': '#38BDF8', 'type': 'dashed', 'width': 1.5}},
           {'name': 'Volume', 'type': 'bar', 'xAxisIndex': 1, 'yAxisIndex': 1, 'data': [], 'itemStyle': {'color': '#38BDF8', 'opacity': 0.25}, 'large': True}
       ]
    }
