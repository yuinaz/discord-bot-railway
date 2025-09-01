
import io
from typing import List, Iterable, Optional, Set
try:
    from PIL import Image, ImageSequence, ImageFile, ImageOps, ImageFilter
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except Exception:
    Image = None
    ImageSequence = None
    ImageOps = None
    ImageFilter = None
try:
    import imagehash
except Exception:
    imagehash = None
try:
    import imageio.v2 as imageio
except Exception:
    imageio = None

def _hamming_hex(a: str, b: str) -> int:
    try:
        return (int(a, 16) ^ int(b, 16)).bit_count()
    except Exception:
        return 9999

def _augment_variants(img: "Image.Image", max_extra: int = 4):
    "Yield simple augmented frames: hflip, rot±7deg, center-crop 95%."
    if not Image or not img:
        return
    count = 0
    try:
        if ImageOps and count < max_extra:
            yield ImageOps.mirror(img); count += 1
    except Exception:
        pass
    try:
        if count < max_extra:
            yield img.rotate(7, expand=True, fillcolor=(0,0,0)); count += 1
        if count < max_extra:
            yield img.rotate(-7, expand=True, fillcolor=(0,0,0)); count += 1
    except Exception:
        pass
    try:
        if count < max_extra:
            w, h = img.size
            dw, dh = int(w*0.025), int(h*0.025)  # crop 95% center
            if w-2*dw > 8 and h-2*dh > 8:
                yield img.crop((dw, dh, w-dw, h-dh)); count += 1
    except Exception:
        pass

def phash_list_from_bytes(data: bytes, max_frames: int = 6, augment: bool = False, augment_per_frame: int = 4) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    if not data:
        return out
    def _add(img):
        try:
            if not imagehash or not Image:
                return
            g = img.convert("RGB")
            hs = str(imagehash.phash(g))
            if hs not in seen:
                seen.add(hs); out.append(hs)
            if augment:
                k = 0
                for v in _augment_variants(g, max_extra=augment_per_frame):
                    try:
                        hv = str(imagehash.phash(v))
                        if hv not in seen:
                            seen.add(hv); out.append(hv)
                        k += 1
                        if k >= augment_per_frame:
                            break
                    except Exception:
                        continue
        except Exception:
            pass
    # Pillow first
    if Image:
        try:
            with Image.open(io.BytesIO(data)) as im:
                nframes = getattr(im, "n_frames", 1)
                if nframes > 1 and ImageSequence is not None:
                    step = max(1, nframes // max(1, min(nframes, max_frames)))
                    idxs = list(range(0, nframes, step))[:max_frames]
                    for i in idxs:
                        try:
                            im.seek(i)
                            _add(im.copy())
                        except Exception:
                            continue
                else:
                    _add(im)
                if out:
                    return out
        except Exception:
            pass
    # Fallback: imageio
    if imageio:
        try:
            rdr = imageio.get_reader(io.BytesIO(data), format='WEBP')
            c = 0
            for frm in rdr:
                try:
                    if Image:
                        _add(Image.fromarray(frm))
                    c += 1
                    if c >= max_frames:
                        break
                except Exception:
                    continue
            if out:
                return out
        except Exception:
            try:
                img = imageio.imread(io.BytesIO(data))
                if Image:
                    _add(Image.fromarray(img))
            except Exception:
                pass
    return out

def phash_hit(hashes: Iterable[str], db: Iterable[str], max_distance: int = 0) -> Optional[str]:
    S = list(db) if not isinstance(db, (set, list, tuple)) else db
    for h in hashes:
        if not h:
            continue
        if h in S:
            return h
    if max_distance > 0:
        for h in hashes:
            for d in S:
                if _hamming_hex(h, d) <= max_distance:
                    return d
    return None
