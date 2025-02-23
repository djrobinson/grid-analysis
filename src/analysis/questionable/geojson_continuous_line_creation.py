import json
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from collections import defaultdict
from typing import Dict, List, Set, Tuple

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Earth."""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def are_points_close(p1: Tuple[float, float], p2: Tuple[float, float], threshold: float = 0.05) -> bool:
    """Check if two points are within threshold km of each other."""
    return haversine_distance(p1[1], p1[0], p2[1], p2[0]) < threshold

def find_matching_point(point: Tuple[float, float], point_set: Set[Tuple[float, float]], threshold: float = 0.05) -> Tuple[float, float]:
    """Find a matching point in point_set within threshold distance."""
    for existing_point in point_set:
        if are_points_close(point, existing_point, threshold):
            return existing_point
    return point

def is_within_spp_bounds(lat: float, lon: float) -> bool:
    """Check if coordinates are within SPP bounds."""
    MIN_LAT = 31
    MAX_LAT = 49
    MIN_LON = -107
    MAX_LON = -88.5
    
    return (MIN_LAT < lat < MAX_LAT) and (MIN_LON < lon < MAX_LON)

def is_at_boundary(lat: float, lon: float) -> bool:
    """Check if coordinates are at the SPP boundary (likely artificially cut)."""
    THRESHOLD = 0.01  # Small buffer for floating point comparison
    MIN_LAT = 31
    MAX_LAT = 49
    MIN_LON = -107
    MAX_LON = -88.5
    
    return (abs(lat - MIN_LAT) < THRESHOLD or 
            abs(lat - MAX_LAT) < THRESHOLD or 
            abs(lon - MIN_LON) < THRESHOLD or 
            abs(lon - MAX_LON) < THRESHOLD)

class GridProcessor:
    def __init__(self, geojson_path: str):
        self.geojson_path = geojson_path
        self.lines = []
        self.endpoints = defaultdict(list)
        self.continuous_lines = []
        self.junctions = {}
        # Configuration flags
        self.ignore_unknown_voltage = False  # Set to False to include unknown voltages
        
    def load_geojson(self):
        """Load and process the GeoJSON file."""
        with open(self.geojson_path) as f:
            data = json.load(f)
            
        for feature in data['features']:
            if feature['geometry']['type'] == 'LineString':
                coords = feature['geometry']['coordinates']
                # Convert voltage to float, default to 0 if not present or invalid
                try:
                    voltage = float(feature['properties'].get('voltage', 0))
                except (ValueError, TypeError):
                    voltage = 0
                voltclass = str(feature['properties'].get('voltclass', 'UNKNOWN'))
                self.lines.append({
                    'coords': coords,
                    'voltage': voltage,
                    'voltclass': voltclass,
                    'properties': feature['properties']
                })
                
    def is_valid_voltage(self, voltage: float, voltclass: str) -> bool:
        """
        Check if voltage/voltclass combination is valid.
        Comment/modify this function to change voltage filtering behavior.
        """
        if self.ignore_unknown_voltage:
            # Make sure we're comparing with float for voltage
            # Valid voltages in the data: 69, 115, 138, 161, 230, 345, 500
            return (voltage > 0 and voltage != -999999.0 and 
                   voltclass.upper() not in ['UNKNOWN', 'NOT AVAILABLE', ''])
        return True

    def join_lines(self, line1: dict, line2: dict) -> dict:
        """
        Join two lines, handling cases where they might connect at either end.
        Returns the joined line with coordinates in the correct order.
        """
        coords1 = line1['coords']
        coords2 = line2['coords']
        
        # Check which ends match
        start1 = tuple(coords1[0])
        end1 = tuple(coords1[-1])
        start2 = tuple(coords2[0])
        end2 = tuple(coords2[-1])
        
        new_coords = []
        if are_points_close(end1, start2):
            new_coords = coords1 + coords2[1:]
        elif are_points_close(start1, end2):
            new_coords = coords2 + coords1[1:]
        elif are_points_close(end1, end2):
            new_coords = coords1 + coords2[::-1][1:]
        elif are_points_close(start1, start2):
            new_coords = coords1[::-1] + coords2[1:]
        
        # Combine quality histories if they exist
        quality_history = []
        if 'quality_history' in line1:
            quality_history.extend(line1['quality_history'])
        if 'quality_history' in line2:
            quality_history.extend(line2['quality_history'])
            
        return {
            'coords': new_coords,
            'voltage': line1['voltage'],
            'voltclass': line1['voltclass'],
            'properties': {**line1['properties']},
            'quality_history': quality_history
        }

    def process_endpoints(self):
        """Process all endpoints and create a mapping of points to connected lines."""
        unique_points = set()
        
        # First pass: collect all unique points
        for line in self.lines:
                
            start = tuple(line['coords'][0])
            end = tuple(line['coords'][-1])
            
            
            # Find existing close points or add new ones
            start = find_matching_point(start, unique_points)
            end = find_matching_point(end, unique_points)
            
            unique_points.add(start)
            unique_points.add(end)
            
            self.endpoints[start].append(line)
            self.endpoints[end].append(line)

    def join_continuous_lines(self):
        """Join lines that form continuous segments."""
        processed_points = set()
        
        for point, connections in self.endpoints.items():
            if point in processed_points:
                continue
            
            if len(connections) == 2:
                line1, line2 = connections
                joined_line = None
                current_quality = None
                
                # Case 1: Same voltage and voltclass - definite join
                if len(set(c['voltage'] for c in connections)) == 1 and len(set(c['voltclass'] for c in connections)) == 1:
                    joined_line = self.join_lines(line1, line2)
                    current_quality = "JOIN_KNOWN"
                
                # Case 2: One known voltage, one unknown - speculative join
                else:
                    known_voltage_lines = [l for l in connections 
                                        if l['voltage'] not in [-999999.0, 0.0] and 
                                        l['voltclass'].upper() not in ['UNKNOWN', 'NOT AVAILABLE', '']]
                    unknown_voltage_lines = [l for l in connections 
                                          if l['voltage'] in [-999999.0, 0.0] or 
                                          l['voltclass'].upper() in ['UNKNOWN', 'NOT AVAILABLE', '']]
                    
                    if len(known_voltage_lines) == 1 and len(unknown_voltage_lines) == 1:
                        joined_line = self.join_lines(known_voltage_lines[0], unknown_voltage_lines[0])
                        current_quality = "JOIN_SPECULATIVE"
                
                    # Case 3: Both unknown voltages - uncertain join
                    elif all(l['voltage'] in [-999999.0, 0.0] or 
                            l['voltclass'].upper() in ['UNKNOWN', 'NOT AVAILABLE', '']
                            for l in connections):
                        joined_line = self.join_lines(line1, line2)
                        current_quality = "JOIN_UNKNOWN"
                
                    # Case 4: Different known voltages - add as transformer junction
                    elif (line1['voltage'] not in [-999999.0, 0.0] and 
                          line2['voltage'] not in [-999999.0, 0.0] and 
                          line1['voltage'] != line2['voltage']):
                        self.identify_junction(point, connections)
                        continue
                
                if joined_line and joined_line['coords']:
                    # Add current quality to history
                    if 'quality_history' not in joined_line:
                        joined_line['quality_history'] = []
                    joined_line['quality_history'].append(current_quality)
                    
                    self.continuous_lines.append(joined_line)
                    processed_points.add(point)
                    processed_points.add(tuple(joined_line['coords'][-1]))
                    continue
            
            # Handle non-joining cases
            if len(connections) == 1:
                # Single endpoint - only add if not at boundary
                end_coords = connections[0]['coords'][-1]
                if not is_at_boundary(end_coords[1], end_coords[0]):
                    if 'quality_history' not in connections[0]:
                        connections[0]['quality_history'] = ["ORIGINAL"]
                    self.continuous_lines.append(connections[0])
            else:
                # This is a junction point with 3+ connections
                self.identify_junction(point, connections)

    def identify_junction(self, point: Tuple[float, float], connections: List[dict]):
        """Identify and categorize junction points."""
        # Get all voltages and volt_classes, including unknown ones
        all_voltages = set(float(conn['voltage']) for conn in connections)
        all_volt_classes = set(conn['voltclass'].upper() for conn in connections)
        
        # Filter out invalid voltages for voltage-based decisions
        valid_voltages = set(float(conn['voltage']) for conn in connections 
                           if conn['voltage'] not in [-999999.0, 0.0])
        
        # Get substation candidates from all connecting lines using correct property names
        substation_candidates = [
            substation
            for conn in connections
            for substation in (
                conn['properties'].get('sub1', ''),
                conn['properties'].get('sub2', '')
            )
            if substation and substation not in ['', 'NOT AVAILABLE', 'UNKNOWN']
        ]
        
        # Count occurrences of each substation
        substation_counts = {}
        for substation in substation_candidates:
            substation_counts[substation] = substation_counts.get(substation, 0) + 1
        
        # Sort by count descending and get the most common substation
        most_common_substation = None
        if substation_counts:
            most_common_substation = sorted(
                substation_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[0][0]
        
        # Check if we have either different voltages OR different voltage classes
        if (len(connections) >= 3 or 
            len(valid_voltages) > 1 or 
            len(all_volt_classes) > 1):
            self.junctions[point] = {
                'type': 'transformer' if (len(valid_voltages) > 1 or len(all_volt_classes) > 1) else 'junction',
                'count': len(connections),
                'voltages': sorted(list(valid_voltages)) if valid_voltages else sorted(list(all_voltages)),
                'volt_classes': sorted(list(all_volt_classes)),
                'substation': most_common_substation if most_common_substation else '',
                'substation_candidates': substation_counts
            }

    def save_results(self):
        """Save results to CSV files."""
        VOLTAGE_ORDER = {
            '500': 12,
            '400': 11,
            '345': 10,
            '250': 9,
            '245': 8,
            '230': 7,
            '161': 6,
            '138': 5,
            '132': 4,
            '115': 3,
            '69': 2,
            '<69': 1,
            'UNKNOWN': 0
        }
        
        VOLTAGE_BUCKETS = {
            'UNKNOWN': lambda v: v in [-999999.0, 0.0],
            '<69': lambda v: v > 0 and v < 69,
            '69': lambda v: v == 69,
            '115': lambda v: v == 115,
            '132': lambda v: v == 132,
            '138': lambda v: v == 138,
            '161': lambda v: v == 161,
            '230': lambda v: v == 230,
            '245': lambda v: v == 245,
            '250': lambda v: v == 250,
            '345': lambda v: v == 345,
            '400': lambda v: v == 400,
            '500': lambda v: v == 500
        }
        
        # Initialize dictionary to hold lines for each voltage bucket
        voltage_buckets_data = {bucket: [] for bucket in VOLTAGE_BUCKETS.keys()}
        unexpected_voltages = set()
        
        # Sort lines into buckets
        for line in self.continuous_lines:
            voltage = float(line['voltage'])
            bucket_found = False
            
            for bucket_name, voltage_check in VOLTAGE_BUCKETS.items():
                if voltage_check(voltage):
                    voltage_buckets_data[bucket_name].append({
                        'voltage': voltage,
                        'voltclass': line['voltclass'],
                        'quality_history': json.dumps(line.get('quality_history', ["ORIGINAL"])),
                        'start_lon': line['coords'][0][0],
                        'start_lat': line['coords'][0][1],
                        'end_lon': line['coords'][-1][0],
                        'end_lat': line['coords'][-1][1],
                        'coordinates': json.dumps(line['coords']),
                        **line['properties']
                    })
                    bucket_found = True
                    break
            
            if not bucket_found:
                unexpected_voltages.add(voltage)
        
        # Log any unexpected voltages
        if unexpected_voltages:
            print("WARNING: Found unexpected voltage values:", sorted(list(unexpected_voltages)))
        
        # Save each bucket to its own CSV
        for bucket_name, lines_data in voltage_buckets_data.items():
            if lines_data:  # Only create CSV if we have data for this voltage
                df = pd.DataFrame(lines_data)
                filename = f'src/data/continuous_lines_{bucket_name.replace("<", "lt")}.csv'
                df.to_csv(filename, index=False)
                print(f"Created {filename} with {len(lines_data)} lines")
        
        # Initialize dictionary to hold junctions for each voltage bucket
        junction_buckets_data = {bucket: [] for bucket in VOLTAGE_BUCKETS.keys()}
        unexpected_junction_voltages = set()
        
        # Sort junctions into buckets based on highest voltage
        for coords, data in self.junctions.items():
            voltages = data['voltages']
            if not voltages:  # If no voltages, put in UNKNOWN bucket
                junction_buckets_data['UNKNOWN'].append({
                    'longitude': coords[0],
                    'latitude': coords[1],
                    'type': data['type'],
                    'connection_count': data['count'],
                    'voltages': json.dumps([float(v) for v in data['voltages']]),
                    'volt_classes': json.dumps(data['volt_classes']),
                    'substation': data.get('substation', ''),
                    'substation_candidates': json.dumps(data.get('substation_candidates', []))
                })
                continue
            
            # Find highest voltage that matches a bucket
            max_voltage = max(voltages)
            bucket_found = False
            
            # Try buckets in reverse order (highest to lowest) to ensure junction goes to highest matching bucket
            for bucket_name, voltage_check in sorted(VOLTAGE_BUCKETS.items(), 
                                                   key=lambda x: VOLTAGE_ORDER[x[0]], 
                                                   reverse=True):
                if voltage_check(max_voltage):
                    junction_buckets_data[bucket_name].append({
                        'longitude': coords[0],
                        'latitude': coords[1],
                        'type': data['type'],
                        'connection_count': data['count'],
                        'voltages': json.dumps([float(v) for v in data['voltages']]),
                        'volt_classes': json.dumps(data['volt_classes']),
                        'substation': data.get('substation', ''),
                        'substation_candidates': json.dumps(data.get('substation_candidates', []))
                    })
                    bucket_found = True
                    break
            
            if not bucket_found:
                unexpected_junction_voltages.add(max_voltage)
            
        # Log any unexpected voltages in junctions
        if unexpected_junction_voltages:
            print("WARNING: Found unexpected junction voltage values:", sorted(list(unexpected_junction_voltages)))
        
        # Save each junction bucket to its own CSV
        for bucket_name, junctions_data in junction_buckets_data.items():
            if junctions_data:  # Only create CSV if we have data for this voltage
                df = pd.DataFrame(junctions_data)
                filename = f'src/data/grid_junctions_{bucket_name.replace("<", "lt")}.csv'
                df.to_csv(filename, index=False)
                print(f"Created {filename} with {len(junctions_data)} junctions")

def main():
    processor = GridProcessor('src/data/spp_only_lines.geojson')
    processor.load_geojson()
    processor.process_endpoints()
    processor.join_continuous_lines()
    processor.save_results()


if __name__ == "__main__":
    main()
