import networkx as nx
from itertools import combinations

# Initialize a 3x3 grid graph and convert labels to integers
G = nx.grid_2d_graph(3, 3)
G = nx.convert_node_labels_to_integers(G)

# Node 4 is fixed (center node), so we don't remove it in initial configurations
original_nodes = set(G.nodes)
remaining_nodes_without_4 = original_nodes - {4}

# Dictionary to store criticality status for each configuration
critical_dict = {}

# Iterate through all possible combinations of node removals (without removing node 4)
for r in range(len(remaining_nodes_without_4) + 1):
    for nodes_to_remove in combinations(remaining_nodes_without_4, r):
        # Define the remaining nodes after removing nodes in nodes_to_remove
        remaining_nodes = tuple(sorted(original_nodes - set(nodes_to_remove)))

        # Make a copy of the graph for this configuration
        G_copy = G.copy()
        G_copy.remove_nodes_from(nodes_to_remove)

        # Count connected components before and after removing node 4
        components_before = nx.number_connected_components(G_copy)
        G_copy.remove_node(4)
        components_after = nx.number_connected_components(G_copy)

        # Mark as critical if removing node 4 increases the number of components
        if components_before < components_after:
            critical_dict[remaining_nodes] = 'critical'
        else:
            critical_dict[remaining_nodes] = 'not_critical'

# Function to check criticality of a given node configuration
def critical_check(tuple_key):
    return critical_dict.get(tuple_key, 'not found')

# Display the results when running the script
if __name__ == '__main__':
    for key, status in critical_dict.items():
        print(f"Configuration {key}: {status}")
