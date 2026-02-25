import pandas as pd
import numpy as np

df = pd.read_csv(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final\MASTER_final_combined.csv")

print("Checking radius_mm column:")
for cond in df['condition'].unique():
    subset = df[df['condition']==cond]
    if 'radius_mm' in df.columns:
        print(f"{cond}: max radius = {subset['radius_mm'].max():.2f} mm")
