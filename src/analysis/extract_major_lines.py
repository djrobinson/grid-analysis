import json
import pandas as pd

def is_valid_substation(substation: str) -> bool:
    """Check if a substation name is valid (not TAP, UNKNOWN, or NOT AVAILABLE)."""
    if not substation:
        return False
    invalid_prefixes = ['TAP', 'UNKNOWN', 'NOT AVAILABLE']
    return not any(substation.startswith(prefix) for prefix in invalid_prefixes)

def extract_major_lines(geojson_path: str):
    """Extract transmission lines that connect named substations."""
    # Read the GeoJSON file
    with open(geojson_path) as f:
        data = json.load(f)
    
    # Initialize lists to store major lines for each voltage level
    voltage_buckets = {
        'UNKNOWN': [],
        '<69': [],
        '69': [],
        '115': [],
        '132': [],
        '138': [],
        '161': [],
        '230': [],
        '245': [],
        '250': [],
        '345': [],
        '400': [],
        '500': []
    }
    
    # Process each feature
    for feature in data['features']:
        if feature['geometry']['type'] != 'LineString':
            continue
        
        properties = feature['properties']
        sub1 = str(properties.get('sub1', ''))
        sub2 = str(properties.get('sub2', ''))
        
        # Skip if both substations are invalid
        if not (is_valid_substation(sub1) or is_valid_substation(sub2)):
            continue
        
        # Get voltage and prepare line data
        try:
            voltage = float(properties.get('voltage', 0))
        except (ValueError, TypeError):
            voltage = 0
            
        line_data = {
            'voltage': voltage,
            'voltclass': properties.get('voltclass', 'UNKNOWN'),
            'sub1': sub1,
            'sub2': sub2,
            'owner': properties.get('owner', ''),
            'start_lon': feature['geometry']['coordinates'][0][0],
            'start_lat': feature['geometry']['coordinates'][0][1],
            'end_lon': feature['geometry']['coordinates'][-1][0],
            'end_lat': feature['geometry']['coordinates'][-1][1],
            'coordinates': json.dumps(feature['geometry']['coordinates'])
        }
        
        # Determine voltage bucket
        if voltage in [-999999.0, 0.0]:
            voltage_buckets['UNKNOWN'].append(line_data)
        elif voltage < 69:
            voltage_buckets['<69'].append(line_data)
        elif voltage == 69:
            voltage_buckets['69'].append(line_data)
        elif voltage == 115:
            voltage_buckets['115'].append(line_data)
        elif voltage == 138:
            voltage_buckets['138'].append(line_data)
        elif voltage == 161:
            voltage_buckets['161'].append(line_data)
        elif voltage == 230:
            voltage_buckets['230'].append(line_data)
        elif voltage == 345:
            voltage_buckets['345'].append(line_data)
        elif voltage == 400:
            voltage_buckets['400'].append(line_data)
        elif voltage == 500:
            voltage_buckets['500'].append(line_data)
        else:
            print(f"WARNING: Unexpected voltage value: {voltage}")
    
    # Save each voltage bucket to a separate CSV file
    for voltage, lines in voltage_buckets.items():
        if lines:  # Only create CSV if we have data for this voltage
            df = pd.DataFrame(lines)
            filename = f'src/data/major_lines_{voltage.replace("<", "lt")}.csv'
            df.to_csv(filename, index=False)
            print(f"Created {filename} with {len(lines)} lines")

def main():
    extract_major_lines('src/data/spp_only_lines.geojson')

if __name__ == "__main__":
    main() 