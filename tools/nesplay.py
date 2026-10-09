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
