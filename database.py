import sqlite3
import pandas as pd
from pathlib import Path
import json

class DatabaseManager:
    def __init__(self, db_name="spotbot.db"):
        self.db_path = Path(__file__).parent / db_name
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()

    def create_tables(self):
        self.connect()
        cursor = self.conn.cursor()
        
        # Schema based on post_trade.py columns
        # Using flexible schema where possible, but defining core columns
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            raw_data TEXT  -- Store full JSON of the row for future proofing
        )
        """
        cursor.execute(create_table_sql)
        self.conn.commit()
        self.close()

    def add_trade(self, data_row):
        self.connect()
        cursor = self.conn.cursor()
        
        # Map data_row keys to DB columns
        # This mapping needs to be maintained
        
        # Helper to safely get value
        def get_val(key, default=None):
            return data_row.get(key, default)

        sql = """
        INSERT INTO trades (
            order_index, initial_balance_usdt, initial_invested_usdt, symbol, quantity, buy_price,
            vwap, ema_7, ema_15, ema_25, ema_50, ema_100, ema_200,
            buy_timestamp, profit_target, stop_loss, stop_limit, oco_result, oco_timestamp,
            trade_result, fee, trade_result_net, total_result_gross, total_result_net,
            final_balance_usdt, bnb_balance_usdt, rsi, condition_met, time_interval,
            candle_open, candle_high, candle_low, candle_close, candle_variation, candle_amplitude,
            variation_24h, candle_volume, candle_patterns, macd, signal_line,
            bb_lower, bb_middle, bb_upper, trend_up, gemini_response, raw_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(data_row, default=str) # Store full raw data
        )
        
        cursor.execute(sql, values)
        self.conn.commit()
        self.close()

    def get_recent_trades(self, limit=20):
        self.connect()
        query = f"SELECT * FROM trades ORDER BY id DESC LIMIT {limit}"
        df = pd.read_sql_query(query, self.conn)
        self.close()
        
        # We need to reconstruct the DataFrame to match what decision.py expects (CSV headers)
        # We can parse the 'raw_data' JSON column to get back the exact structure
        
        if df.empty:
            return pd.DataFrame()
            
        # Sort back to ascending for analysis
        df = df.sort_values('id', ascending=True)
        
        restored_rows = []
        for _, row in df.iterrows():
            if row['raw_data']:
                try:
                    data = json.loads(row['raw_data'])
                    restored_rows.append(data)
                except:
                    pass
        
        return pd.DataFrame(restored_rows)

    def migrate_from_csv(self, csv_path="results.csv"):
        csv_file = Path(__file__).parent / csv_path
        if not csv_file.exists():
            print("CSV file not found.")
            return

        try:
            # Use python engine and skip bad lines to avoid crashing on corrupted rows
            # Also try to be lenient with quoting
            df = pd.read_csv(csv_file, on_bad_lines='skip', engine='python')
            print(f"Migrating {len(df)} rows from CSV to SQLite...")
            
            for _, row in df.iterrows():
                data_row = row.to_dict()
                # Handle NaN values
                for k, v in data_row.items():
                    if pd.isna(v):
                        data_row[k] = None
                self.add_trade(data_row)
                
            print("Migration complete.")
            
            # Rename CSV to backup
            backup_path = csv_file.with_name(f"{csv_file.stem}_backup{csv_file.suffix}")
            csv_file.rename(backup_path)
            print(f"Renamed {csv_file} to {backup_path}")
            
        except Exception as e:
            print(f"Error migrating CSV: {e}")

    def get_stats(self):
        """Calculates total trades, win rate, and total net profit."""
        self.connect()
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM trades")
            total_trades = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM trades WHERE oco_result = 'profit'")
            wins = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(trade_result_net) FROM trades")
            result = cursor.fetchone()[0]
            total_net_profit = result if result is not None else 0.0
            
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            return {
                "total_trades": total_trades,
                "wins": wins,
                "losses": total_trades - wins,
                "win_rate": win_rate,
                "total_net_profit": total_net_profit
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "total_net_profit": 0.0
            }
        finally:
            self.close()

    def get_equity_data(self):
        """Returns timestamps and final balances for the equity chart."""
        self.connect()
        cursor = self.conn.cursor()
        try:
            # We want buy_timestamp and final_balance_usdt
            # Maybe limit to last 100 to avoid clutter if needed, but let's take all for now
            cursor.execute("SELECT buy_timestamp, final_balance_usdt FROM trades ORDER BY id ASC")
            rows = cursor.fetchall()
            
            # Helper to clean timestamp if needed, but assuming standard format
            data = [{"time": row[0], "balance": row[1]} for row in rows]
            return data
        except Exception as e:
            print(f"Error getting equity data: {e}")
            return []
        finally:
            self.close()
