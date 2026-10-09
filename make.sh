#!/bin/bash
# Build the three original versions (MOD=0) and compare them with the dumps
# in the parent folder. The 16-byte header is skipped: the dumps use NES 2.0.
cd "$(dirname "$0")"
ASM6F=${ASM6F:-../asm6f/asm6f}
mkdir -p build
fail=0
for r in ju reva eu; do
    case $r in
        ju)   dump="../Dr. Mario (Japan, USA) (En).nes" ;;
        reva) dump="../Dr. Mario (Japan, USA) (En) (Rev 1).nes" ;;
        eu)   dump="../Dr. Mario (Europe).nes" ;;
    esac
    tools/gen_config.sh $r 0 > build/gen_config.asm
    out=build/drmario_orig_$r.nes
    if ! $ASM6F -q -dGEN drmario.asm $out; then echo "$r: BUILD FAILED"; fail=1; continue; fi
    if [ ! -f "$dump" ]; then echo "$r: built ($dump not found)"; continue; fi
    if cmp -s <(tail -c +17 $out) <(tail -c +17 "$dump"); then
        echo "$r: OK"
    else
        echo "$r: DIFFERS"; fail=1
    fi
done
rm -f build/gen_config.asm
exit $fail
