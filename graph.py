class Graph():
    """
    Represents a standard directed graph that allows cycle detection.
    The number of nodes must be fixed at the time of graph creation.
    Edges can (and should) be added after the graph is initialized
    """
    def __init__(self, vertices):
        self.V = vertices
        self.E = {v:set() for v in vertices}

    def add_edge(self, from_node, to_node):
        self.E[from_node].add(to_node)

    def neighbors(self, v):
        return self.E[v]

    def reachable_from(self, start):
        visited = {v:False for v in self.V}
        reachable = set()

        # Launches DFS from a given node
        def explore(v):
            visited[v] = True
            reachable.add(v)
            for n in self.neighbors(v):
                if not visited[n]:
                    explore(n)

        # Launch DFS from just the start and return
        explore(start)
        return reachable

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
