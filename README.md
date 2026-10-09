# Dr. Mario (NES) Disassembly
This is a disassembly of Dr. Mario for the Nintendo Entertainment System.

It builds Dr. Mario (Japan, USA) (Rev A).nes using ASM6f (https://github.com/freem/asm6f).

Thanks to Sour, author of the excellent NES emulator Mesen (https://www.mesen.ca/), which debug options were vital to this project.

Also, thanks to all contributors of the Dr.Mario articles at Data Crystal (https://datacrystal.romhacking.net/wiki/Dr._Mario) and The Cutting Room Floor (https://tcrf.net/Dr._Mario_(NES)).

## Mod: Chinese text and slow speed (branch `cn`)

- **Slow speed** (缓动, `OFF` in English): a fourth speed, left of LOW and the default at power-on. The capsule never falls by itself. Pressing down moves it one row; holding down moves it one row every `CFG_DROP_FRAMES` frames (0.5 s by default). Holding up drops it fast, like down at the other speeds. Score, cutscenes and the level 20 ending count it as LOW. The demo still plays at MED.
- **Chinese text** (`-l zh`): every screen except the Dr. MARIO logo and the Nintendo line, in the 12 px [Fusion Pixel](https://github.com/TakWolf/fusion-pixel-font) font (SIL OFL 1.1, see `fonts/OFL.txt`). The text and its positions are in `text/zh_strings.txt`. `tools/build_text.py` draws it on the original screens and writes `build/chr_zh.bin` (64K CHR: banks 8/9 hold the 2-player level) and `build/text_zh.asm`.

Building needs asm6f (`make -C ../asm6f`) and Python 3:

    ./build.sh [-r reva|ju|eu] [-l zh|en] [-c config/default.asm]   # build/drmario_cn_<region>_<lang>.nes
    ./run-ares.sh -l zh                                                # build and open in ares
    ./make.sh                                                          # MOD=0: rebuild JU, Rev A, EU and compare with the dumps

`config/default.asm` sets `CFG_SLOW` (1 = slow is the power-on speed) and `CFG_DROP_FRAMES` (slow speed: frames per row while down is held; 30, or 25 on the 50 Hz EU version). `tools/democheck.py ROM ORIGINAL` checks that the demo plays exactly like the original (needs `pip install cynes`).
