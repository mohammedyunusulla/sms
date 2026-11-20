"""
Read QR codes from photographed notebook pages (Homework AI).

The school sticks a pre-printed QR sticker on a notebook page; the student photographs that page blank
at the start and filled in at the end. The server reads the QR itself (it doesn't trust a value sent
by the phone) so the two photos can be matched to the same physical page.
"""
import io
from typing import List


class QrReadError(Exception):
    """The photo couldn't be opened as an image."""


def read_qr_codes(raw: bytes) -> List[str]:
    """Every QR code text found in the photo (empty list when none can be read)."""
    try:
        import zxingcpp
        from PIL import Image, ImageOps
    except ImportError as exc:  # pragma: no cover - deployment problem
        raise RuntimeError("QR reading isn't installed on the server (zxing-cpp / Pillow)") from exc

    try:
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image)  # phone photos are often stored sideways
        gray = image.convert("L")
    except Exception as exc:
        raise QrReadError("The photo couldn't be opened. Use a JPG or PNG photo.") from exc

    found: List[str] = []
    # Try the full photo, then smaller copies (very large phone photos or a small sticker can hide the code)
    attempts = [gray]
    longest = max(gray.size)
    for target in (2000, 1200):
        if longest > target:
            scale = target / longest
            attempts.append(gray.resize((max(1, int(gray.width * scale)), max(1, int(gray.height * scale)))))
    for candidate in attempts:
        try:
            results = zxingcpp.read_barcodes(candidate, formats=zxingcpp.BarcodeFormat.QRCode)
        except Exception:
            continue
        for result in results:
            text = (result.text or "").strip()
            if text and text not in found:
                found.append(text)
        if found:
            break
    return found
