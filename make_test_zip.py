"""Create demo ZIPs of synthetic images for load-testing bulk mode:  python make_test_zip.py 30 demo.zip"""
import io, random, sys, zipfile
from PIL import Image, ImageDraw

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
out = sys.argv[2] if len(sys.argv) > 2 else "demo.zip"
with zipfile.ZipFile(out, "w") as zf:
    for k in range(n):
        im = Image.new("RGB", (640, 480), tuple(random.randint(0, 255) for _ in range(3)))
        d = ImageDraw.Draw(im)
        for _ in range(6):
            x, y = random.randint(0, 500), random.randint(0, 380)
            d.ellipse([x, y, x + random.randint(30, 140), y + random.randint(30, 140)],
                      fill=tuple(random.randint(0, 255) for _ in range(3)))
        b = io.BytesIO(); im.save(b, "JPEG"); zf.writestr(f"img_{k:03d}.jpg", b.getvalue())
print(f"wrote {out} with {n} images")
