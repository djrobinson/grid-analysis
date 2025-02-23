import pandas as pd
import networkx as nx
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

class NetworkAnalyzer:
    """Analyzes SPP network topology from constraint data."""
    
    def __init__(self):
        self.G = nx.Graph()
        self.voltage_levels: Dict[str, Set[int]] = {}
        self.companies: Dict[str, Set[str]] = {}
        
    def parse_facility(self, facility_str: str) -> Tuple[List[str], List[float], str]:
        """
        Parse facility string to extract nodes, voltages, and company.
        
        Example inputs:
        - "LN FLOURNOY - WOOLWORT" -> (["FLOURNOY", "WOOLWORT"], [], None)
        - "CSWS:LEASIDE SWSHREV:138:1:9" -> (["LEASIDE", "SWSHREV"], [138.0], "CSWS")
        - "OKGE:WDWRD1 XF A:138 69:1:5" -> (["WDWRD1", "XF A"], [138.0, 69.0], "OKGE")
        - "WAUE:BELFELD XF KU1A3:345 230 13.8" -> (["BELFELD", "XF KU1A3"], [345.0, 230.0, 13.8], "WAUE")
        - "SPS:HOBBS:COMBINEDCYCLE" -> (["HOBBS"], [], "SPS")
        """
        # Parse detailed format (company:node1 node2:voltage:...)
        if ':' in str(facility_str):
            parts = facility_str.split(':')
            company = parts[0]
            nodes = parts[1].split()
            
            # Handle multiple voltage levels, including decimals
            voltages = []
            if len(parts) > 2:
                try:
                    voltages = [float(v) for v in parts[2].split()]
                except ValueError:
                    # If voltage parsing fails, just continue with empty voltages
                    pass
                
            return nodes, voltages, company
            
        # Parse simple format (LN/XFMR NODE1 - NODE2)
        else:
            nodes = [n.strip() for n in facility_str.split('-')]
            if nodes[0].startswith(('LN ', 'XFMR ')):
                nodes[0] = nodes[0].split(' ', 1)[1].strip()
            return nodes, [], None

    def add_constraint_to_network(self, row: pd.Series) -> None:
        """Add a single constraint's information to the network."""
        # Parse monitored facility
        mon_nodes, mon_voltages, mon_company = self.parse_facility(str(row['Monitored Facility']))
        
        # Parse contingent facility if not BASE
        if row['Contingent Facility'] != 'BASE':
            cont_nodes, cont_voltages, cont_company = self.parse_facility(str(row['Contingent Facility']))
        else:
            cont_nodes, cont_voltages, cont_company = [], [], None
        
        # Add nodes and edges to network
        # for nodes, voltages, company in [(mon_nodes, mon_voltages, mon_company)]:
        for nodes, voltages, company in [(cont_nodes, cont_voltages, cont_company)]:
            if not nodes:
                continue
                
            # Add nodes with attributes
            for node in nodes:
                if node not in self.G:
                    self.G.add_node(node, voltages=set(), companies=set())
                
                if voltages:
                    self.G.nodes[node]['voltages'].update(voltages)
                if company:
                    self.G.nodes[node]['companies'].add(company)
            
            # Add edge between nodes if it's a pair
            if len(nodes) == 2:
                self.G.add_edge(nodes[0], nodes[1], 
                              voltages=set(voltages),
                              company=company)

    def build_network(self, constraints_df: pd.DataFrame) -> None:
        """Build network from constraints dataframe."""
        for _, row in constraints_df.iterrows():
            self.add_constraint_to_network(row)
            
    def get_network_statistics(self) -> Dict:
        """Get basic statistics about the network."""
        return {
            'num_nodes': self.G.number_of_nodes(),
            'num_edges': self.G.number_of_edges(),
            'num_components': nx.number_connected_components(self.G),
            'voltage_levels': sorted(set.union(*[data['voltages'] 
                                               for _, data in self.G.nodes(data=True)])),
            'companies': sorted(set.union(*[data['companies'] 
                                          for _, data in self.G.nodes(data=True)]))
        }

def main():
    """Example usage of NetworkAnalyzer."""
    # Load constraint data
    data_path = Path("src/data/rt_constraints_20250101.csv")
    constraints_df = pd.read_csv(data_path)
    
    # Create analyzer and build network
    analyzer = NetworkAnalyzer()
    analyzer.build_network(constraints_df)
    
    # Print statistics
    stats = analyzer.get_network_statistics()
    print("\nNetwork Statistics:")
    print([c for c in sorted(nx.connected_components(analyzer.G), key=len, reverse=True)])
    print("Isolated nodes: ", list(nx.isolates(analyzer.G)))
    print(f"Nodes: {stats['num_nodes']}")
    print(f"Edges: {stats['num_edges']}")
    print(f"Connected Components: {stats['num_components']}")

    print(f"\nVoltage Levels: {stats['voltage_levels']}")
    print(f"\nCompanies: {stats['companies']}")

if __name__ == "__main__":
    main() 