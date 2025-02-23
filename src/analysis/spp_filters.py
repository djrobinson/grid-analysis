import pandas as pd
import json


def filter_points_to_spp_only(points_df):
    # lat/lon
    points_df = points_df[points_df['Latitude'] > 31]
    points_df = points_df[points_df['Latitude'] < 49]
    points_df = points_df[points_df['Longitude'] > -107]
    points_df = points_df[points_df['Longitude'] < -88.5]
    # Also filter out all plants <10MW
    points_df = points_df[points_df['Total_MW'] > 10]
    return points_df


def filter_geo_to_spp_only(geojson_data):
    endpoints = []
    for feature in geojson_data['features']:
        MIN_LON = -107
        MAX_LON = -88.5
        MIN_LAT = 31
        MAX_LAT = 49
        # Lon bounds: -89.30543	48.75449
        # Lat bounds: -106.4123	31.98229
        # Only append if BOTH start and end points are within the bounds
        print(feature['geometry']['coordinates'][0][0])
        if feature['geometry']['type'] == 'LineString':
            if feature['geometry']['coordinates'][0][0] > MIN_LON and feature['geometry']['coordinates'][0][0] < MAX_LON \
                and feature['geometry']['coordinates'][0][1] > MIN_LAT and feature['geometry']['coordinates'][0][1] < MAX_LAT \
                and feature['geometry']['coordinates'][- 1][0] > MIN_LON and feature['geometry']['coordinates'][- 1][0] < MAX_LON \
                and feature['geometry']['coordinates'][- 1][1] > MIN_LAT and feature['geometry']['coordinates'][- 1][1] < MAX_LAT:
                endpoints.append({
                    'type': "Feature",
                    'properties': {
                        'owner': feature['properties']['OWNER'],
                        'voltclass': feature['properties']['VOLT_CLASS'],
                        'voltage': feature['properties']['VOLTAGE'],
                        'sub2': feature['properties']['SUB_2'],
                        'sub1': feature['properties']['SUB_1'],
                        'start_lon': feature['geometry']['coordinates'][0][0],
                        'start_lat': feature['geometry']['coordinates'][0][1],
                        'end_lon': feature['geometry']['coordinates'][- 1][0],
                        'end_lat': feature['geometry']['coordinates'][- 1][1]
                    },
                    'geometry': feature['geometry'],
                })
        if feature['geometry']['type'] == 'MultiLineString':
            for line in feature['geometry']['coordinates']:
                if line[0][0] > MIN_LON and line[0][0] < MAX_LON and line[0][1] > MIN_LAT and line[0][1] < MAX_LAT:
                    endpoints.append({
                        'type': 'Feature',
                        'properties': {
                            'owner': feature['properties']['OWNER'],
                            'voltclass': feature['properties']['VOLT_CLASS'],
                            'voltage': feature['properties']['VOLTAGE'],
                            'sub2': feature['properties']['SUB_2'],
                            'sub1': feature['properties']['SUB_1'],
                            'start_lon': line[0][0],
                            'start_lat': line[0][1],
                            'end_lon': line[- 1][0],
                            'end_lat': line[- 1][1]
                        },
                        'geometry': feature['geometry'],
                        
                    })
    return endpoints


def stitch_together_price_node_and_transmission_zone():
    # Read input files
    nodes_df = pd.read_csv('src/data/Sheet 4-Table 1.csv')
    # remove blank columns from nodes_df
    nodes_df = nodes_df.dropna(axis=1, how='all')
    porpod = pd.read_csv('src/data/PORPOD2016.csv')
    transformers = pd.read_csv('src/data/transformers.csv')
    # Get unique EMS Key
    valid_zones = set(transformers['EMS Key'])
    
    # Create a mapping of Service Point to Provider
    service_point_to_provider = {}
    for _, row in porpod.iterrows():
        if row['AFC Por'] in valid_zones:
            service_point_to_provider[row['Service Point']] = row['AFC Por']
        else:
            service_point_to_provider[row['Service Point']] = row['Owner TP']
    
    # Function to find provider for a node
    def find_provider(node):
        # First try exact match
        if node in service_point_to_provider:
            return service_point_to_provider[node]
        
        # Try finding a service point that contains this node
        for service_point in service_point_to_provider:
            if (len(node) > 3 and node in service_point) or (len(service_point) > 3 and service_point in node):
                return service_point_to_provider[service_point]
        
        # If no match found, try to extract provider from node name
        if '.' in node:
            potential_provider = node.split('.')[0]
            # Verify this is actually a provider by checking if it exists in our provider list
            if potential_provider in valid_zones:
                return potential_provider
        
        # If no match found with previous methods, try fuzzy matching
        node_clean = ''.join(c.lower() for c in node if c.isalpha())
        if len(node_clean) > 3:  # Only try if we have enough characters
            for service_point in service_point_to_provider:
                service_point_clean = ''.join(c.lower() for c in service_point if c.isalpha())
                if len(service_point_clean) > 3 and (node_clean in service_point_clean or service_point_clean in node_clean):
                    return service_point_to_provider[service_point]
        
        return None

    # Add Provider column to nodes_df
    nodes_df['Zone'] = nodes_df['Node'].apply(find_provider)
    
    # Write the combined data to a new CSV
    nodes_df.to_csv('src/data/price_nodes.csv', index=False)
    
    # Print some statistics
    total_nodes = len(nodes_df)
    matched_nodes = nodes_df['Zone'].notna().sum()
    print(f"Total nodes: {total_nodes}")
    print(f"Matched nodes: {matched_nodes}")
    print(f"Match rate: {matched_nodes/total_nodes*100:.1f}%")
    
    return nodes_df


def filter_geo_json_to_spp_only():
    # Filter to SPP only if we're starting w/ all EIA data
    with open('src/data/transmission_lines.geojson') as f:
        geojson_data = json.load(f)
    spp_geo_json = filter_geo_to_spp_only(geojson_data)
    # Write to spp_only_lines.geojson
    with open('src/data/spp_only_lines.geojson', 'w') as f:
        json.dump(spp_geo_json, f)
    print(f"Wrote {len(spp_geo_json)} endpoints to spp_only_lines.geojson")


def filter_plants_to_spp_only():
    plants_df = pd.read_csv('src/data/Power_Plants.csv')
    plants_df = filter_points_to_spp_only(plants_df)
    plants_df.to_csv('src/data/spp_only_plants.csv', index=False)
    print(f"Wrote {len(plants_df)} plants to spp_only_plants.csv")


if __name__ == "__main__":
    filter_geo_json_to_spp_only()
    filter_plants_to_spp_only()
    # stitch_together_price_node_and_transmission_zone()

