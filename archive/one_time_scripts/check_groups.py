import pandas as pd

df = pd.read_csv(r'C:\Users\ehunt\OneDrive - Northwestern University\Lab Work\Nissan\Adhesion Tests\SteppedConeTests\V2\MASTER_v2_selected_metrics.csv')
peo = df[df['folder'].str.contains('2p5PEO')]

def get_autolog_group(layer_num):
    if layer_num < 100:
        return f"L{(layer_num // 10) * 10}"
    else:
        base = (layer_num // 10) * 10
        return f"L{base}"

peo['autolog_group'] = peo['layer_number'].apply(get_autolog_group)

print('Autolog groups created:')
print(sorted(peo['autolog_group'].unique()))
print('\nCount:', len(peo['autolog_group'].unique()))

print('\nExpected 9 autolog files:')
print('L60-65, L100-105, L140-145, L180-185, L210-215, L250-255, L300-305, L335-340, L365-370')

print('\nLayers per group:')
for group in sorted(peo['autolog_group'].unique()):
    layers = sorted(peo[peo['autolog_group'] == group]['layer_number'].values)
    print(f"{group}: {layers}")
