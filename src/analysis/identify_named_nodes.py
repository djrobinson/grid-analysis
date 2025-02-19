import pandas as pd
from math import radians, sin, cos, sqrt, atan2

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Earth in kilometers."""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def is_valid_substation(name: str) -> bool:
    """Check if a substation name is valid (not UNKNOWN, TAP, or NOT AVAILABLE)."""
    if not name:
        return False
    invalid_prefixes = ['UNKNOWN', 'TAP', 'NOT AVAILABLE']
    return not any(name.startswith(prefix) for prefix in invalid_prefixes)

def determine_point_name(row: pd.Series) -> str:
    """
    Determine the point name based on priority:
    1. Valid substation name
    2. Plant name (if within 1km)
    3. Price node name (if within 1km)
    """
    # Priority 1: Valid substation name
    if is_valid_substation(str(row['substation_name'])):
        return row['substation_name']
    
    # Priority 2: Plant name if within 1km
    if pd.notna(row['plant_name']) and pd.notna(row['plant_distance']):
        if row['plant_distance'] <= 1.0:  # Distance is in km
            return row['plant_name']
    
    # Priority 3: Price node if within 1km
    if pd.notna(row['price_node']) and pd.notna(row['price_node_distance']):
        if row['price_node_distance'] <= 1.0:  # Distance is in km
            return row['price_node']
    
    return None

def process_nodes():
    """Process combined_nodes.csv to identify named points on the grid."""
    # Read the combined nodes data
    df = pd.read_csv('src/data/combined_nodes.csv', escapechar='\\', quoting=1, on_bad_lines='warn')
    
    # Add point_name column based on priority logic
    df['point_name'] = df.apply(determine_point_name, axis=1)
    
    # Filter to only keep rows where we have a valid point name
    named_nodes = df[df['point_name'].notna()].copy()
    
    # Save the results
    output_file = 'src/data/named_nodes.csv'
    named_nodes.to_csv(output_file, index=False)
    
    # Print statistics
    total_nodes = len(df)
    named_nodes_count = len(named_nodes)
    print(f"\nNode Statistics:")
    print(f"Total nodes processed: {total_nodes}")
    print(f"Nodes with valid names: {named_nodes_count}")
    print(f"Percentage named: {(named_nodes_count/total_nodes)*100:.1f}%")
    
    # Print breakdown of name sources
    substation_names = named_nodes[named_nodes['point_name'] == named_nodes['substation_name']].shape[0]
    plant_names = named_nodes[named_nodes['point_name'] == named_nodes['plant_name']].shape[0]
    price_node_names = named_nodes[named_nodes['point_name'] == named_nodes['price_node']].shape[0]
    
    print("\nName Source Breakdown:")
    print(f"From substation names: {substation_names} ({(substation_names/named_nodes_count)*100:.1f}%)")
    print(f"From plant names: {plant_names} ({(plant_names/named_nodes_count)*100:.1f}%)")
    print(f"From price nodes: {price_node_names} ({(price_node_names/named_nodes_count)*100:.1f}%)")

if __name__ == "__main__":
    process_nodes() 