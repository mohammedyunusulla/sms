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
        from PIL import Image, ImageFilter, ImageOps
    except ImportError as exc:  # pragma: no cover - deployment problem
        raise RuntimeError("QR reading isn't installed on the server (zxing-cpp / Pillow)") from exc

    try:
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image)  # phone photos are often stored sideways
        gray = image.convert("L")
    except Exception as exc:
        raise QrReadError("The photo couldn't be opened. Use a JPG or PNG photo.") from exc

    found: List[str] = []
    # Try the full photo first, then smaller copies.
    # On phone photos where the sticker is tiny in a corner, also try top-area crops and high-contrast versions.
    attempts = [gray]
    longest = max(gray.size)
    for target in (2000, 1200):
        if longest > target:
            scale = target / longest
            attempts.append(gray.resize((max(1, int(gray.width * scale)), max(1, int(gray.height * scale)))))

    def _decode(candidate: "Image.Image") -> None:
        nonlocal found
        try:
            results = zxingcpp.read_barcodes(candidate, formats=zxingcpp.BarcodeFormat.QRCode)
        except Exception:
            return
        for result in results:
            text = (result.text or "").strip()
            if text and text not in found:
                found.append(text)

    for candidate in attempts:
        _decode(candidate)
        if found:
            break

        w, h = candidate.size
        top_band = candidate.crop((0, 0, w, max(1, int(h * 0.45))))
        top_left = candidate.crop((0, 0, max(1, int(w * 0.6)), max(1, int(h * 0.6))))
        top_left_tight = candidate.crop((0, 0, max(1, int(w * 0.4)), max(1, int(h * 0.5))))

        for crop in (top_band, top_left, top_left_tight):
            variants = [
                crop,
                ImageOps.autocontrast(crop),
                ImageOps.autocontrast(crop).filter(ImageFilter.SHARPEN),
            ]
            for variant in variants:
                _decode(variant)
                if found:
                    break

                # Stronger upscale helps when QR occupies very few pixels.
                vw, vh = variant.size
                if max(vw, vh) < 1800:
                    enlarged2x = variant.resize((max(1, vw * 2), max(1, vh * 2)))
                    _decode(enlarged2x)
                    if found:
                        break
                    enlarged3x = variant.resize((max(1, vw * 3), max(1, vh * 3)))
                    _decode(enlarged3x)
                    if found:
                        break

                # Binary pass for low-contrast print-on-paper captures.
                bw = variant.point(lambda p: 255 if p > 145 else 0)
                _decode(bw)
                if found:
                    break
            if found:
                break
        if found:
            break
    return found
