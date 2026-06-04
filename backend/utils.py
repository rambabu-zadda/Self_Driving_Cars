# backend/utils.py
import base64
import io
from PIL import Image

def pil_image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def png_bytes_to_datauri(bts: bytes) -> str:
    b64 = base64.b64encode(bts).decode('ascii')
    return f"data:image/png;base64,{b64}"
