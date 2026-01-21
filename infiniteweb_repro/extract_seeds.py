import pandas as pd
import json

# Load a small sample
df = pd.read_parquet('/volume/pt-coder/users/lysun/kzheng/web_agent/train_deduped_filtered_167k_top20k_v6.parquet')

# The 'question' column usually contains the user intent/description
print("--- Potential Website Seeds (from 'question' column) ---")
for i, text in enumerate(df['question'].head(10)):
    # The dataset often starts with a preamble. Let's strip it to find the real generic intent.
    # Common preamble: "You are a code expert. Please use your professional knowledge to generate accurate and professional responses. Be sure to provide executable code whenever possible."
    content = text.replace("You are a code expert. Please use your professional knowledge to generate accurate and professional responses. Be sure to provide executable code whenever possible.", "").strip()
    
    # Take the first meaningful sentence or chunk
    seed_summary = content[:150].replace('\n', ' ') + "..."
    print(f"{i+1}. {seed_summary}")
