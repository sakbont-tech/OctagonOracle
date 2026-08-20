import pandas as pd
import numpy as np

df = pd.read_csv("data/processed/clean_ufc_data.csv")

even_fighters = df[0: len(df) :2].reset_index(drop=True)
odd_fighters = df.iloc[1: len(df) :2].reset_index(drop=True)

even_fighters.drop(columns=["Fighter", "Result"], inplace=True)
odd_fighters.drop(columns=["Fighter", "Result"], inplace=True)

diff_even = even_fighters - odd_fighters
diff_odd = odd_fighters - even_fighters

target_even = df.iloc[0: len(df) : 2]["Result"].reset_index(drop=True)
target_odd = df.iloc[1: len(df) : 2]["Result"].reset_index(drop=True)

target_even = target_even.replace({'W': 1, 'L' : 0})
target_odd = target_odd.replace({'W': 1, 'L' : 0})

diff_even["Target"] = target_even
diff_odd["Target"] = target_odd

ml_dataset = pd.concat([diff_even, diff_odd], ignore_index=True)
ml_dataset.to_csv("data/processed/ml_ready_ufc_data.csv", index=False)