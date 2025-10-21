import json

def tolerant_loads(s, *args, **kwargs):
    # Accept and ignore arbitrary kwargs like cls, object_hook, etc.
    if s is None:
        return None
    return json.loads(s)

def tolerant_dumps(obj, *args, **kwargs):
    return json.dumps(obj)
