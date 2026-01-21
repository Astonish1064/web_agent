import pandas as pd
import json

parquet_file = "/volume/pt-coder/users/lysun/kzheng/web_agent/train_deduped_filtered_167k_top20k_v6.parquet"
output_file = "sampled_data.json"

try:
    print(f"Reading parquet file: {parquet_file}")
    df = pd.read_parquet(parquet_file)
    print(f"Total rows: {len(df)}")
    print("Columns:", df.columns.tolist())
    
    # Sample 5 rows
    sample = df.sample(5)
    
    # Convert to dictionary records
    records = sample.to_dict(orient='records')
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(records, f, indent=2, default=str)
        
    print(f"Successfully saved 5 samples to {output_file}")
    
except Exception as e:
    print(f"Error: {e}")
