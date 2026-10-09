;;
;; Mod routines (assembled only when MOD = 1)
;;
;; Slow speed: stored as speed_low plus a per-player flag (p1_slow/p2_slow), so every table
;; indexed by speed (score, cutscenes, colors) treats it as LOW. Only the gravity, the speed ups,
;; the options cursor and the speed text look at the flag. The demo always plays with gravity.
;;


;;
;; slowMode_check
;;
;; X = player (0 = P1, 1 = P2). Returns A != 0 (Z clear) if that player plays at slow speed
;;
slowMode_check:
        lda flag_demo               ;The demo keeps the original speed
        bne @notSlow
        lda p1_slow,X
        rts
    @notSlow:
        lda #$00
        rts


;;
;; currentP_isSlow
;;
;; Same as slowMode_check, for the current player. Clobbers X
;;
currentP_isSlow:
        lda currentP                ;player1 = 4, player2 = 5
        and #$01
        tax
        jmp slowMode_check


;;
;; speedTextOffset
;;
;; A = speed setting, X = player (0/1). Returns X = offset in textLevelSpeed / cutsceneText_speed
;;
speedTextOffset:
        asl A
        asl A
        pha
        jsr slowMode_check
        beq @normal
        pla
        lda #textSpeedSlow
        pha
    @normal:
        pla
        tax
        rts


;;
;; speedCursorPos
;;
;; Returns A = options cursor position of the current player (0 = slow, 1-3 = low/med/hi). Clobbers X
;;
speedCursorPos:
        lda currentP
        and #$01
        tax
        lda p1_slow,X
        bne @slow
        ldx currentP_speedSetting
        inx
        txa
        rts
    @slow:
        lda #$00
        rts


;;
;; updateSpeedCursor_mod
;;
;; Moves the current player's speed cursor over the 4 positions
;;
updateSpeedCursor_mod:
        jsr speedCursorPos
        ldx currentP_btnsPressed    ;Like the original, only an exact left or right press counts
        cpx #btn_right
        bne @checkLeft
        cmp #$03
        beq @exit
        clc
        adc #$01
        bne @move                   ;Always taken
    @checkLeft:
        cpx #btn_left
        bne @exit
        cmp #$00
        beq @exit
        sec
        sbc #$01
    @move:
        ldx #sq0_cursor_horizontal
        stx sfx_toPlay_sq0
        tay                         ;Y = new position
        lda currentP
        and #$01
        tax
        tya
        beq @setSlow
        dey
        sty currentP_speedSetting
        lda #$00
        sta p1_slow,X
        rts
    @setSlow:
        lda #speed_low
        sta currentP_speedSetting
        lda #$01
        sta p1_slow,X
    @exit:
        rts
