;Mod defaults (included by build/gen_config.asm in MOD builds)
CFG_SLOW            = 1         ;1 = speed defaults to slow (no gravity) at power-on, 0 = MED as the original
; Slow speed: holding down moves the pill one row every CFG_DROP_FRAMES frames
; (0.5 s). Pressing down moves it one row at once.
if ver_EU
CFG_DROP_FRAMES     = 25        ;50 frames per second
else
CFG_DROP_FRAMES     = 30        ;60 frames per second
endif
