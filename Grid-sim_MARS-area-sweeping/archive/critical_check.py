import networkx as nx
from itertools import combinations

# Initialize the 3x3 grid graph
G = nx.grid_2d_graph(3, 3)
G = nx.convert_node_labels_to_integers(G)

# Node 4 is fixed and will not be removed
original_nodes = set(G.nodes)
remaining_nodes_without_4 = original_nodes - {4}

# Dictionary to store whether each remaining node set is critical or non-critical
critical_dict = {}

# Iterate through all possible combinations of node removals
for r in range(len(remaining_nodes_without_4) + 1):
    for nodes_to_remove in combinations(remaining_nodes_without_4, r):
        # Determine the remaining nodes
        remaining_nodes = tuple(sorted(original_nodes - set(nodes_to_remove)))

        # Make a copy of the graph for each case
        G_copy = G.copy()
        G_copy.remove_nodes_from(nodes_to_remove)

        # Count the number of connected components after removing only the nodes in nodes_to_remove
        components_before_removing_4 = nx.number_connected_components(G_copy)

        # Remove node 4 and count again
        G_copy.remove_node(4)
        components_after_removing_4 = nx.number_connected_components(G_copy)

        # Determine if the removal is critical or non-critical
        if components_before_removing_4 < components_after_removing_4:
            critical_dict[tuple(remaining_nodes)] = 'critical'
        else:
            critical_dict[tuple(remaining_nodes)] = 'not_critical'

# Display the results
def critical_check(tuple_key):
    return critical_dict[tuple_key]

if __name__ == '__main__':
    for key in critical_dict:
        print(key)
