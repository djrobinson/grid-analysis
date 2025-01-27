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


def filter_to_spp_only(geojson_data):
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



def main():
    # Read input files
    nodes_df = pd.read_csv('src/data/Sheet 4-Table 1.csv')
    plants_df = pd.read_csv('src/data/Power_Plants.csv')
    
    # Filter to SPP only if we're starting w/ all EIA data
    with open('src/data/transmission_lines.geojson') as f:
        geojson_data = json.load(f)
    endpoints = filter_to_spp_only(geojson_data)
    # Write to spp_only_lines.geojson
    with open('src/data/spp_only_lines.geojson', 'w') as f:
        json.dump(endpoints, f)
    print(f"Wrote {len(endpoints)} endpoints to spp_only_lines.geojson")

    # Load spp_only_lines.geojson
    # with open('src/data/spp_only_lines.geojson') as f:
    #     geojson_data = json.load(f)


if __name__ == "__main__":
    main()