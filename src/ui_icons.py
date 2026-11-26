"""Small locally drawn line icons for primary chat controls."""

from PIL import Image, ImageDraw
import customtkinter


def create_icon(name: str, color: str, size: int = 20) -> customtkinter.CTkImage:
    """Create a compact, dependency-free line icon as a CustomTkinter image."""
    scale = 3
    image = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    stroke = max(2, size // 9) * scale

    def point(x, y):
        return (int(x * scale), int(y * scale))

    if name == "send":
        draw.line(
            [point(2, size / 2), point(size - 2, size / 2),
             point(size * 0.58, size * 0.18)],
            fill=color,
            width=stroke,
            joint="curve",
        )
        draw.line(
            [point(size - 2, size / 2), point(size * 0.58, size * 0.82)],
            fill=color,
            width=stroke,
        )
        draw.line(
            [point(2, size / 2), point(size * 0.18, size * 0.68)],
            fill=color,
            width=stroke,
        )
        draw.line(
            [point(2, size / 2), point(size * 0.18, size * 0.32)],
            fill=color,
            width=stroke,
        )
    elif name == "mic":
        draw.rounded_rectangle(
            (point(size * 0.38, size * 0.12), point(size * 0.62, size * 0.62)),
            radius=stroke * 2,
            outline=color,
            width=stroke,
        )
        draw.arc(
            (point(size * 0.22, size * 0.32), point(size * 0.78, size * 0.82)),
            start=0,
            end=180,
            fill=color,
            width=stroke,
        )
        draw.line(
            [point(size / 2, size * 0.82), point(size / 2, size * 0.96)],
            fill=color,
            width=stroke,
        )
        draw.line(
            [point(size * 0.34, size * 0.96), point(size * 0.66, size * 0.96)],
            fill=color,
            width=stroke,
        )
    else:
        raise ValueError(f"Unknown icon: {name}")

    image = image.resize((size, size), Image.Resampling.LANCZOS)
    return customtkinter.CTkImage(light_image=image, dark_image=image, size=(size, size))
