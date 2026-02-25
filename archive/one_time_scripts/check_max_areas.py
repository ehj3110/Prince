import pandas as pd
import numpy as np
from pathlib import Path

folder = Path(r"C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\Presentation data\Final")

for cond in ['FEP', 'PDMS - Unsealed', 'PDMS - Sealed', 'Hybrid', 'Hybrid - Compliant']:
    csv = folder / cond / 'automated_work_of_adhesion.csv'
    if csv.exists():
        df = pd.read_csv(csv)
        max_area = df['Cross_Sectional_Area_mm2'].max()
        max_radius = np.sqrt(max_area / np.pi)
        print(f'{cond}: Max area = {max_area:.2f} mm² (radius = {max_radius:.2f} mm)')
