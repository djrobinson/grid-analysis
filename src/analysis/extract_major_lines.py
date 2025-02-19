import json
import pandas as pd

class GridProcessor:
    def __init__(self, geojson_path: str):
        self.geojson_path = geojson_path
        self.data = None
        
    def is_valid_substation(self, substation: str) -> bool:
        """Check if a substation name is valid (not TAP, UNKNOWN, or NOT AVAILABLE)."""
        if not substation:
            return False
        invalid_prefixes = ['TAP', 'UNKNOWN', 'NOT AVAILABLE']
        return not any(str(substation).startswith(prefix) for prefix in invalid_prefixes)
    
    def load_geojson(self):
        """Load the GeoJSON file."""
        with open(self.geojson_path) as f:
            self.data = json.load(f)
    
    def process_endpoints(self):
        """Placeholder for endpoint processing - not needed for basic extraction."""
        pass
    
    def join_continuous_lines(self):
        """Placeholder for line joining - not needed for basic extraction."""
        pass
    
    def save_results(self):
        """Extract and save major transmission lines that connect named substations."""
        if not self.data:
            raise ValueError("No data loaded. Call load_geojson() first.")
            
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
        
        # Initialize buckets for unknown lines
        unknown_voltage_buckets = {
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
        for feature in self.data['features']:
            if feature['geometry']['type'] != 'LineString':
                continue
            
            properties = feature['properties']
            sub1 = str(properties.get('sub1', ''))
            sub2 = str(properties.get('sub2', ''))
            
            # Prepare line data
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
                'coordinates': json.dumps(feature['geometry']['coordinates']),
                'quality': properties.get('quality', 'ORIGINAL')
            }
            
            # Determine which bucket set to use
            target_buckets = voltage_buckets if (self.is_valid_substation(sub1) or self.is_valid_substation(sub2)) else unknown_voltage_buckets
            
            # Determine voltage bucket
            if voltage in [-999999.0, 0.0]:
                target_buckets['UNKNOWN'].append(line_data)
            elif voltage < 69:
                target_buckets['<69'].append(line_data)
            elif voltage == 69:
                target_buckets['69'].append(line_data)
            elif voltage == 115:
                target_buckets['115'].append(line_data)
            elif voltage == 132:
                target_buckets['132'].append(line_data)
            elif voltage == 138:
                target_buckets['138'].append(line_data)
            elif voltage == 161:
                target_buckets['161'].append(line_data)
            elif voltage == 230:
                target_buckets['230'].append(line_data)
            elif voltage == 245:
                target_buckets['245'].append(line_data)
            elif voltage == 250:
                target_buckets['250'].append(line_data)
            elif voltage == 345:
                target_buckets['345'].append(line_data)
            elif voltage == 400:
                target_buckets['400'].append(line_data)
            elif voltage == 500:
                target_buckets['500'].append(line_data)
            else:
                print(f"WARNING: Unexpected voltage value: {voltage}")
        
        # Save each voltage bucket to a separate CSV file
        for voltage, lines in voltage_buckets.items():
            if lines:  # Only create CSV if we have data for this voltage
                df = pd.DataFrame(lines)
                filename = f'src/data/major_lines_{voltage.replace("<", "lt")}.csv'
                df.to_csv(filename, index=False)
                print(f"Created {filename} with {len(lines)} lines")
        
        # Save each unknown voltage bucket to a separate CSV file
        for voltage, lines in unknown_voltage_buckets.items():
            if lines:  # Only create CSV if we have data for this voltage
                df = pd.DataFrame(lines)
                filename = f'src/data/unknown_lines_{voltage.replace("<", "lt")}.csv'
                df.to_csv(filename, index=False)
                print(f"Created {filename} with {len(lines)} lines")

    def extract_major_lines(self):
        self.load_geojson()
        self.process_endpoints()
        self.join_continuous_lines()
        self.save_results()
