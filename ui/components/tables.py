def get_recent_trades_columns():
    return [
       {'name': 'date', 'label': 'Horário', 'field': 'date', 'align': 'left'},
       {'name': 'pair', 'label': 'Par', 'field': 'pair', 'align': 'left'},
       {'name': 'market', 'label': 'Mercado', 'field': 'market', 'align': 'center'},
       {'name': 'type', 'label': 'Direção', 'field': 'type', 'align': 'center'},
       {'name': 'pnl', 'label': 'PnL Líquido', 'field': 'pnl', 'align': 'right'},
    ]
