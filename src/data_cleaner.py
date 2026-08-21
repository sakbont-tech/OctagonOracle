import pandas as pd
import numpy as np

df = pd.read_csv("data/raw/historical_ufc_data.csv")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

df["Ctrl"] = df["Ctrl"].replace(["---", "--"], "0:00")
time_parts = df["Ctrl"].str.split(":", expand=True).astype(int)
df["Ctrl"] = (time_parts[0] * 60) + time_parts[1]

columns = ['Sig. str.', 'Total str.', 'Td', 'Head (SS)', 'Body (SS)', 'Leg (SS)', 'Distance (SS)', 'Clinch (SS)', 'Ground (SS)']


for column in columns:

    base_name = column.replace(' (SS)', '').replace('.', '').replace(' ', '_').lower()

    data = df[column].str.split(" of ", expand=True).astype(int)

    data = df[column].str.split(" of ", expand=True).astype(int)

    df[f"{base_name}_landed"] = data[0]
    df[f"{base_name}_attempted"] = data[1]

    df[f"{base_name}_rate"] = np.where(
        df[f"{base_name}_attempted"] > 0,                               
        df[f"{base_name}_landed"] / df[f"{base_name}_attempted"],           
        0.0                                                        
    )

    df.drop(columns=[column], inplace=True)

df.drop(columns=['Sig. str. %', 'Td %'], inplace=True, errors='ignore')

pd.set_option('display.max_columns', None)

df.to_csv("data/processed/clean_ufc_data.csv", index=False)