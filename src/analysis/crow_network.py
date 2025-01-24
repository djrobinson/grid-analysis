import pandas as pd
import networkx as nx

# Load the CSV file into a DataFrame
file_path_lines = 'src/data/CROW_to_Offline_Model_Mapping_9-20-2024-v2/Lines-Table 1.csv'
df_lines = pd.read_csv(file_path_lines)

# Load the transformer CSV file into a DataFrame
file_path_transformers = 'src/data/CROW_to_Offline_Model_Mapping_9-20-2024-v2/Transformers-Table 1.csv'
df_transformers = pd.read_csv(file_path_transformers)

# Create a directed graph
G = nx.DiGraph()

# Add edges to the graph using the bus numbers, and set the bus names as node attributes
for _, row in df_lines.iterrows():
    from_bus_name = row['IDC From Bus Name']
    to_bus_name = row['IDC To Bus Name']
    
    # Add nodes with bus names as attributes
    G.add_node(from_bus_name, name=from_bus_name)
    G.add_node(to_bus_name, name=to_bus_name)
    
    # Add edge between the nodes
    G.add_edge(from_bus_name, to_bus_name)

# Add transformer connections to the graph
for _, row in df_transformers.iterrows():
    high_bus_name = row['IDC High Bus Name']
    low_bus_name = row['IDC Low Bus Name']
    terr_bus_name = row['IDC Terr Bus Name']
    
    # Add nodes with bus names as attributes
    G.add_node(high_bus_name, name=high_bus_name)
    G.add_node(low_bus_name, name=low_bus_name)
    
    # Add edge between high and low bus
    G.add_edge(high_bus_name, low_bus_name)
    
    # If a tertiary bus is available, add it and create an edge
    if pd.notna(terr_bus_name):
        G.add_node(terr_bus_name, name=terr_bus_name)
        G.add_edge(low_bus_name, terr_bus_name)

# Print out the stats about the network
print("Number of nodes:", G.number_of_nodes())
print("Number of edges:", G.number_of_edges())

# Find connected components
connected_components = list(nx.connected_components(G.to_undirected()))
print("Number of connected components:", len(connected_components))
print([len(c) for c in sorted(nx.connected_components(G.to_undirected()), key=len, reverse=True)])

# Find isolates
isolates = list(nx.isolates(G.to_undirected()))
print("Number of isolates:", len(isolates))

# Print the isolates with their names
if isolates:
    print("Isolates:")
    for isolate in isolates:
        print(f"Bus Number: {isolate}, Bus Name: {G.nodes[isolate]['name']}")
else:
    print("No isolates found.")