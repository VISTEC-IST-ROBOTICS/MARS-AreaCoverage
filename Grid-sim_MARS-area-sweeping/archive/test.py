import networkx as nx
import matplotlib.pyplot as plt

# Initialize an empty graph
G = nx.grid_2d_graph(3, 3)

# Convert the graph nodes to a single index for visualization clarity
G = nx.convert_node_labels_to_integers(G)
nodes_to_remove = [ 7,1]
G.remove_nodes_from(nodes_to_remove)
# Draw the graph
pos = {i: (i % 3, i // 3) for i in range(9)}  # Define position for visualization as a grid layout
nx.draw(G, pos, with_labels=True, node_size=700, node_color="lightblue")
print(nx.number_connected_components(G))
plt.show()
