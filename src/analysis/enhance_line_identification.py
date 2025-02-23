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

def assign_substations_to_endpoints(geojson_path: str) -> str:
    """
    Create a new GeoJSON file with start_sub and end_sub properties that correctly
    match the geographical start and end points of each line.
    """
    # Load named nodes
    print("Loading named nodes...")
    named_nodes_df = pd.read_csv('src/data/named_nodes.csv')
    
    # Load original GeoJSON
    print("Loading original GeoJSON...")
    with open(geojson_path) as f:
        geojson_data = json.load(f)
    
    # Initialize new GeoJSON
    new_geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    print("Reassigning substations to endpoints...")
    for feature in geojson_data['features']:
        if feature['geometry']['type'] != 'LineString':
            continue
            
        properties = feature['properties']
        coords = feature['geometry']['coordinates']
        
        # Get start and end coordinates
        start_lon, start_lat = coords[0]
        end_lon, end_lat = coords[-1]
        
        sub1 = str(properties.get('sub1', ''))
        sub2 = str(properties.get('sub2', ''))
        
        # Find which substation (if any) corresponds to which endpoint
        start_sub = None
        end_sub = None
        
        # Only process named substations
        if not is_unnamed_substation(sub1):
            # Find the coordinates of sub1 in named_nodes_df
            sub1_node = named_nodes_df[named_nodes_df['point_name'] == sub1]
            if not sub1_node.empty:
                if (sub1_node.iloc[0]['longitude'] == start_lon and 
                    sub1_node.iloc[0]['latitude'] == start_lat):
                    start_sub = sub1
                    print("found start sub1")
                elif (sub1_node.iloc[0]['longitude'] == end_lon and 
                      sub1_node.iloc[0]['latitude'] == end_lat):
                    end_sub = sub1
                    print("found end sub1")
        if not is_unnamed_substation(sub2):
            # Find the coordinates of sub2 in named_nodes_df
            sub2_node = named_nodes_df[named_nodes_df['point_name'] == sub2]
            if not sub2_node.empty:
                if (sub2_node.iloc[0]['longitude'] == start_lon and 
                    sub2_node.iloc[0]['latitude'] == start_lat and 
                    start_sub is None):
                    start_sub = sub2
                    print("found start sub2")
                elif (sub2_node.iloc[0]['longitude'] == end_lon and 
                      sub2_node.iloc[0]['latitude'] == end_lat and 
                      end_sub is None):
                    end_sub = sub2
                    
        
        # Create new feature with reassigned substations
        new_feature = {
            "type": "Feature",
            "geometry": feature['geometry'],
            "properties": {
                **properties,
                "start_sub": start_sub if start_sub else "",
                "end_sub": end_sub if end_sub else "",
                "original_start_sub": start_sub if start_sub else "",
                "original_end_sub": end_sub if end_sub else ""
            }
        }
        
        new_geojson['features'].append(new_feature)
    
    # Save new GeoJSON
    output_file = 'src/data/spp_only_lines_with_endpoints.geojson'
    with open(output_file, 'w') as f:
        json.dump(new_geojson, f, indent=2)
    
    return output_file

def enhance_line_identification():
    """Enhance line identification using named nodes to identify additional major lines."""
    # First, create the endpoint-assigned GeoJSON
    input_file = 'src/data/spp_only_lines.geojson'
    endpoint_assigned_file = assign_substations_to_endpoints(input_file)
    
    # Load named nodes
    print("Loading named nodes...")
    named_nodes_df = pd.read_csv('src/data/named_nodes.csv')
    
    # Load endpoint-assigned GeoJSON
    print("Loading endpoint-assigned GeoJSON...")
    with open(endpoint_assigned_file) as f:
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
    sanity_iterator = 0
    for feature in geojson_data['features']:
        if feature['geometry']['type'] != 'LineString':
            continue
            
        properties = feature['properties']
        coords = feature['geometry']['coordinates']
        
        # Get original substation names
        start_sub = str(properties.get('start_sub', ''))
        end_sub = str(properties.get('end_sub', ''))
        
        # Check if both substations are unnamed
        both_unnamed = is_unnamed_substation(start_sub) and is_unnamed_substation(end_sub)
        
        # Get start and end coordinates
        start_lon, start_lat = coords[0]
        end_lon, end_lat = coords[-1]
        
        # Find closest named nodes for start and end points
        improved_start = None
        improved_end = None
        
        if is_unnamed_substation(start_sub):
            improved_start = find_closest_named_node(start_lon, start_lat, named_nodes_df, 0.5)
        else:
            improved_start = start_sub
            
        if is_unnamed_substation(end_sub):
            improved_end = find_closest_named_node(end_lon, end_lat, named_nodes_df, 0.5)
        else:
            improved_end = end_sub
        
        # Create improved feature
        # Determine quality based on improvements
        quality = "ORIGINAL"
        if improved_start and improved_end:
            quality = "BOTH_ENHANCED"
        elif improved_start:
            quality = "ENHANCED_START"
        elif improved_end:
            quality = "ENHANCED_END"
            
        improved_feature = {
            "type": "Feature",
            "geometry": feature['geometry'],
            "properties": {
                **properties,
                "start_sub": improved_start if improved_start else start_sub,
                "end_sub": improved_end if improved_end else end_sub,
                "original_start_sub": start_sub,
                "original_end_sub": end_sub,
                "quality": quality
            }
        }
        
        # Track statistics
        if not both_unnamed:
            already_named_lines += 1
        elif improved_start or improved_end:
            newly_identified_lines += 1
            
        if improved_start or improved_end:
            improved_lines += 1
        sanity_iterator += 1
        if sanity_iterator % 100 == 0:
            print(sanity_iterator)
            
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