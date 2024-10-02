import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class EnhancedSearchGraph:
    def __init__(self):
        self.graph = nx.Graph()
        self.vectorizer = TfidfVectorizer()

    def add_results(self, results):
        for result in results:
            self.graph.add_node(result['url'], **result)
        
        # Create content vectors
        contents = [r['content_preview'] for r in results]
        tfidf_matrix = self.vectorizer.fit_transform(contents)
        
        # Create edges based on content similarity
        for i in range(len(results)):
            for j in range(i+1, len(results)):
                similarity = cosine_similarity(tfidf_matrix[i], tfidf_matrix[j])[0][0]
                if similarity > 0.2:  # Threshold for creating an edge
                    self.graph.add_edge(results[i]['url'], results[j]['url'], weight=similarity)

    def rank_results(self):
        # Use PageRank to rank the results
        pagerank = nx.pagerank(self.graph)
        ranked_results = sorted([(node, pagerank[node], data) for node, data in self.graph.nodes(data=True)], 
                                key=lambda x: x[1], reverse=True)
        return [{'url': node, 'rank': rank, **data} for node, rank, data in ranked_results]

# Integration function
def enhance_search_results(results):
    graph = EnhancedSearchGraph()
    graph.add_results(results)
    return graph.rank_results()