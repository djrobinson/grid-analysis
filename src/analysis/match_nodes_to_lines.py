import pandas as pd
import json
from math import radians, sin, cos, sqrt, atan2

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth."""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance

def get_line_endpoints(geojson_data):
    """Extract endpoints from each LineString feature."""
    endpoints = []
    for feature in geojson_data['features']:
        if feature['geometry']['type'] == 'LineString':
            coords = feature['geometry']['coordinates']
            start_point = coords[0]  # [lon, lat]
            end_point = coords[-1]   # [lon, lat]
            
            # Store endpoints with their metadata
            endpoints.append({
                'lon': start_point[0],
                'lat': start_point[1],
                'sub': feature['properties'].get('SUB_1'),
                'voltage': feature['properties'].get('VOLT_CLASS')
            })
            endpoints.append({
                'lon': end_point[0],
                'lat': end_point[1],
                'sub': feature['properties'].get('SUB_2'),
                'voltage': feature['properties'].get('VOLT_CLASS')
            })
    
    return endpoints

def find_closest_endpoints(nodes_df, endpoints, max_distance=10):
    """Find the closest endpoints for each node within max_distance (km)."""
    matches = []
    
    for _, node in nodes_df.iterrows():
        node_matches = []
        
        for endpoint in endpoints:
            distance = haversine_distance(
                node['Lat'], node['Lon'],
                endpoint['lat'], endpoint['lon']
            )
            
            if distance <= max_distance:
                node_matches.append({
                    'node': node['NOde'],
                    'distance_km': distance,
                    'endpoint_sub': endpoint['sub'],
                    'endpoint_voltage': endpoint['voltage'],
                    'endpoint_lat': endpoint['lat'],
                    'endpoint_lon': endpoint['lon']
                })
        
        # Sort matches by distance and keep the closest ones
        node_matches.sort(key=lambda x: x['distance_km'])
        matches.extend(node_matches[:3])  # Keep up to 3 closest matches per node
    
    return pd.DataFrame(matches)

def main():
    # Read input files
    nodes_df = pd.read_csv('src/data/Sheet 4-Table 1.csv')
    
    with open('src/data/spp_grid.geojson') as f:
        geojson_data = json.load(f)
    
    # Process the data
    endpoints = get_line_endpoints(geojson_data)
    matches_df = find_closest_endpoints(nodes_df, endpoints)
    
    # Save results
    matches_df.to_csv('node_endpoint_matches.csv', index=False)
    
    # Print summary
    print(f"Found {len(matches_df)} potential matches")
    print("\nSample matches:")
    print(matches_df.head())

if __name__ == "__main__":
    main()
