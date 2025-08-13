def once(obj, key: str) -> bool:
    """Return True the first time a key is seen on obj; False thereafter."""
    marker = f"_once_marker_{key}"
    if getattr(obj, marker, False):
        return False
    setattr(obj, marker, True)
    return True
