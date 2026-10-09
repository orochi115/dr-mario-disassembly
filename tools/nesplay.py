"""Small helpers around cynes for scripted runs and screenshots."""
import cynes
from PIL import Image

A, B, SELECT, START = 0x80, 0x40, 0x20, 0x10
UP, DOWN, LEFT, RIGHT = 0x08, 0x04, 0x02, 0x01

class Play:
    def __init__(self, rom):
        self.nes = cynes.NES(rom)
        self.frame = None

    def wait(self, n=1, pad=0):
        self.nes.controller = pad
        for _ in range(n):
            self.frame = self.nes.step(1)
        self.nes.controller = 0
        return self

    def press(self, pad, hold=2, after=10):
        self.wait(hold, pad)
        return self.wait(after)

    def shot(self, path):
        Image.fromarray(self.frame).save(path)
        return self

    def __getitem__(self, a):
        return self.nes[a]

    def __setitem__(self, a, v):
        self.nes[a] = v


def grid(src, dst, scale=3):
    """Save a scaled copy of a screenshot with an 8x8 tile grid and row/column numbers."""
    from PIL import ImageDraw
    im = Image.open(src).convert('RGB')
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for i in range(0, 33):
        c = (255, 255, 0) if i % 4 == 0 else (90, 90, 90)
        d.line([(i * 8 * scale, 0), (i * 8 * scale, im.height)], fill=c)
        d.line([(0, i * 8 * scale), (im.width, i * 8 * scale)], fill=c)
    for i in range(32):
        d.text((i * 8 * scale + 2, 1), str(i), fill=(0, 255, 255))
    for i in range(30):
        d.text((1, i * 8 * scale + 2), str(i), fill=(0, 255, 255))
    im.save(dst)
