import sys

from PIL import Image


def fit_icon(source: Image.Image, size: int) -> Image.Image:
    subject = source.crop(source.getchannel("A").getbbox())
    scale = size / max(subject.size)
    scaled = subject.resize(
        (round(subject.width * scale), round(subject.height * scale)),
        Image.LANCZOS,
    )
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(
        scaled, ((size - scaled.width) // 2, (size - scaled.height) // 2), scaled
    )
    return canvas


def fit_logo(source: Image.Image, height: int) -> Image.Image:
    subject = source.crop(source.getchannel("A").getbbox())
    scale = height / subject.height
    return subject.resize(
        (round(subject.width * scale), height),
        Image.LANCZOS,
    )


def main() -> None:
    kind, source_path, target_path, size = sys.argv[1:5]
    source = Image.open(source_path).convert("RGBA")
    fitted = (fit_icon if kind == "icon" else fit_logo)(source, int(size))
    fitted.save(target_path, optimize=True)


main()
