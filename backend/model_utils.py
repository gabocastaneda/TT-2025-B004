# backend/model_utils.py
import numpy as np

class SimpleScaler:
    def __init__(self):
        self.mean_ = None
        self.std_ = None
    
    def fit(self, X):
        self.mean_ = np.mean(X, axis=0)
        self.std_ = np.std(X, axis=0)
        return self
    
    def transform(self, X):
        return (X - self.mean_) / (self.std_ + 1e-8)
    
    def fit_transform(self, X):
        return self.fit(X).transform(X)

class SimpleLabelEncoder:
    def __init__(self):
        self.classes_ = None
        self.mapping_ = {}
    
    def fit(self, y):
        self.classes_ = np.unique(y)
        self.mapping_ = {cls: i for i, cls in enumerate(self.classes_)}
        return self
    
    def transform(self, y):
        return np.array([self.mapping_[val] for val in y])
    
    def inverse_transform(self, y):
        reverse_mapping = {v: k for k, v in self.mapping_.items()}
        return np.array([reverse_mapping[val] for val in y])