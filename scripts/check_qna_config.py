
# best-effort loader identical to patch behaviour
import os, json

def _load_json(p):
    try:
        with open(p,"r",encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def main():
    base = os.getenv("NEURO_CONFIG_DIR","data/neuro-lite/config")
    found = None
    for name in ("qna_config.json","autolearn_config.json","autolearn.json"):
        p = os.path.join(base, name)
        if os.path.exists(p):
            found = p; break
    print("[qna] base dir:", base)
    if not found:
        print("[qna] config file not found in base dir")
        return
    data = _load_json(found) or {}
    print("[qna] loaded:", found)
    print("[qna] qna_channel_id:", data.get("qna_channel_id"))
    print("[qna] provider_order:", data.get("provider_order"))
    ask = data.get("ask",{}); ans = data.get("answer",{})
    print("[qna] ask:", ask)
    print("[qna] answer:", ans)
    topics = ask.get("topics_file") or "qna_topics.json"
    tp = os.path.join(base, topics)
    print("[qna] topics_path:", tp, "exists:", os.path.exists(tp))

if __name__ == "__main__":
    import os
    main()
