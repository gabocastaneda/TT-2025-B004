# Shim: satisface los pickles que buscan 'models'
from backend.models import *
# backend/models.py
# Este archivo debe proveer los símbolos que el pickle espera.
# Si tu pickle esperaba 'models.knn_model.KNN', nuestro shim lo
# redirige a este módulo y aquí definimos 'KNN'.

from sklearn.neighbors import KNeighborsClassifier as KNN

# Si en el entrenamiento usaste nombres/clases adicionales,
# expórtalas aquí con el mismo nombre:
# from sklearn.preprocessing import StandardScaler as StandardScaler
# etc.
