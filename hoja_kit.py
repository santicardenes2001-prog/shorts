"""Hoja de contacto con todos los recursos del kit."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit", "png")
names = sorted(n[:-4] for n in os.listdir(D) if n.endswith(".png"))
skip_prefix = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ()
names = [n for n in names if not n.startswith(skip_prefix)]
cell, cols = 300, 6
rows = (len(names) + cols - 1) // cols
font = ImageFont.truetype(os.path.join(os.path.dirname(D), "..", "fonts", "LilitaOne-Regular.ttf"), 22)
sheet = Image.new("RGB", (cols * cell, rows * (cell + 34)), "#EDE7DD")
d = ImageDraw.Draw(sheet)
for i, n in enumerate(names):
    im = Image.open(os.path.join(D, n + ".png")).convert("RGBA")
    im.thumbnail((cell - 20, cell - 20))
    x, y = (i % cols) * cell, (i // cols) * (cell + 34)
    d.rectangle([x + 4, y + 4, x + cell - 4, y + cell - 4], fill="#FFFFFF")
    sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2), im)
    d.text((x + cell // 2, y + cell + 14), n, fill="#24201F", font=font, anchor="mm")
sheet.save(sys.argv[1] if len(sys.argv) > 1 else "hoja_kit.png")
print(sheet.size)
