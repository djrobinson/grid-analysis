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
        """Extract and save transmission lines to a single CSV file."""
        if not self.data:
            raise ValueError("No data loaded. Call load_geojson() first.")
            
        # Initialize list to store all lines
        all_lines = []
        
        # Process each feature
        for feature in self.data['features']:
            if feature['geometry']['type'] != 'LineString':
                continue
            
            properties = feature['properties']
            
            # Get both original and corrected substation names
            sub1 = str(properties.get('sub1', ''))
            sub2 = str(properties.get('sub2', ''))
            start_sub = str(properties.get('start_sub', ''))
            end_sub = str(properties.get('end_sub', ''))
            
            # Prepare line data
            try:
                voltage = float(properties.get('voltage', 0))
            except (ValueError, TypeError):
                voltage = 0
                
            # Determine voltage category
            voltage_category = 'UNKNOWN'
            if voltage not in [-999999.0, 0.0]:
                if voltage < 69:
                    voltage_category = '<69'
                else:
                    voltage_category = str(int(voltage))
                
            # Determine if line has valid substations
            has_valid_sub = (
                self.is_valid_substation(sub1) or 
                self.is_valid_substation(sub2) or 
                self.is_valid_substation(start_sub) or 
                self.is_valid_substation(end_sub)
            )
                
            line_data = {
                'voltage': voltage,
                'voltage_category': voltage_category,
                'voltclass': properties.get('voltclass', 'UNKNOWN'),
                'sub1': sub1,
                'sub2': sub2,
                'start_substation': start_sub if start_sub else None,
                'end_substation': end_sub if end_sub else None,
                'owner': properties.get('owner', ''),
                'start_lon': feature['geometry']['coordinates'][0][0],
                'start_lat': feature['geometry']['coordinates'][0][1],
                'end_lon': feature['geometry']['coordinates'][-1][0],
                'end_lat': feature['geometry']['coordinates'][-1][1],
                'coordinates': json.dumps(feature['geometry']['coordinates']),
                'quality': properties.get('quality', 'ORIGINAL'),
                'identified': True if has_valid_sub else False
            }
            
            all_lines.append(line_data)
        
        # Save all lines to a single CSV file
        if all_lines:
            df = pd.DataFrame(all_lines)
            filename = 'src/data/transmission_lines.csv'
            df.to_csv(filename, index=False)
            print(f"Created {filename} with {len(all_lines)} lines")
            print(f"Known lines: {len(df[df['identified'] == True])}")
            print(f"Unknown lines: {len(df[df['identified'] == False])}")

    def extract_major_lines(self):
        self.load_geojson()
        self.process_endpoints()
        self.join_continuous_lines()
        self.save_results()


if __name__ == "__main__":
    processor = GridProcessor('src/data/spp_only_lines_improved.geojson')
    processor.extract_major_lines()