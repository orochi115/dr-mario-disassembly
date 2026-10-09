#!/bin/bash
# Build the mod: ./build.sh [-r reva|ju|eu] [-l zh|en] [-c config/NAME.asm]
# Writes build/drmario_cn_<region>_<lang>.nes and prints its path on the last line.
set -e
cd "$(dirname "$0")"
ASM6F=${ASM6F:-../asm6f/asm6f}
REGION=reva LANG_=zh CFG=config/default.asm
while getopts "r:l:c:" o; do
    case $o in
        r) REGION=$OPTARG ;;
        l) LANG_=$OPTARG ;;
        c) CFG=$OPTARG ;;
        *) echo "usage: $0 [-r reva|ju|eu] [-l zh|en] [-c config/NAME.asm]" >&2; exit 1 ;;
    esac
done
case $LANG_ in zh) ZH=1 ;; en) ZH=0 ;; *) echo "unknown language $LANG_" >&2; exit 1 ;; esac
[ -x "$ASM6F" ] || make -C ../asm6f >/dev/null
mkdir -p build
tools/gen_config.sh $REGION 1 $ZH $CFG > build/gen_config.asm
OUT=build/drmario_cn_${REGION}_${LANG_}.nes
$ASM6F -q -dGEN drmario.asm $OUT
echo "Built $REGION/$LANG_ with $CFG"
echo $OUT
