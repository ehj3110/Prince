import pandas as pd

df = pd.read_csv('C:/Users/ehunt/OneDrive - Northwestern University/Lab Work/Nissan/Adhesion Tests/SteppedConeTests/V9/data/MASTER_all_metrics.csv')
print(f'Total layers: {len(df)}')
print(f'\nColumns: {df.columns.tolist()[:10]}')
print(f'\nConditions:')
summary = df.groupby('condition_label').agg({
    'peak_force_N': ['count', 'mean', 'std'], 
    'work_of_adhesion_mJ': ['mean', 'std']
}).round(4)
print(summary)

print(f'\n\nTEMPO Comparison:')
tempo = df[df['condition_label'].str.contains('TEMPO')]
for cond in tempo['condition_label'].unique():
    data = tempo[tempo['condition_label']==cond]
    print(f'\n{cond}:')
    print(f'  Peak Force: {data["peak_force_N"].mean():.4f} +/- {data["peak_force_N"].std():.4f} N')
    print(f'  Work: {data["work_of_adhesion_mJ"].mean():.4f} +/- {data["work_of_adhesion_mJ"].std():.4f} mJ')
    print(f'  Layers: {len(data)}')
