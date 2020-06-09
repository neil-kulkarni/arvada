class Graph():
    """
    Represents a standard directed graph that allows cycle detection.
    The number of nodes must be fixed at the time of graph creation.
    Edges can (and should) be added after the graph is initialized
    """
    def __init__(self, vertices):
        self.V = vertices
        self.E = {v:[] for v in vertices}

    def add_edge(self, from_node, to_node):
        self.E[from_node].append(to_node)

    def neighbors(self, v):
        return self.E[v]

    def is_connected(self):
        visited = {v:False for v in self.V}
        connected_components = 0

        # Launches DFS from a given node
        def explore(v):
            visited[v] = True
            for n in self.neighbors(v):
                if not visited[n]:
                    explore(n)

        # Launches DFS for each connected component in the graph
        for node in self.V:
            if not visited[node]:
                connected_components += 1
                explore(node)

        return connected_components == 1

    def has_cycle(self):
        visited = {v:False for v in self.V}
        has_cycle = False

        # Launches DFS from a given node
        def explore(v):
            nonlocal has_cycle
            visited[v] = True
            for n in self.neighbors(v):
                if not visited[n]:
                    explore(n)
                else:
                    has_cycle = True

        # Launches DFS for each connected component in the graph
        for node in self.V:
            if not visited[node]:
                explore(node)

        return has_cycle
