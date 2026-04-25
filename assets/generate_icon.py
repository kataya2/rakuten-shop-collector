"""Generate assets/icon.ico for PyInstaller packaging."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 32, 48, 64, 128, 256]
_RED = "#BF0000"
_OUTPUT = Path(__file__).parent / "icon.ico"


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_size = max(8, int(size * 0.55))
    for candidate in [
        "arialbd.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "arial.ttf",
    ]:
        try:
            return ImageFont.truetype(candidate, font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def _make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    m = max(1, size // 8)
    draw.rounded_rectangle(
        [m, m, size - m - 1, size - m - 1],
        radius=max(2, size // 8),
        fill=_RED,
    )
    font = _get_font(size)
    bbox = draw.textbbox((0, 0), "R", font=font)
    x = (size - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (size - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), "R", fill="white", font=font)
    return img


def main() -> None:
    img = _make_frame(256)
    img.save(_OUTPUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"Generated: {_OUTPUT}")


if __name__ == "__main__":
    main()
