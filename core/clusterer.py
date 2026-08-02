import numpy as np
from sklearn.cluster import DBSCAN

class FaceClusterer:
    def __init__(self, eps=0.45, min_samples=1):
        """
        Initialize the DBSCAN clusterer.
        
        :param eps: The maximum distance between two samples for one to be considered as in the neighborhood of the other.
                    Since we use 'cosine' distance, the distance is 1 - cosine_similarity.
                    Values between 0.4 and 0.5 usually work well for buffalo_l embeddings.
        :param min_samples: Minimum number of samples to form a cluster. Set to 1 to allow single-image "clusters" (people appearing only once).
        """
        self.clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
        
    def cluster(self, embeddings: list) -> list:
        """
        Cluster a list of face embeddings.
        
        :param embeddings: List of 1D numpy arrays (512-dimensional embeddings)
        :return: List of cluster labels. Faces with the same label belong to the same person.
        """
        if not embeddings:
            return []
            
        # Stack embeddings into a 2D array (N_samples, N_features)
        X = np.vstack(embeddings)
        
        # Fit and predict cluster labels
        labels = self.clusterer.fit_predict(X)
        
        return labels.tolist()
