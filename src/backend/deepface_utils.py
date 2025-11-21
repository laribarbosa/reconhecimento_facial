# backend/deepface_utils.py
from deepface import DeepFace
from backend.deepface_cache import get_cache
import os

# parâmetros
MODEL_NAME = "SFace"   # ou "MobileFaceNet"
THRESHOLD = 0.35

def reconhecer_usuario(img_path, db_paths=None):
    """
    Versão otimizada de reconhecimento:
    - Usa cache (deepface_cache) para comparar embeddings rapidamente.
    - Se cache vazio, tenta construir cache a partir de db_paths.
    - Retorna {"db_img": path, "distance": dist} ou None.
    """
    cache = get_cache()

    # Se cache vazio e foram passados db_paths, construir cache
    if not cache.reps and db_paths:
        cache.build_from_paths(db_paths)

    # Tenta matching usando cache
    best = cache.find_best_match(img_path, threshold=THRESHOLD)
    if best:
        path, dist = best
        return {"db_img": path, "distance": dist}

    # Se não encontrou via cache (ou cache falhou), faz fallback em verificação direta
    if db_paths:
        results = []
        for db_img in db_paths:
            try:
                result = DeepFace.verify(img_path, db_img, model_name=MODEL_NAME, enforce_detection=False)
                if result.get("verified"):
                    results.append({"db_img": db_img, "distance": result.get("distance", 0)})
            except Exception:
                continue
        if results:
            return min(results, key=lambda x: x["distance"])
    return None
