import pandas as pd
import os

DATA_DIR = r"data/mimic/mimic-iv-ed-2.2/ed"
TRIAGE_PATH = os.path.join(DATA_DIR, "triage.csv.gz")

if os.path.exists(TRIAGE_PATH):
    df = pd.read_csv(TRIAGE_PATH, compression='gzip', nrows=5)
    print(df[['subject_id', 'chiefcomplaint', 'acuity']].to_string())
else:
    print("File not found")
