import json
import os

# Create output directory if it doesn't exist
output_dir = "voltage_classes"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Read the input GeoJSON file
with open('src/data/transmission_lines.geojson', 'r') as f:
    data = json.load(f)

# Initialize dictionaries for each voltage class
voltage_classes = {
    "UNDER 100": {"type": "FeatureCollection", "features": []},
    "100-161": {"type": "FeatureCollection", "features": []},
    "220-287": {"type": "FeatureCollection", "features": []},
    "345": {"type": "FeatureCollection", "features": []},
    "500": {"type": "FeatureCollection", "features": []},
    "735 AND ABOVE": {"type": "FeatureCollection", "features": []}
}

# Sort features into appropriate voltage class files
for feature in data['features']:
    volt_class = feature['properties']['VOLT_CLASS']
    if volt_class in voltage_classes:
        voltage_classes[volt_class]['features'].append(feature)

# Write each voltage class to a separate file
for volt_class, features in voltage_classes.items():
    filename = f"{volt_class.replace('-', '_').replace(' ', '_').lower()}.geojson"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(features, f, indent=2)

print("Files created:")
for filename in os.listdir(output_dir):
    print(f"- {os.path.join(output_dir, filename)}")