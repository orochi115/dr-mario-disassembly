#!/usr/bin/env python3
"""Build the Chinese text for Dr. Mario: CHR banks and asm data.

Reads text/zh_strings.txt, the original CHR (bin/drmario_chr.bin), the original
nametables (data/drmario_data_nametables.asm) and the metasprites
(data/drmario_data_metasprites.asm). Chinese uses the Fusion Pixel 12px font
(OFL, see fonts/).

Each character is drawn on the screen's pixels: a 12x12 glyph inside a 16x16
cell (at GLYPH_X, GLYPH_Y), half-width characters (digits, ASCII) in an 8x16
cell. The pixels of every changed 8x8 cell are then turned back into tiles:
an existing tile with the same pixels is reused, otherwise a free tile of that
screen's CHR bank(s) is taken. Screens whose background swaps between two
banks (title 3/4, level 0/1) get the same tile number in both banks.

Outputs (in build/):
  chr_zh.bin   64K CHR: banks 0-7 as the original plus glyphs, banks 8/9 are
               the 2-player level banks (copies of 0/1 plus glyphs)
  text_zh.asm  nametables, dynamic tile tables, metasprites and constants

Strings file syntax (one command per line, # starts a comment):
  ERASE  SCREEN COL ROW W H TILE   set nametable cells to TILE (hex)
  FILL   SCREEN X Y W H COLOR      fill pixels with a colour (0-3)
  TEXT   SCREEN ID COL ROW TEXT    draw TEXT on the screen's nametable
  DYN    SCREEN ID COL ROW TEXT    draw TEXT on a scratch area and emit its
                                   tiles as rows (ZH_<ID>: top row, bottom row)
COL and ROW are in tiles and may carry a pixel offset: 12+4 = 12 tiles + 4 px.
DYN text is drawn on cells filled with the screen's DYN_BASE tile.

Usage: build_text.py [--preview]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
FONT = os.path.join(SRC, 'fonts', 'fusion-pixel-12px-monospaced-zh_hans.bdf')
CHR_IN = os.path.join(SRC, 'bin', 'drmario_chr.bin')
NT_ASM = os.path.join(SRC, 'data', 'drmario_data_nametables.asm')
SPR_ASM = os.path.join(SRC, 'data', 'drmario_data_metasprites.asm')
STRINGS = os.path.join(SRC, 'text', 'zh_strings.txt')
OUT_DIR = os.path.join(SRC, 'build')

GLYPH_X = 2     # Glyph position inside the 16x16 cell
GLYPH_Y = 2
HALF_X = 1      # Half-width glyph position inside the 8x16 cell

# Tiles used by the level screens beside the nametable: digits, field objects
# (pills, viruses, cleared and emptied cells), the text box and the crowns
DIGITS = set(range(10))
FIELD = {t | c for t in (0x40, 0x50, 0x60, 0x70, 0x80, 0x90, 0xA0, 0xB0, 0xD0, 0xE0, 0xF0)
         for c in range(3)}
TXTBOX = {0x8B, 0x8C, 0x8D, 0x8E, 0x8F, 0xED, 0xEE, 0xEF, 0xFE, 0xFF}
CROWNS = {0x5C, 0x5D, 0x6C, 0x6D}
# A field box cell is a field object: it can't be $00 (end of the box data),
# $Bx (cleared, drawn as emptied) or $Fx
FIELD_SAFE = [t for t in range(1, 256) if t >> 4 not in (0xB, 0xF)]

SCREENS = {
    # name: banks (all get the same tiles), nametable label, ink colour,
    # tiles which must be kept beside the ones the nametable uses,
    # base tile for DYN text
    'TITLE':    dict(banks=[3, 4], nt='bkgTitle', ink=1, keep=set(), base=0xFF),
    'OPTIONS':  dict(banks=[5], nt='bkgOptions', ink=1, keep=DIGITS | {0xF3, 0xF4, 0xF5, 0xF6, 0xFF},
                     base=0xFF, sprites=['bigCursor_top', 'bigCursor_bottom', 'musicTypeBox_large',
                                         'musicTypeBox_small', 'smallCursor_top', 'smallCursor_bottom']),
    'LEVEL1P':  dict(banks=[0, 1], nt='bkgLevel_1P', ink=0, keep=DIGITS | FIELD | TXTBOX, base=0xFE),
    'LEVEL2P':  dict(banks=[8, 9], src=[0, 1], nt='bkgLevel_2P', ink=0,
                     keep=DIGITS | FIELD | TXTBOX | CROWNS, base=0xFE),
    'CUTSCENE': dict(banks=[6], nt='bkgCutscene_andEnding', ink=1, keep=DIGITS | {0xFF}, base=0xFF),
    'SPRITES':  dict(banks=[2], nt=None, ink=2, keep=None, base=0xFF),
}
# Sprite bank: the letters of PAUSE/START and blank tiles no metasprite uses
SPRITE_TEXT = {'txtPause', 'txtStart', 'txtLow', 'txtMed', 'txtHi'}
# Metasprites drawn from other banks: cutscene sprites (bank 7), options (bank 5)
OTHER_BANK_SPRITES = ('UFO_', 'flying', 'witch', 'rooster', 'sprayCan', 'Cloud', 'Snowman',
                      'virusGroupCutscene', 'bigCursor', 'smallCursor', 'musicTypeBox')


def err(msg):
    sys.exit('build_text: ' + msg)


# ---------------------------------------------------------------------------
# Font

def load_font(wanted):
    """{char: (width, 12 rows of bits)}; width is 12 or 6 (half-width)."""
    glyphs, ascent, cur = {}, 10, None
    with open(FONT, encoding='utf-8') as f:
        lines = iter(f)
        for line in lines:
            if line.startswith('FONT_ASCENT'):
                ascent = int(line.split()[1])
            elif line.startswith('ENCODING'):
                code = int(line.split()[1])
                cur = chr(code) if chr(code) in wanted else None
            elif cur and line.startswith('DWIDTH'):
                dw = int(line.split()[1])
            elif cur and line.startswith('BBX'):
                w, h, xo, yo = map(int, line.split()[1:])
            elif cur and line.startswith('BITMAP'):
                bm = [[0] * 12 for _ in range(12)]
                top = ascent - (yo + h)
                nbits = ((w + 7) // 8) * 8
                for r in range(h):
                    bits = int(next(lines).strip(), 16)
                    for c in range(w):
                        if bits >> (nbits - 1 - c) & 1:
                            y, x = top + r, xo + c
                            if 0 <= y < 12 and 0 <= x < 12:
                                bm[y][x] = 1
                glyphs[cur] = (dw, bm)
                cur = None
    missing = [c for c in wanted if c not in glyphs]
    if missing:
        err('missing glyphs in font: ' + ''.join(missing))
    return glyphs


# ---------------------------------------------------------------------------
# Source data

def asm_bytes(path, label, stop_at_label=True):
    """Bytes of the .db lines after `label:` up to the next label.
    Lines inside if/endif blocks are skipped (mod patches)."""
    out, on, depth = [], False, 0
    for line in open(path):
        code = line.split(';')[0].strip()
        if re.match(r'^%s:' % re.escape(label), code):
            on = True
            continue
        if not on:
            continue
        if re.match(r'^\w+:', code) and stop_at_label:
            break
        low = code.lower()
        if low.startswith('if'):
            depth += 1
            continue
        if low.startswith('endif'):
            depth -= 1
            continue
        if depth or not low.startswith('.db'):
            continue
        out += [int(v, 16) for v in re.findall(r'\$([0-9A-Fa-f]{2})', code)]
    if not out:
        err('no data for ' + label)
    return out


def decode_nt(data):
    """Decode copyBkgOrPalToPPU data into {ppu address: byte}."""
    vram, i = {}, 0
    while data[i] < 0x80:
        addr = data[i] << 8 | data[i + 1]
        ctl = data[i + 2]
        i += 3
        n = ctl & 0x3F or 64
        if ctl & 0x40:
            vals = [data[i]] * n
            i += 1
        else:
            vals = data[i:i + n]
            i += n
        step = 32 if ctl & 0x80 else 1
        for k, v in enumerate(vals):
            vram[addr + k * step] = v
    return vram


def encode_nt(vram):
    """Encode {address: byte} for copyBkgOrPalToPPU, using runs for repeats."""
    out = []
    addrs = sorted(vram)
    i = 0
    while i < len(addrs):
        # Contiguous block
        j = i
        while j + 1 < len(addrs) and addrs[j + 1] == addrs[j] + 1:
            j += 1
        block = [vram[a] for a in addrs[i:j + 1]]
        base = addrs[i]
        k = 0
        lit = []

        while k < len(block):
            r = k
            while r < len(block) and block[r] == block[k] and r - k < 63:
                r += 1
            if r - k >= 4:
                start = base + k - len(lit)
                while lit:
                    n = min(len(lit), 63)
                    out.extend([start >> 8, start & 0xFF, n] + lit[:n])
                    start += n
                    del lit[:n]
                a = base + k
                out.extend([a >> 8, a & 0xFF, 0x40 | (r - k), block[k]])
                k = r
            else:
                lit.append(block[k])
                k += 1
        start = base + len(block) - len(lit)
        while lit:
            n = min(len(lit), 63)
            out.extend([start >> 8, start & 0xFF, n] + lit[:n])
            start += n
            del lit[:n]
        i = j + 1
    out.append(0xFF)
    assert decode_nt(out) == vram
    return out


def metasprites():
    """{label: [(y, tile, attr, x), ...]} from the metasprite file."""
    sprites, cur, buf = {}, None, []
    for line in open(SPR_ASM):
        code = line.split(';')[0].strip()
        m = re.match(r'^(\w+):', code)
        if m:
            cur = m.group(1)
            buf = []
            continue
        if cur and code.lower().startswith('.db'):
            buf += [int(v, 16) for v in re.findall(r'\$([0-9A-Fa-f]{2})', code)]
            groups = []
            k = 0
            while k < len(buf) and buf[k] != 0x80:
                groups.append(tuple(buf[k:k + 4]))
                k += 4
            sprites[cur] = groups
    return sprites


# ---------------------------------------------------------------------------
# CHR helpers

def tile_pixels(chr_, bank, t):
    o = bank * 4096 + t * 16
    return tuple(((chr_[o + y] >> (7 - x)) & 1) | (((chr_[o + y + 8] >> (7 - x)) & 1) << 1)
                 for y in range(8) for x in range(8))


def tile_bytes(px):
    b = bytearray(16)
    for y in range(8):
        for x in range(8):
            c = px[y * 8 + x]
            b[y] |= (c & 1) << (7 - x)
            b[y + 8] |= (c >> 1) << (7 - x)
    return bytes(b)


class Screen:
    def __init__(self, name, cfg, chr_, sprites):
        self.name = name
        self.cfg = cfg
        self.banks = cfg['banks']
        self.src = cfg.get('src', self.banks)
        self.ink = cfg['ink']
        self.chr = chr_          # bytearray, 64K
        self.vram = None
        if cfg['nt']:
            self.vram = decode_nt(asm_bytes(NT_ASM, cfg['nt']))
        self.alloc = {}          # pixels per bank -> tile
        self.changed = {}        # nametable address -> tile
        self.used_new = []
        # Free tiles
        if name == 'SPRITES':
            used = set()
            for lab, groups in sprites.items():
                if lab not in SPRITE_TEXT and not any(k in lab for k in OTHER_BANK_SPRITES):
                    used |= {g[1] for g in groups}
            letters = set()
            for lab in ('txtPause', 'txtStart'):
                letters |= {g[1] for g in sprites[lab]}
            blank = {t for t in range(256) if not any(tile_pixels(chr_, 2, t))}
            self.free = sorted((letters | blank) - used - {0xFF})
        else:
            keep = set(cfg['keep'])
            for lab in cfg.get('sprites', []):
                keep |= {g[1] for g in sprites[lab]}
            self.keep = keep
            self.free = None     # Computed once the nametable is final
        self.pending = []        # (kind, ...) drawn later

    # Pixel access to the nametable picture
    def nt_tile(self, col, row):
        a = 0x2000 + row * 32 + col
        return self.changed.get(a, self.vram[a])


def parse_pos(s):
    if '+' in s:
        t, p = s.split('+')
        return int(t) * 8 + int(p)
    if '-' in s[1:]:
        t, p = s.split('-')
        return int(t) * 8 - int(p)
    return int(s) * 8


def glyph_cells(text, font):
    """List of (dx, width, bitmap) for the characters of text."""
    out, x = [], 0
    for ch in text:
        if ch == ' ':
            x += 8
            continue
        if ch == '　':
            x += 16
            continue
        w, bm = font[ch]
        if w > 8:
            out.append((x + GLYPH_X, bm))
            x += 16
        else:
            out.append((x + HALF_X, bm))
            x += 8
    return out, x


class Canvas:
    """Pixels of a rectangle of cells over per-bank tile pictures."""

    def __init__(self, nbanks):
        self.px = [{} for _ in range(nbanks)]   # (x, y) -> colour, per bank

    def cells(self):
        return sorted({(x // 8, y // 8) for (x, y) in self.px[0]})


def build(preview=False):
    chr_ = bytearray(open(CHR_IN, 'rb').read())
    chr_ += chr_[0:0x2000]                      # banks 8/9 = copies of 0/1
    sprites = metasprites()
    screens = {n: Screen(n, c, chr_, sprites) for n, c in SCREENS.items()}

    cmds = []
    for ln, line in enumerate(open(STRINGS, encoding='utf-8'), 1):
        line = line.rstrip('\n')
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split(None, 1)
        cmds.append((ln, parts[0], parts[1] if len(parts) > 1 else ''))
    wanted = set()
    for ln, op, rest in cmds:
        if op in ('TEXT', 'DYN'):
            f = rest.split(None, 4)
            wanted |= set(f[4]) - {' ', '　'}
    font = load_font(wanted)

    # 1. Erase and gather drawing commands per screen
    dyn = []
    for ln, op, rest in cmds:
        f = rest.split()
        scr = screens.get(f[0])
        if not scr:
            err('line %d: unknown screen %s' % (ln, f[0]))
        if op == 'ERASE':
            col, row, w, h, tile = int(f[1]), int(f[2]), int(f[3]), int(f[4]), int(f[5], 16)
            for r in range(row, row + h):
                for c in range(col, col + w):
                    scr.changed[0x2000 + r * 32 + c] = tile
        elif op == 'FILL':
            scr.pending.append(('fill', parse_pos(f[1]), parse_pos(f[2]), int(f[3]), int(f[4]), int(f[5])))
        elif op == 'TEXT':
            ident, x, y, text = rest.split(None, 4)[1:]
            scr.pending.append(('text', ident, parse_pos(x), parse_pos(y), text))
        elif op == 'DYN':
            ident, x, y, text = rest.split(None, 4)[1:]
            dyn.append((scr, ident, parse_pos(x), parse_pos(y), text))
        else:
            err('line %d: unknown command %s' % (ln, op))

    consts = []
    asm = []

    # 2. Static text: compose pixels on the nametable picture
    for scr in screens.values():
        if scr.vram is None:
            continue
        nb = len(scr.banks)
        pic = [{} for _ in range(nb)]     # (x, y) -> colour for touched pixels

        def base_px(b, x, y):
            if (x, y) in pic[b]:
                return pic[b][(x, y)]
            t = scr.nt_tile(x // 8, y // 8)
            return tile_pixels(chr_, scr.src[b], t)[(y % 8) * 8 + x % 8]
        for item in scr.pending:
            if item[0] == 'fill':
                _, x0, y0, w, h, colour = item
                for y in range(y0, y0 + h):
                    for x in range(x0, x0 + w):
                        for b in range(nb):
                            pic[b][(x, y)] = colour
            else:
                _, ident, x0, y0, text = item
                cells, width = glyph_cells(text, font)
                consts.append(('ZH_%s_X' % ident, x0))
                consts.append(('ZH_%s_W' % ident, width))
                for dx, bm in cells:
                    for gy in range(12):
                        for gx in range(12):
                            if bm[gy][gx]:
                                for b in range(nb):
                                    pic[b][(x0 + dx + gx, y0 + GLYPH_Y + gy)] = scr.ink
        touched = sorted({(x // 8, y // 8) for (x, y) in pic[0]})
        scr.cells_px = {}
        for (c, r) in touched:
            scr.cells_px[(c, r)] = tuple(
                tuple(base_px(b, c * 8 + i % 8, r * 8 + i // 8) for i in range(64)) for b in range(nb))

    # 3. Free tiles of each nametable screen: everything the final nametable
    #    and the screen's other users (keep) don't need
    for scr in screens.values():
        if scr.vram is None:
            continue
        final = dict(scr.vram)
        final.update(scr.changed)
        used = {v for a, v in final.items() if 0x2000 <= a < 0x23C0 and
                ((a - 0x2000) % 32, (a - 0x2000) // 32) not in scr.cells_px}
        scr.free = [t for t in range(256) if t not in used and t not in scr.keep]
    # The cutscene bank: only blank tiles and the letters are certainly unused
    screens['CUTSCENE'].free = [t for t in screens['CUTSCENE'].free
                                if not any(tile_pixels(chr_, 6, t)) or 0x0A <= t <= 0x24]

    def new_tile(scr, pics, allowed=None):
        if pics in scr.alloc:
            t = scr.alloc[pics]
            if allowed is None or t in allowed:
                return t
        # Reuse a tile which keeps its pixels and already looks the same
        for t in range(256):
            if t in scr.free or (allowed is not None and t not in allowed):
                continue
            if all(tile_pixels(chr_, bank, t) == pics[b] for b, bank in enumerate(scr.banks)):
                scr.alloc.setdefault(pics, t)
                return t
        for t in scr.free:
            if allowed is not None and t not in allowed:
                continue
            scr.free.remove(t)
            for b, bank in enumerate(scr.banks):
                o = bank * 4096 + t * 16
                chr_[o:o + 16] = tile_bytes(pics[b])
            scr.alloc.setdefault(pics, t)
            scr.used_new.append(t)
            return t
        err('out of tiles on screen %s' % scr.name)

    # 4. Dynamic text first (field boxes need safe tiles), then static text.
    #    Each DYN string becomes the rows of tiles of the cells its ink covers.
    dyn_tables = {}
    for scr, ident, x0, y0, text in dyn:
        nb = len(scr.banks)
        base_t = scr.cfg['base']
        base = tile_pixels(chr_, scr.src[0], base_t)
        pic = {}
        if text not in ('@LV', '@SP'):
            cells, width = glyph_cells(text, font)
            for dx, bm in cells:
                for gy in range(12):
                    for gx in range(12):
                        if bm[gy][gx]:
                            pic[(x0 + dx + gx, y0 + GLYPH_Y + gy)] = scr.ink
        if not pic:
            dyn_tables[ident] = (scr, x0 // 8, y0 // 8, [], text)
            continue
        c0 = min(x for x, y in pic) // 8
        c1 = max(x for x, y in pic) // 8
        if ident.startswith('CUT'):         # Whole character cells
            c0, c1 = x0 // 8, (x0 + width - 1) // 8
        r0 = min(y for x, y in pic) // 8
        r1 = max(y for x, y in pic) // 8
        allowed = FIELD_SAFE if ident.startswith('BOX') else None
        rows = []
        for r in range(r0, r1 + 1):
            row = []
            for c in range(c0, c1 + 1):
                px = tuple(pic.get((c * 8 + i % 8, r * 8 + i // 8), base[i]) for i in range(64))
                row.append(base_t if px == base else new_tile(scr, (px,) * nb, allowed))
            rows.append(row)
        dyn_tables[ident] = (scr, c0, r0, rows, text)

    for scr in screens.values():
        if scr.vram is None:
            continue
        for (c, r), pics in sorted(scr.cells_px.items()):
            scr.changed[0x2000 + r * 32 + c] = new_tile(scr, pics)

    # 5. Nametables. No cell may still point at a tile that got new pixels.
    for scr in screens.values():
        if scr.vram is None or not scr.changed:
            continue
        final = dict(scr.vram)
        final.update(scr.changed)
        for a, t in final.items():
            if a < 0x23C0 and t in scr.used_new and a not in scr.changed:
                err('%s: cell %04X still uses tile %02X, which now holds a glyph' % (scr.name, a, t))
        asm.append('%s:' % scr.cfg['nt'])
        data = encode_nt(final)
        for k in range(0, len(data), 16):
            asm.append('.db ' + ','.join('$%02X' % v for v in data[k:k + 16]))
        asm.append('')

    # 6. Dynamic data
    def db(vals):
        return '.db ' + ','.join('$%02X' % (v & 0xFF) for v in vals)

    def table(ident):
        if ident not in dyn_tables:
            err('missing DYN ' + ident)
        return dyn_tables[ident]

    def quad(ident, cols=2):
        """Top row then bottom row of a DYN string of `cols` columns."""
        scr, c0, r0, rows, _ = table(ident)
        if len(rows) != 2 or len(rows[0]) != cols:
            err('%s must cover %d x 2 cells, not %d x %d' % (ident, cols, len(rows[0]), len(rows)))
        return rows[0] + rows[1], 0x2000 + r0 * 32 + c0

    # Speed values, 4 tiles each in speedTextOffset order: low, med, hi, slow
    for name in ('SPD1P', 'SPD2P_P1', 'SPD2P_P2'):
        asm.append('zh_%s:' % name)
        for k in range(4):
            tiles, addr = quad('%s_%d' % (name, k))
            asm.append(db(tiles))
            if k == 0:
                consts.append(('ZH_%s_ADDR' % name, addr))
                if (addr & 0xFF) > 0xDF:
                    err('%s: the bottom row must be in the same page (zh_drawSpeed)' % name)
        asm.append('')

    # Options screen: first character of the title (single / two players)
    asm.append('zh_optPlayers:')
    for k in (1, 2):
        tiles, addr = quad('OPT_%dP' % k)
        asm.append(db(tiles))
    consts.append(('ZH_OPT_PLAYERS_ADDR', addr))
    asm.append('')

    # Field text boxes (8 columns): rows of tiles, $00 ends the data. The 2P
    # table follows the 1P one (the code adds ZH_BOX_<box>_2P to its index).
    BOXES = {'stageClear': 10, 'gameOver': 7, 'draw': 5}
    for box, height in BOXES.items():
        for mode in ('1P', '2P'):
            if box == 'draw' and mode == '1P':
                continue
            grid = [[0xFF] * 8 for _ in range(height)]
            top = 1 if box == 'stageClear' else 0
            for r in range(top, height):
                if r == top:
                    grid[r] = [0x8B] + [0x8C] * 6 + [0x8D]
                elif r == height - 1:
                    grid[r] = [0xED] + [0xEE] * 6 + [0xEF]
                else:
                    grid[r] = [0x8E] + [0xFE] * 6 + [0x8F]
            for ident, (scr, c0, r0, rows, _) in dyn_tables.items():
                if ident.startswith('BOX_%s_%s_' % (mode, box)):
                    for dr, row in enumerate(rows):
                        for dc, t in enumerate(row):
                            if not (1 <= c0 + dc <= 6 and top < r0 + dr < height - 1):
                                err('%s is outside the box' % ident)
                            grid[r0 + dr][c0 + dc] = t
            asm.append('zh_txtBox_%s_%s:' % (box, mode))
            for row in grid:
                asm.append(db(row))
            asm.append('.db $00')
            if mode == '1P':
                consts.append(('ZH_BOX_%s_2P' % box, height * 8 + 1))
        asm.append('')

    # Cutscene text: 5-byte records (low address byte, then 4 tiles), see
    # zh_render_cutscene_txt. Tiles $00 = speed value, $01 = level number.
    asm.append('zh_cutsceneText:')
    asm.append(db([0] * 5) + '                 ;Index 0 is never used')
    nrec = 1
    for ident, (scr, c0, r0, rows, text) in dyn_tables.items():
        if not ident.startswith('CUT_'):
            continue
        addr = 0x2000 + r0 * 32 + c0
        if text == '@LV':
            asm.append(db([addr + 32, 1, 0, 0, 0]))
            nrec += 1
            continue
        if text == '@SP':
            asm.append(db([addr, 0, 0, 0, 0]))
            nrec += 1
            continue
        if len(rows) != 2 or len(rows[0]) % 2:
            err('%s: cutscene text must be whole characters on 2 rows' % ident)
        for k in range(0, len(rows[0]), 2):
            a = addr + k
            if a >> 8 != 0x21 or (a + 32) >> 8 != 0x21:
                err('%s: cutscene text must stay in $2100-$21FF' % ident)
            asm.append(db([a, rows[0][k], rows[0][k + 1], rows[1][k], rows[1][k + 1]]))
            nrec += 1
    asm.append('.db $FF')
    if nrec * 5 > 255:
        err('cutscene text too long (records are indexed by frame * 5)')
    asm.append('zh_cutsceneSpeed:                       ;8 tiles each: top row, bottom row')
    for k in range(4):
        tiles, _ = quad('CUTSPD_%d' % k, 4)
        asm.append(db(tiles))
    asm.append('')

    # Sprite text: metasprites (y, tile, attribute, x), $80 ends
    for ident, label in (('SPR_PAUSE', 'zh_txtPause'), ('SPR_START', 'zh_txtStart')):
        scr, c0, r0, rows, _ = table(ident)
        asm.append('%s:' % label)
        for r, row in enumerate(rows):
            for c, t in enumerate(row):
                if t != scr.cfg['base']:
                    asm.append(db([(r0 + r) * 8, t, 0, (c0 + c) * 8]))
        asm.append('.db $80')
    asm.append('')

    # Report
    report = []
    for scr in screens.values():
        report.append('%s +%d (%d free)' % (scr.name, len(scr.used_new), len(scr.free)))
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, 'chr_zh.bin'), 'wb') as f:
        f.write(chr_)
    with open(os.path.join(OUT_DIR, 'text_zh.asm'), 'w') as f:
        f.write(';Generated by tools/build_text.py from text/zh_strings.txt - do not edit\n\n')
        for name, v in consts:
            f.write('%-24s= $%02X\n' % (name, v) if v < 256 else '%-24s= $%04X\n' % (name, v))
        f.write('\n' + '\n'.join(asm) + '\n')
    print('build_text: ' + ', '.join(report))
    if preview:
        write_previews(screens, chr_)


def write_previews(screens, chr_):
    from PIL import Image
    grey = [(0, 0, 0), (85, 85, 85), (170, 170, 170), (255, 255, 255)]
    for scr in screens.values():
        if scr.vram is None:
            continue
        im = Image.new('RGB', (256, 240))
        final = dict(scr.vram)
        final.update(scr.changed)
        for r in range(30):
            for c in range(32):
                px = tile_pixels(chr_, scr.banks[0], final[0x2000 + r * 32 + c])
                for i, v in enumerate(px):
                    im.putpixel((c * 8 + i % 8, r * 8 + i // 8), grey[v])
        im.resize((768, 720), Image.NEAREST).save(os.path.join(OUT_DIR, 'preview_%s.png' % scr.name.lower()))


if __name__ == '__main__':
    build('--preview' in sys.argv)
