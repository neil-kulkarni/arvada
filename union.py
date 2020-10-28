"""
No longer used.
"""

class UnionFind():
    """
    WeightedQuickUnion data structure for connectivity that also supplies a
    reverse mapping in order to isolate each class.
    """
    def __init__(self, vertices):
        self.parent = {v:v for v in vertices}
        self.size = {v:1 for v in vertices}
        self.followers = {v:[v] for v in vertices}

    def find(self, p):
        """
        Helper method that finds the `boss` of a vertex.
        """
        if p == self.parent[p]:
            return p
        self.parent[p] = self.find(self.parent[p])
        return self.parent[p]

    def connect(self, p, q):
        """
        Connects vertices p and q.
        """
        i, j = self.find(p), self.find(q)
        if i == j:
            return
        if self.size[i] < self.size[j]:
            self.parent[i] = j
            self.size[j] += self.size[i]
            self.followers[j] += self.followers[i]
            self.followers.pop(i)
        else:
            self.parent[j] = i
            self.size[i] += self.size[j]
            self.followers[i] += self.followers[j]
            self.followers.pop(j)

    def is_connected(self, p, q):
        """
        Checks whether vertices p and q are connected.
        """
        return self.find(p) == self.find(q)

    def classes(self):
        """
        Returns a view inside the classes mapping.
        """
        return self.followers
