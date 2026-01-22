import pandas as pd
import os
from config.logging_config import get_logger

logger = get_logger("DataLoader")

def load_data(market, days=None, data_dir="data"):
    """
    Load data from local CSV file.
    If days is specified, filter for the last N days.
    """
    file_path = os.path.join(data_dir, f"{market}.csv")
    
    if not os.path.exists(file_path):
        logger.error(f"Data file not found: {file_path}. Please run collect_data.py first.")
        return None
        
    try:
        df = pd.read_csv(file_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        if days:
            # Filter last N days based on timestamp
            # We assume data ends roughly 'now', or just take last rows corresponding to days * 24?
            # Better to filter by time difference from last date in file
            last_date = df.iloc[-1]['datetime']
            start_date = last_date - pd.Timedelta(days=days)
            df = df[df['datetime'] > start_date].copy()
            
        return df
    except Exception as e:
        logger.error(f"Failed to load data for {market}: {e}")
        return None
