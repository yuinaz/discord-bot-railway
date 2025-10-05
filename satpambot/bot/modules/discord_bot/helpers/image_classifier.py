# Image classifier (scam pattern) via CLIP embeddings + HF Inference API



import json
import os
from typing import List

import requests

HF_API = os.getenv("HF_API", "https://api-inference.huggingface.co")



HF_TOKEN = os.getenv("HF_API_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")



MODEL = os.getenv("IC_MODEL", "openai/clip-vit-base-patch32")



EMB_FILE = os.getenv("IC_EMB_FILE", "data/ic_embeddings.json")



IC_ENABLED = os.getenv("IC_ENABLED", "true").lower() == "true"



IC_THRESHOLD = float(os.getenv("IC_THRESHOLD", "0.28"))  # cosine >= threshold => scam-ish



IC_ACTION = os.getenv("IC_ACTION", "delete")  # delete|ban|kick











def _headers():



    h = {"Accept": "application/json"}



    if HF_TOKEN:



        h["Authorization"] = f"Bearer {HF_TOKEN}"



    return h











def _endpoint():



    return f"{HF_API}/pipeline/feature-extraction/{MODEL}"











def _load_db():



    try:



        with open(EMB_FILE, "r", encoding="utf-8") as f:



            return json.load(f)



    except Exception:



        return {"scam": [], "normal": []}











def _save_db(db):



    os.makedirs(os.path.dirname(EMB_FILE), exist_ok=True)



    with open(EMB_FILE, "w", encoding="utf-8") as f:



        json.dump(db, f, ensure_ascii=False, indent=2)











def _cos(a: List[float], b: List[float]) -> float:



    if not a or not b or len(a) != len(b):



        return 0.0



    import numpy as np







    va = np.array(a, dtype="float32")



    vb = np.array(b, dtype="float32")



    na = np.linalg.norm(va)



    nb = np.linalg.norm(vb)



    if na == 0 or nb == 0:



        return 0.0



    return float((va @ vb) / (na * nb))











def _post_image_get_embedding(image_bytes: bytes) -> List[float]:



    # HF feature-extraction returns vector for the image



    url = _endpoint()



    resp = requests.post(url, headers=_headers(), data=image_bytes, timeout=float(os.getenv("IC_TIMEOUT", "8")))



    resp.raise_for_status()



    data = resp.json()







    # Some backends return nested lists; flatten if needed



    def flatten(x):



        if isinstance(x, list) and x and isinstance(x[0], list):



            return x[0]



        return x







    return list(map(float, flatten(data)))











def add_exemplar(image_bytes: bytes, label: str):



    db = _load_db()



    emb = _post_image_get_embedding(image_bytes)



    if label not in db:



        db[label] = []



    db[label].append(emb)



    _save_db(db)



    return True











def score_scam(image_bytes: bytes) -> float:



    db = _load_db()



    if not db.get("scam"):



        return 0.0



    emb = _post_image_get_embedding(image_bytes)



    # centroid of scam



    import numpy as np







    scam = np.array(db["scam"], dtype="float32")



    centroid = scam.mean(axis=0)



    return _cos(list(centroid), list(emb))











def classify_image(image_bytes: bytes):



    if not IC_ENABLED:



        return {"enabled": False}



    try:



        s = score_scam(image_bytes)



        verdict = "black" if s >= IC_THRESHOLD else "white"



        return {



            "enabled": True,



            "score": s,



            "threshold": IC_THRESHOLD,



            "verdict": verdict,



            "action": IC_ACTION,



        }



    except Exception as e:



        return {"enabled": False, "error": str(e)}



