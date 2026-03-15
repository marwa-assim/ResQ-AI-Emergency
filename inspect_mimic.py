import pandas as pd
import os

DATA_DIR = r"data/mimic/mimic-iv-ed-2.2/ed"
TRIAGE_FILE = os.path.join(DATA_DIR, "triage.csv.gz")
EDSTAYS_FILE = os.path.join(DATA_DIR, "edstays.csv.gz")

def inspect_file(filepath, name):
    print(f"\n--- Inspecting {name} ---")
    if not os.path.exists(filepath):
        print(f"ERROR: File not found at {filepath}")
        return

    try:
        # Read only first 100 rows to be fast
        df = pd.read_csv(filepath, compression='gzip', nrows=100)
        print("Columns:", list(df.columns))
        print("\nFirst 3 rows:")
        print(df.head(3))
        
        if 'acuity' in df.columns:
            print("\nAcuity Distribution (Sample):")
            print(df['acuity'].value_counts())
            
    except Exception as e:
        print(f"Failed to read {name}: {e}")

if __name__ == "__main__":
    inspect_file(TRIAGE_FILE, "Triage")
    inspect_file(EDSTAYS_FILE, "ED Stays")
