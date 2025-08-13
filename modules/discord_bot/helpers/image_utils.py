from PIL import Image

def compress_image(image: Image.Image, max_size=(500, 500)) -> Image.Image:
    image.thumbnail(max_size)
    return image

def convert_to_rgb(image: Image.Image) -> Image.Image:
    if image.mode != "RGB":
        return image.convert("RGB")
    return image
