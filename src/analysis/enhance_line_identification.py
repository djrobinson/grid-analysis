import json
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Tuple, Optional
from src.analysis.extract_major_lines import GridProcessor

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Earth in kilometers."""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def is_unnamed_substation(name: str) -> bool:
    """Check if a substation name is unnamed (starts with TAP, UNKNOWN, or NOT AVAILABLE)."""
    if not name:
        return True
    invalid_prefixes = ['TAP', 'UNKNOWN', 'NOT AVAILABLE']
    return any(str(name).startswith(prefix) for prefix in invalid_prefixes)

def find_closest_named_node(lon: float, lat: float, named_nodes_df: pd.DataFrame, 
                          max_distance: float = 1.0) -> Optional[str]:
    """Find the closest named node within max_distance kilometers."""
    min_distance = float('inf')
    closest_name = None
    
    for _, node in named_nodes_df.iterrows():
        distance = haversine_distance(lat, lon, node['latitude'], node['longitude'])
        if distance < min_distance and distance <= max_distance:
            min_distance = distance
            closest_name = node['point_name']
    
    return closest_name

def enhance_line_identification():
    """Enhance line identification using named nodes to identify additional major lines."""
    # Load named nodes
    print("Loading named nodes...")
    named_nodes_df = pd.read_csv('src/data/named_nodes.csv')
    
    # Load original GeoJSON
    print("Loading original GeoJSON...")
    with open('src/data/spp_only_lines.geojson') as f:
        geojson_data = json.load(f)
    
    # Initialize improved GeoJSON
    improved_geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # Track statistics
    total_lines = len(geojson_data['features'])
    improved_lines = 0
    already_named_lines = 0
    newly_identified_lines = 0
    
    print("Processing lines...")
    for feature in geojson_data['features']:
        if feature['geometry']['type'] != 'LineString':
            continue
            
        properties = feature['properties']
        coords = feature['geometry']['coordinates']
        
        # Get original substation names
        sub1 = str(properties.get('sub1', ''))
        sub2 = str(properties.get('sub2', ''))
        
        # Check if both substations are unnamed
        both_unnamed = is_unnamed_substation(sub1) and is_unnamed_substation(sub2)
        
        # Get start and end coordinates
        start_lon, start_lat = coords[0]
        end_lon, end_lat = coords[-1]
        
        # Find closest named nodes for start and end points
        improved_sub1 = None
        improved_sub2 = None
        
        if is_unnamed_substation(sub1):
            improved_sub1 = find_closest_named_node(start_lon, start_lat, named_nodes_df, 0.5)
        else:
            improved_sub1 = sub1
            
        if is_unnamed_substation(sub2):
            improved_sub2 = find_closest_named_node(end_lon, end_lat, named_nodes_df, 0.5)
        else:
            improved_sub2 = sub2
        
        # Create improved feature
        # Determine quality based on improvements
        quality = "ORIGINAL"
        if improved_sub1 and improved_sub2:
            quality = "BOTH_ENHANCED"
        elif improved_sub1:
            quality = "ENHANCED_SUB1"
        elif improved_sub2:
            quality = "ENHANCED_SUB2"
            
        improved_feature = {
            "type": "Feature",
            "geometry": feature['geometry'],
            "properties": {
                **properties,
                "sub1": improved_sub1 if improved_sub1 else sub1,
                "sub2": improved_sub2 if improved_sub2 else sub2,
                "original_sub1": sub1,
                "original_sub2": sub2,
                "quality": quality
            }
        }
        
        # Track statistics
        if not both_unnamed:
            already_named_lines += 1
        elif improved_sub1 or improved_sub2:
            newly_identified_lines += 1
            
        if improved_sub1 or improved_sub2:
            improved_lines += 1
            
        improved_geojson['features'].append(improved_feature)
    
    # Save improved GeoJSON
    output_file = 'src/data/spp_only_lines_improved.geojson'
    with open(output_file, 'w') as f:
        json.dump(improved_geojson, f, indent=2)
    
    print("\nProcessing Statistics:")
    print(f"Total lines processed: {total_lines}")
    print(f"Lines with improvements: {improved_lines}")
    print(f"Previously named lines: {already_named_lines}")
    print(f"Newly identified lines: {newly_identified_lines}")
    
    return output_file

def main():
    # Enhance line identification
    improved_geojson = enhance_line_identification()
    
    # Run extract_major_lines with improved GeoJSON
    processor = GridProcessor('src/data/spp_only_lines_improved.geojson')
    processor.extract_major_lines()

if __name__ == "__main__":
    main() 