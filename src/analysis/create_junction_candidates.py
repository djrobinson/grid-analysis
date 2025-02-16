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


def find_nodes_edges(nodes_df, plants_df, geo_json):
    # Create a dictionary of all start OR end points 
    # in geo_json that have >2 meetings
    # These are probably substations, but we'll call them "junctions"
    candidates = {}
    all_junctions = {}

    for feature in geo_json['features']:
        if (feature['properties']['start_lon'], feature['properties']['start_lat']) in candidates:
            candidates[(feature['properties']['start_lon'], feature['properties']['start_lat'])] += 1
        else:
            candidates[(feature['properties']['start_lon'], feature['properties']['start_lat'])] = 1
        if (feature['properties']['end_lon'], feature['properties']['end_lat']) in candidates:
            candidates[(feature['properties']['end_lon'], feature['properties']['end_lat'])] += 1
        else:
            candidates[(feature['properties']['end_lon'], feature['properties']['end_lat'])] = 1

    for lon, lat in candidates:

        # Get the properties of the feature
        lines = [feature['properties'] for feature in geo_json['features'] if feature['properties']['start_lon'] == lon and feature['properties']['start_lat'] == lat or feature['properties']['end_lon'] == lon and feature['properties']['end_lat'] == lat]
        # Do properties owner match?
        all_junctions[lon, lat] = {
            'count': len(lines),
            'substation_candidates': [
                substation
                for line in lines
                for substation in (line['sub1'], line['sub2'])
            ],
            # Remove any voltage of -999999
            'voltages':  list(set([line['voltage'] for line in lines if line['voltage'] != -999999])),
            # Remove any voltclass == 'NOT AVAILABLE'
            'volt_classes': list(set([line['voltclass'] for line in lines if line['voltclass'] != 'NOT AVAILABLE']))
        }
    # Now, to determine substation for junction, we take the substation_cadidates and the one with the most occurrences in the list
    for junction in all_junctions:
        new_substation_candidates = all_junctions[junction]['substation_candidates']
        # Count occurrences of each substation
        substation_counts = {substation: new_substation_candidates.count(substation) for substation in new_substation_candidates}
        # Sort by count descending
        substation_counts = sorted(substation_counts.items(), key=lambda x: x[1], reverse=True)
        all_junctions[junction]['substation'] = substation_counts[0][0]
    
    # Lets' filter down based on 3 things
    # 1. if the junction connects to multiple voltages
    # 2. if there are >3 lines
    # 3. if the substation name doesn't start with "TAP", "UNKNOWN", or "NOT AVAILABLE"
    # 4. If the junctino only has a single line. Label this junction as an "endpoint" (not sure this is useful)

    junctions = {}
    for junction in all_junctions:
        if len(all_junctions[junction]['volt_classes']) > 1:
            junctions[junction] = {
                'type': 'transformer',
                'count': all_junctions[junction]['count'],
                'substation': all_junctions[junction]['substation'],
                'substation_candidates': all_junctions[junction]['substation_candidates'],
                'voltages': all_junctions[junction]['voltages'],
                'volt_classes': all_junctions[junction]['volt_classes']
            }
        elif all_junctions[junction]['count'] > 2 and not (all_junctions[junction]['substation'].startswith("TAP") or all_junctions[junction]['substation'].startswith("UNKNOWN") or all_junctions[junction]['substation'].startswith("NOT AVAILABLE")):
            junctions[junction] = {
                'type': 'junction',
                'count': all_junctions[junction]['count'],
                'substation': all_junctions[junction]['substation'],
                'substation_candidates': all_junctions[junction]['substation_candidates'],
                'voltages': all_junctions[junction]['voltages'],
                'volt_classes': all_junctions[junction]['volt_classes']
            }
        # elif all_junctions[junction]['count'] == 1:
        #     junctions[junction] = {
        #         'type': 'endpoint',
        #         'count': 1,
        #         'substation': 'endpoint',
        #         'substation_candidates': all_junctions[junction]['substation_candidates'],
        #         'voltages': all_junctions[junction]['voltages']
        #     }


    print(len(junctions))
    # Write to junctions.json
    with open('src/data/junctions.json', 'w') as f:
        # first stringify the tuple keys
        junctions_str = {str(k): v for k, v in junctions.items()}
        json.dump(junctions_str, f)
    
    # found_nodes_multiple = []
    # found_nodes_single = []
    # unmapped_nodes = []
    # threshold_distance = 1
    # # Find start/end points that map to a node
    # for _, node in nodes_df.iterrows():
    #     found = False
    #     candidates_for_node = {}
    #     # Get haversine distance to all junctions
    #     for junction in junctions:
    #         distance = haversine_distance(node['Lon'], node['Lat'], junction[0], junction[1])
    #         if distance < threshold_distance:
    #             candidates_for_node[junction] = distance
    #     #  Find closest from list
    #     if len(candidates_for_node) > 1:
    #         # sort by distance ascending
    #         candidates_for_node = sorted(candidates_for_node.items(), key=lambda x: x[1])
    #         found_nodes_multiple.append(candidates_for_node[0])
    #         found = True

    #     # found_nodes_multiple.append(node)

    #     if not found:
    #         for candidate in candidates:
    #             distance = haversine_distance(node['Lon'], node['Lat'], candidate[0], candidate[1])
    #             if distance < threshold_distance:
    #                 candidates_for_node[junction] = distance
    #         if len(candidates_for_node) > 1:
    #             # sort by distance ascending
    #             candidates_for_node = sorted(candidates_for_node.items(), key=lambda x: x[1])
    #             found_nodes_single.append(candidates_for_node[0])
    #             found = True
            

    #     if not found:
    #         unmapped_nodes.append(node)

    # print('FOUND MULTIPLE:', len(found_nodes_multiple))
    # print('FOUND SINGLE:', len(found_nodes_single))
    # print('UNMAPPED:', len(unmapped_nodes))



    # found_plants = []
    # # Find start/end points that map to a plant
    # for _, plant in plants_df.iterrows():
    #     found = False
    #     candidates_for_plant = {}
    #     for junction in junctions:
    #         distance = haversine_distance(plant['Longitude'], plant['Latitude'], junction[0], junction[1])
    #         if distance < threshold_distance:
    #             candidates_for_plant[junction] = distance 
    #     if len(candidates_for_plant) > 1:
    #         candidates_for_plant = sorted(candidates_for_plant.items(), key=lambda x: x[1])
    #         found_plants.append(candidates_for_plant[0])
    #         found = True
    #     if not found:
    #         for candidate in candidates:
    #             distance = haversine_distance(plant['Longitude'], plant['Latitude'], candidate[0], candidate[1])
    #             if distance < threshold_distance:
    #                 candidates_for_plant[junction] = distance
    #         if len(candidates_for_plant) > 1:
    #             candidates_for_plant = sorted(candidates_for_plant.items(), key=lambda x: x[1])
    #             found_plants.append(candidates_for_plant[0])
    #             found = True

    # Create a combined nodes dataframe
    combined_nodes = []

    # Start with junctions as base nodes
    for junction_coords, junction_data in junctions.items():
        node_entry = {
            # Junction attributes
            'longitude': junction_coords[0],
            'latitude': junction_coords[1],
            'substation_name': junction_data['substation'],
            'connection_count': junction_data['count'],
            'voltages': junction_data['voltages'],
            'volt_classes': junction_data['volt_classes'],
            # Initialize other type fields as None
            'price_node': None,
            'price_node_distance': None,
            'price_node_zone': None,
            'plant_name': None,
            'plant_code': None,
            'utility_name': None,
            'primary_source': None,
            'total_mw': None,
            'battery_mw': None,
            'bio_mw': None,
            'coal_mw': None,
            'geo_mw': None,
            'hydro_mw': None,
            'hydrops_mw': None,
            'ng_mw': None,
            'nuclear_mw': None,
            'crude_mw': None,
            'solar_mw': None,
            'wind_mw': None,
            'other_mw': None
        }
        combined_nodes.append(node_entry)
    
    # Match price nodes to existing nodes or create new entries
    for node in combined_nodes:
        closest_node = None
        min_dist = float('inf')
        # Find closest existing node
        for _, price_node in nodes_df.iterrows():
            dist = haversine_distance(
                price_node['Lat'], price_node['Lon'], 
                node['latitude'], node['longitude']
            )
            if dist < min_dist:
                min_dist = dist
                closest_node = price_node
        
        if closest_node is not None:
            node['price_node'] = closest_node['Node']
            node['price_node_distance'] = min_dist
            node['price_node_zone'] = closest_node['Zone']
    
    # Match plants to existing nodes or create new entries
    for node in combined_nodes:
        closest_node = None
        min_dist = float('inf')
        for _, plant in plants_df.iterrows():
        # First try to match to existing nodes
            dist = haversine_distance(
                plant['Latitude'], plant['Longitude'],
                node['latitude'], node['longitude']
            )
            if dist < min_dist:
                min_dist = dist
                closest_node = plant
        
        if closest_node is not None:
            node['plant_name'] = closest_node['Plant_Name']
            node['plant_distance'] = min_dist
            node['plant_code'] = closest_node['Plant_Code']
            node['utility_name'] = closest_node['Utility_Name']
            node['primary_source'] = closest_node['PrimSource']
            node['total_mw'] = closest_node['Total_MW']
            node['battery_mw'] = closest_node['Bat_MW']
            node['bio_mw'] = plant['Bio_MW']
            node['coal_mw'] = plant['Coal_MW']
            node['geo_mw'] = plant['Geo_MW']
            node['hydro_mw'] = plant['Hydro_MW']
            node['hydrops_mw'] = plant['HydroPS_MW']
            node['ng_mw'] = plant['NG_MW']
            node['nuclear_mw'] = plant['Nuclear_MW']
            node['crude_mw'] = plant['Crude_MW']
            node['solar_mw'] = plant['Solar_MW']
            node['wind_mw'] = plant['Wind_MW']
            node['other_mw'] = plant['Other_MW']

    
    # Convert to dataframe and write to CSV
    combined_df = pd.DataFrame(combined_nodes)
    
    # Filter to only keep nodes with junction data
    combined_df = combined_df[combined_df['substation_name'].notna()]
    
    combined_df.to_csv('src/data/combined_nodes.csv', index=False)
    print(f"Wrote {len(combined_df)} combined nodes to combined_nodes.csv")
    
    return combined_df


def main():
    # Read input files
    nodes_df = pd.read_csv('src/data/price_nodes.csv')
    plants_df = pd.read_csv('src/data/spp_only_plants.csv')

    # Load spp_only_lines.geojson
    with open('src/data/spp_only_lines.geojson') as f:
        geojson_data = json.load(f)
    find_nodes_edges(nodes_df, plants_df, geojson_data)


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
    # filter_geo_json_to_spp_only()
    # filter_plants_to_spp_only()
    # stitch_together_price_node_and_transmission_zone()
    main()
