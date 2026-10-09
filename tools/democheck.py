#!/usr/bin/env python3
"""democheck.py ROM [ORIGINAL] [FRAMES] - compare the attract-mode demo of ROM with ORIGINAL.

Runs both ROMs from power-on without input and records the sequence of distinct
game states while the demo runs (flag_demo $0741 = $FE): P1 field ($0400-$047F),
falling pill X/Y/rotation and colours, virus count. Frame timing is ignored, only
the order of states counts. Needs cynes (pip install cynes in a venv).
"""
import sys
import cynes

def demo_states(rom, frames):
    nes = cynes.NES(rom)
    states, demos = [], 0
    prev_demo = False
    for _ in range(frames):
        nes.step(1)
        in_demo = nes[0x741] == 0xFE and nes[0x46] != 0   # mode != 0
        if in_demo and not prev_demo:
            demos += 1
            states.append(('demo', demos))
        prev_demo = in_demo
        if not in_demo:
            continue
        s = (tuple(nes[0x400 + i] for i in range(0x80)),
             nes[0x305], nes[0x306], nes[0x325], nes[0x301], nes[0x302], nes[0x324])
        if s != states[-1]:
            states.append(s)
    return states, demos

def main():
    rom = sys.argv[1]
    orig = sys.argv[2] if len(sys.argv) > 2 else '../Dr. Mario (Japan, USA) (En) (Rev 1).nes'
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 9000
    a, na = demo_states(orig, frames)
    b, nb = demo_states(rom, frames)
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            print(f'DIFFER at state {i} of {len(a)}/{len(b)} (demos {na}/{nb})')
            sys.exit(1)
    print(f'demo OK: {n} states match (original {len(a)}, rom {len(b)}, demos {na}/{nb})')
    sys.exit(0 if n > 10 else 1)

main()
