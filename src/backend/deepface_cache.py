# backend/deepface_cache.py
"""
Cache de embeddings para acelerar comparações faciais.
Guarda embeddings em memória e persiste em arquivo (representations.pkl).
Fornece funções para construir, atualizar e consultar o cache.
"""

import os
import pickle
from deepface import DeepFace
import numpy as np
from typing import Dict, List, Tuple

CACHE_FILE = "backend/deepface_representations.pkl"
# Modelo recomendado: "SFace" ou "MobileFaceNet" (mais rápido que VGG-Face)
MODEL_NAME = "SFace"
METRIC = "cosine"  # distância de similaridade (menor = mais parecido)

class DeepFaceCache:
    def __init__(self, model_name=MODEL_NAME, metric=METRIC):
        self.model_name = model_name
        self.metric = metric
        # mapa: image_path -> embedding (numpy array)
        self.reps: Dict[str, np.ndarray] = {}
        self._load()

    def _load(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "rb") as f:
                    data = pickle.load(f)
                # garantir compatibilidade
                if isinstance(data, dict):
                    self.reps = {k: np.array(v) for k, v in data.items()}
            except Exception:
                self.reps = {}

    def _save(self):
        # salva vetor serializável
        to_save = {k: v.tolist() for k, v in self.reps.items()}
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(to_save, f)

    def build_from_paths(self, paths: List[str], enforce_rebuild=False):
        """Cria/atualiza cache para a lista de caminhos.
           Se enforce_rebuild True, recalcula tudo."""
        to_compute = []
        if enforce_rebuild:
            self.reps = {}
            to_compute = paths
        else:
            to_compute = [p for p in paths if p not in self.reps and os.path.exists(p)]

        for p in to_compute:
            try:
                rep = DeepFace.represent(img_path=p, model_name=self.model_name, enforce_detection=False)
                # DeepFace.represent retorna lista de dicts (por modelo) ou vetor; adaptar:
                if isinstance(rep, list):
                    rep = rep[0]["embedding"]
                self.reps[p] = np.array(rep)
            except Exception:
                # ignora imagens que não processam
                continue

        self._save()

    def update_single(self, img_path: str):
        """Atualiza cache com um único arquivo (usado ao cadastrar usuário)."""
        try:
            rep = DeepFace.represent(img_path=img_path, model_name=self.model_name, enforce_detection=False)
            if isinstance(rep, list):
                rep = rep[0]["embedding"]
            self.reps[img_path] = np.array(rep)
            self._save()
        except Exception:
            pass

    def find_best_match(self, probe_path: str, threshold=0.35) -> Tuple[str, float] or None:
        """Compara probe_path com todos no cache e retorna (best_path, distance) ou None.
           A distância retornada segue a métrica escolhida (cosine)."""
        if not self.reps:
            return None

        try:
            probe_rep = DeepFace.represent(img_path=probe_path, model_name=self.model_name, enforce_detection=False)
            if isinstance(probe_rep, list):
                probe_rep = np.array(probe_rep[0]["embedding"])
            else:
                probe_rep = np.array(probe_rep)
        except Exception:
            return None

        best_path = None
        best_dist = float("inf")

        # cálculo vetorial rápido — usamos cosine (1 - cosine similarity)
        from numpy.linalg import norm
        for path, db_vec in self.reps.items():
            # distância cosine: 1 - (a.b / (||a||*||b||))
            try:
                denom = (norm(db_vec) * norm(probe_rep))
                if denom == 0:
                    continue
                cosine_sim = np.dot(db_vec, probe_rep) / denom
                dist = 1.0 - cosine_sim
            except Exception:
                continue

            if dist < best_dist:
                best_dist = dist
                best_path = path

        if best_path is not None and best_dist <= threshold:
            return (best_path, float(best_dist))
        return None

# Instância global (importar e reutilizar)
_cache = DeepFaceCache()

def get_cache():
    return _cache
