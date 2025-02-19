import pandas as pd
import json
import glob
from pathlib import Path

def create_geojson_from_csvs():
    """Convert all major_lines_*.csv files to separate GeoJSON files by voltage level."""
    # Find all major lines CSV files
    csv_files = glob.glob('src/data/major_lines_*.csv')
    
    # Process each CSV file separately
    for csv_file in csv_files:
        print(f"Processing {csv_file}...")
        
        # Initialize GeoJSON structure for this voltage level
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        # Read CSV file
        df = pd.read_csv(csv_file)
        
        # Convert each row to a GeoJSON feature
        for _, row in df.iterrows():
            # Parse the coordinates from the JSON string
            try:
                coordinates = json.loads(row['coordinates'])
            except (json.JSONDecodeError, KeyError):
                print(f"Warning: Could not parse coordinates for a row in {csv_file}")
                continue
            
            # Create feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "voltage": float(row['voltage']),
                    "voltclass": row['voltclass'],
                    "owner": row.get('owner', ''),
                    "sub1": row.get('sub1', ''),
                    "sub2": row.get('sub2', '')
                }
            }
            
            # Add any additional properties that exist in the CSV
            for col in row.index:
                if col not in ['coordinates', 'voltage', 'voltclass', 
                             'owner', 'sub1', 'sub2', 'start_lon', 'start_lat', 
                             'end_lon', 'end_lat']:
                    feature['properties'][col] = row[col]
            
            geojson['features'].append(feature)
        
        # Create output filename based on input CSV name
        csv_basename = Path(csv_file).stem
        output_file = f'src/data/{csv_basename}.geojson'
        
        # Save the GeoJSON for this voltage level
        with open(output_file, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"Created {output_file} with {len(geojson['features'])} features")
        
        # Print statistics for this voltage level
        voltage_counts = {}
        for feature in geojson['features']:
            voltage = feature['properties']['voltage']
            voltage_counts[voltage] = voltage_counts.get(voltage, 0) + 1
        
        print("\nVoltage statistics:")
        for voltage, count in sorted(voltage_counts.items()):
            print(f"  {voltage}kV: {count} lines")
        print()

if __name__ == "__main__":
    create_geojson_from_csvs() 