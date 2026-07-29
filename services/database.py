import sqlite3
import json
import pandas as pd
import warnings
from pathlib import Path
from config.settings import DATABASE_URL, BASE_DIR

warnings.filterwarnings("ignore", category=UserWarning)

_stats_cache = None
_last_stats_time = 0

class DatabaseManager:
    def __init__(self, db_url=None):
        self.db_url = db_url or DATABASE_URL
        self.is_postgres = self.db_url.startswith("postgresql://") or self.db_url.startswith("postgres://")
        self.conn = None

    def connect(self):
        if self.conn is not None:
            try:
                if not self.is_postgres:
                    return
                cursor = self.conn.cursor()
                cursor.execute("SELECT 1")
                return
            except Exception:
                self.conn = None

        if self.is_postgres:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            self.conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        else:
            if self.db_url.startswith("sqlite:///"):
                db_path = Path(self.db_url.replace("sqlite:///", ""))
            else:
                db_path = BASE_DIR / "spotbot.db"
            
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

    def close(self):
        pass

    def create_tables(self):
        self.connect()
        cursor = self.conn.cursor()
        
        pk_sql = "SERIAL PRIMARY KEY" if self.is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS trades (
            id {pk_sql},
            order_index INTEGER,
            initial_balance_usdt REAL,
            initial_invested_usdt REAL,
            symbol TEXT,
            quantity REAL,
            buy_price REAL,
            vwap REAL,
            ema_7 REAL,
            ema_15 REAL,
            ema_25 REAL,
            ema_50 REAL,
            ema_100 REAL,
            ema_200 REAL,
            buy_timestamp TEXT,
            profit_target REAL,
            stop_loss REAL,
            stop_limit REAL,
            oco_result TEXT,
            oco_timestamp TEXT,
            trade_result REAL,
            fee REAL,
            trade_result_net REAL,
            total_result_gross REAL,
            total_result_net REAL,
            final_balance_usdt REAL,
            bnb_balance_usdt REAL,
            rsi REAL,
            condition_met TEXT,
            time_interval TEXT,
            candle_open REAL,
            candle_high REAL,
            candle_low REAL,
            candle_close REAL,
            candle_variation REAL,
            candle_amplitude REAL,
            variation_24h REAL,
            candle_volume REAL,
            candle_patterns TEXT,
            macd REAL,
            signal_line REAL,
            bb_lower REAL,
            bb_middle REAL,
            bb_upper REAL,
            trend_up TEXT,
            gemini_response TEXT,
            raw_data TEXT
        )
        """
        cursor.execute(create_table_sql)
        self.conn.commit()
        self.close()

    def add_trade(self, data_row):
        self.connect()
        cursor = self.conn.cursor()
        
        def get_val(key, default=None):
            return data_row.get(key, default)

        placeholder = "%s" if self.is_postgres else "?"
        placeholders = ", ".join([placeholder] * 46)

        sql = f"""
        INSERT INTO trades (
            order_index, initial_balance_usdt, initial_invested_usdt, symbol, quantity, buy_price,
            vwap, ema_7, ema_15, ema_25, ema_50, ema_100, ema_200,
            buy_timestamp, profit_target, stop_loss, stop_limit, oco_result, oco_timestamp,
            trade_result, fee, trade_result_net, total_result_gross, total_result_net,
            final_balance_usdt, bnb_balance_usdt, rsi, condition_met, time_interval,
            candle_open, candle_high, candle_low, candle_close, candle_variation, candle_amplitude,
            variation_24h, candle_volume, candle_patterns, macd, signal_line,
            bb_lower, bb_middle, bb_upper, trend_up, gemini_response, raw_data
        ) VALUES ({placeholders})
        """
        
        values = (
            get_val("Índice da Ordem"),
            get_val("Saldo Inicial em USDT"),
            get_val("USDT Inicial Investido"),
            get_val("Símbolo"),
            get_val("Quantidade de Moeda"),
            get_val("Preço de Compra"),
            get_val("VWAP"),
            get_val("EMA 7"),
            get_val("EMA 15"),
            get_val("EMA 25"),
            get_val("EMA 50"),
            get_val("EMA 100"),
            get_val("EMA 200"),
            get_val("Data/Hora da Compra"),
            get_val("Meta de Lucro OCO"),
            get_val("Stop Loss OCO"),
            get_val("Limite de Stop OCO"),
            get_val("Resultado da Ordem OCO"),
            get_val("Data/Hora OCO"),
            get_val("Resultado Parcial da Transação"),
            get_val("Taxa"),
            get_val("Resultado Parcial da Transação Líquido"),
            get_val("Resultado Total Bruto"),
            get_val("Resultado Total Liquido"),
            get_val("Saldo Final em USDT"),
            get_val("Saldo BNB em USDT"),
            get_val("RSI da operação"),
            get_val("Condição Atendida"),
            get_val("Intervalo de tempo (Candles)"),
            get_val("Preço de Abertura (Candle)"),
            get_val("Preço Máximo (Candle)"),
            get_val("Preço Mínimo (Candle)"),
            get_val("Preço de Fechamento (Candle)"),
            get_val("Variação (Candle)"),
            get_val("Amplitude (Candle)"),
            get_val("Variação (24h)"),
            get_val("Volume (Candle)"),
            get_val("Padrões de Candle"),
            get_val("MACD"),
            get_val("Linha de Sinal"),
            get_val("Banda Inferior BB"),
            get_val("Banda Média BB"),
            get_val("Banda Superior BB"),
            str(get_val("Tendência de Alta")),
            get_val("Resposta do Gemini"),
            json.dumps(data_row, default=str)
        )
        
        cursor.execute(sql, values)
        self.conn.commit()
        self.close()

    def get_recent_trades(self, limit=20):
        try:
            self.connect()
            query = f"SELECT * FROM trades ORDER BY id DESC LIMIT {limit}"
            df = pd.read_sql_query(query, self.conn)
            self.close()
            
            if df.empty:
                return pd.DataFrame()
                
            df = df.sort_values('id', ascending=True)
            restored_rows = []
            for _, row in df.iterrows():
                raw = row.get('raw_data')
                if raw:
                    try:
                        data = json.loads(raw)
                        restored_rows.append(data)
                    except Exception:
                        pass
            
            return pd.DataFrame(restored_rows)
        except Exception:
            try:
                self.create_tables()
            except Exception:
                pass
            return pd.DataFrame()

    def get_stats(self):
        global _stats_cache, _last_stats_time
        import time
        now = time.time()
        if _stats_cache is not None and (now - _last_stats_time < 15.0):
            return _stats_cache

        try:
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM trades")
            row = cursor.fetchone()
            total_trades = row['total'] if self.is_postgres else row[0]
            
            cursor.execute("SELECT COUNT(*) as wins FROM trades WHERE oco_result = 'profit'")
            row_wins = cursor.fetchone()
            wins = row_wins['wins'] if self.is_postgres else row_wins[0]
            
            cursor.execute("SELECT SUM(trade_result_net) as net_sum FROM trades")
            row_sum = cursor.fetchone()
            result = row_sum['net_sum'] if self.is_postgres else row_sum[0]
            total_net_profit = float(result) if result is not None else 0.0
            
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            _stats_cache = {
                "total_trades": total_trades,
                "wins": wins,
                "losses": total_trades - wins,
                "win_rate": win_rate,
                "total_net_profit": total_net_profit
            }
            _last_stats_time = now
            return _stats_cache
        except Exception:
            if _stats_cache is not None:
                return _stats_cache
            return {
                "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0, "total_net_profit": 0.0
            }

    def migrate_from_csv(self, csv_path="results.csv"):
        csv_file = BASE_DIR / csv_path
        if not csv_file.exists():
            return

        try:
            df = pd.read_csv(csv_file, on_bad_lines='skip', engine='python')
            print(f"Migrando {len(df)} registros do CSV para o Banco de Dados...")
            
            for _, row in df.iterrows():
                data_row = row.to_dict()
                for k, v in data_row.items():
                    if pd.isna(v):
                        data_row[k] = None
                self.add_trade(data_row)
                
            print("Migração concluída.")
            backup_path = csv_file.with_name(f"{csv_file.stem}_backup{csv_file.suffix}")
            csv_file.rename(backup_path)
            print(f"Arquivo CSV renomeado para {backup_path}")
            
        except Exception as e:
            print(f"Erro na migração do CSV: {e}")
