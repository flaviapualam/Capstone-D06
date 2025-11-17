# ml/isolation_forest.py
import numpy as np
import random
import math
from typing import List

class Node:
    """Sebuah node di dalam Isolation Tree."""
    def __init__(self, is_leaf: bool, size: int = 0, 
                 split_feature: int = None, split_value: float = None, 
                 left_child=None, right_child=None):
        self.is_leaf = is_leaf
        self.size = size  # Jumlah sampel di leaf node
        self.split_feature = split_feature
        self.split_value = split_value
        self.left_child = left_child
        self.right_child = right_child

class IsolationTree:
    """Implementasi 'from scratch' dari satu Isolation Tree."""
    def __init__(self, max_depth: int):
        self.max_depth = max_depth
        self.root: Node = None

    def fit(self, X: np.ndarray):
        """Melatih tree pada data subsample."""
        self.root = self._build_tree(X, 0)

    def _build_tree(self, X: np.ndarray, current_height: int) -> Node:
        # Kasus terminasi (menjadi leaf node)
        if current_height >= self.max_depth or len(X) <= 1:
            return Node(is_leaf=True, size=len(X))

        n_samples, n_features = X.shape
        
        # 1. Pilih fitur secara acak
        split_feature = random.randint(0, n_features - 1)
        
        # 2. Ambil nilai min/max dari fitur itu
        min_val = np.min(X[:, split_feature])
        max_val = np.max(X[:, split_feature])

        # Jika semua nilai sama, kita tidak bisa membaginya
        if min_val == max_val:
            return Node(is_leaf=True, size=len(X))

        # 3. Pilih nilai split secara acak di antara min/max
        split_value = random.uniform(min_val, max_val)

        # 4. Bagi data
        idx_left = X[:, split_feature] <= split_value
        idx_right = X[:, split_feature] > split_value

        # Pastikan kita tidak membuat infinite loop (jika salah satu sisi kosong)
        if not np.any(idx_left) or not np.any(idx_right):
            return Node(is_leaf=True, size=len(X))

        # 5. Rekursif
        left_child = self._build_tree(X[idx_left], current_height + 1)
        right_child = self._build_tree(X[idx_right], current_height + 1)

        return Node(
            is_leaf=False,
            split_feature=split_feature,
            split_value=split_value,
            left_child=left_child,
            right_child=right_child
        )

    def _get_path_length(self, x: np.ndarray, node: Node, current_height: int) -> int:
        """Menghitung path length untuk satu sampel."""
        if node.is_leaf:
            # Kita tidak menggunakan 'c(n)' adjustment agar tetap sederhana
            return current_height
        
        if x[node.split_feature] <= node.split_value:
            return self._get_path_length(x, node.left_child, current_height + 1)
        else:
            return self._get_path_length(x, node.right_child, current_height + 1)

    def get_path_length(self, x: np.ndarray) -> int:
        """Wrapper publik untuk path length."""
        if self.root is None:
            return 0
        return self._get_path_length(x, self.root, 0)

class IsolationForest:
    """
    Implementasi 'from scratch' dari Isolation Forest.
    Kompatibel dengan API scikit-learn (fit, predict, score_samples).
    """
    def __init__(self, n_estimators: int = 100, subsample_size: int = 256, contamination: float = 0.05):
        self.n_estimators = n_estimators
        self.subsample_size = subsample_size
        self.contamination = contamination
        self.trees: List[IsolationTree] = []
        self.max_depth: int = 0
        self.threshold_: float = 0.0 # Threshold untuk anomali

    def fit(self, X: np.ndarray):
        """Melatih Isolation Forest."""
        self.trees = []
        n_samples = len(X)
        
        if self.subsample_size > n_samples:
            self.subsample_size = n_samples
            
        self.max_depth = math.ceil(math.log2(self.subsample_size))
        
        for _ in range(self.n_estimators):
            # 1. Ambil subsample
            idx = np.random.choice(n_samples, self.subsample_size, replace=False)
            X_sub = X[idx]
            
            # 2. Latih satu tree
            tree = IsolationTree(self.max_depth)
            tree.fit(X_sub)
            self.trees.append(tree)

        # 3. Hitung threshold berdasarkan kontaminasi
        scores = self.score_samples(X)
        # Ambil skor di persentil 'contamination'
        self.threshold_ = np.percentile(scores, self.contamination * 100)
        
        return self

    def _get_avg_path_length(self, x: np.ndarray) -> float:
        """Mendapatkan rata-rata path length di semua tree."""
        total_path_length = 0
        for tree in self.trees:
            total_path_length += tree.get_path_length(x)
        return total_path_length / self.n_estimators

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """
        Menghitung skor anomali. 
        Mengikuti konvensi sklearn: anomali memiliki SKOR LEBIH RENDAH.
        Kita kembalikan -avg_path_length.
        """
        scores = [self._get_avg_path_length(x) for x in X]
        # Skor adalah negatif dari rata-rata path length
        # Path pendek (anomali) -> skor mendekati 0
        # Path panjang (normal) -> skor sangat negatif
        return -np.array(scores)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Memprediksi apakah anomali (-1) atau normal (1).
        """
        scores = self.score_samples(X)
        # Jika skor > threshold (lebih mendekati 0), itu anomali
        return np.where(scores > self.threshold_, -1, 1)