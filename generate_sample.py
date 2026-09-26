import pandas as pd
import numpy as np

radius = 150 # mm (300mm wafer)
data = []

# Generate points in a polar pattern for realistic measurement
for r in np.linspace(0, radius, 20):
    for theta in np.linspace(0, 2*np.pi, 36, endpoint=False):
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        
        # Simulate thickness: bowl shape (thicker at edges)
        thickness = 1000 + (r / radius)**2 * 50 + np.random.randn() * 2
        
        # Simulate sheet resistance
        rs = 50 - (r / radius) * 10 + np.random.randn() * 0.5
        
        data.append({
            'DieX': round(x, 2),
            'DieY': round(y, 2),
            'Thickness_A': round(thickness, 2),
            'SheetRes_Ohm': round(rs, 2)
        })

df = pd.DataFrame(data)
df.to_csv('sample_wafer_data.csv', index=False)
print("Created sample_wafer_data.csv")
