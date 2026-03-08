import pandas as pd
import numpy as np

folders = ['PDMS_800nm', 'PDMS_800nm_Continuous', 'PDMS_Flat', 
           'PDMSV2_800nm', 'PFPE_800nm', 'PFPE_800nm_Continuous', 
           'PFPE_Flat_NoOil_BPAGDA']
root = r'C:\Users\cheng sun\BoyuanSun\Slicing\Evan\10SqmmCylinder\Printing_Logs\ToProcess'

print('Layer counts per folder:')
print('=' * 80)

for f in folders:
    try:
        df = pd.read_csv(f'{root}\\{f}\\autolog_L45-L49.csv')
        print(f'\n{f}')
        print(f'  Total rows: {len(df)}')
        
        if 'Phase' in df.columns:
            phases = df['Phase'].value_counts()
            print(f'  Phase counts: {dict(phases)}')
            
            # Count layers
            phase = df['Phase'].values
            layer_count = 0
            in_layer = False
            layer_sizes = []
            start_idx = None
            
            for i, p in enumerate(phase):
                if not in_layer and p in ['Exposure', 'Lift', 'Pause']:
                    in_layer = True
                    start_idx = i
                    layer_count += 1
                elif in_layer and (p not in ['Exposure', 'Lift', 'Pause'] or i == len(phase) - 1):
                    end_idx = i if i == len(phase) - 1 else i - 1
                    layer_sizes.append(end_idx - start_idx + 1)
                    in_layer = False
            
            print(f'  Detected {layer_count} layers')
            print(f'  Layer sizes: {layer_sizes}')
            
    except Exception as e:
        print(f'{f}: ERROR - {e}')

print('\n' + '=' * 80)
