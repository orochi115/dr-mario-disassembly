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
;; slowDrop_check
;;
;; Slow speed, down button: returns A != 0 (Z clear) when the pill must go down one row.
;; Only down on the d-pad counts, like the original fast drop. A new press moves at once,
;; holding moves every CFG_DROP_FRAMES frames.
;;
slowDrop_check:
        lda currentP_btnsHeld
        and #btns_dpad
        cmp #btn_down
        bne @noDrop
        lda currentP_btnsPressed
        and #btn_down
        bne @drop                   ;Just pressed
        dec currentP_slowDropTimer
        bne @noDrop
    @drop:
        lda #CFG_DROP_FRAMES
        sta currentP_slowDropTimer
        rts                         ;A != 0
    @noDrop:
        lda #$00
        rts


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


if LANG_ZH

;;
;; zh_drawSpeed
;;
;; Draws a 2x2 speed character with rendering off. X = speedTextOffset result,
;; Y = 0 (1-player), 1 (2-player, P1) or 2 (2-player, P2)
;;
zh_drawSpeed:
        txa
        clc
        adc zh_speedTableOfs,Y      ;The three tables follow each other (16 bytes each)
        tax
        lda zh_speedAddr_hi,Y
        sta PPUADDR
        lda zh_speedAddr_lo,Y
        sta PPUADDR
        lda zh_SPD1P+0,X
        sta PPUDATA
        lda zh_SPD1P+1,X
        sta PPUDATA
        lda zh_speedAddr_hi,Y       ;Bottom row (the addresses don't cross a page)
        sta PPUADDR
        lda zh_speedAddr_lo,Y
        clc
        adc #$20
        sta PPUADDR
        lda zh_SPD1P+2,X
        sta PPUDATA
        lda zh_SPD1P+3,X
        sta PPUDATA
        rts

zh_speedTableOfs:
.db zh_SPD1P-zh_SPD1P, zh_SPD2P_P1-zh_SPD1P, zh_SPD2P_P2-zh_SPD1P
zh_speedAddr_hi:
.db >ZH_SPD1P_ADDR, >ZH_SPD2P_P1_ADDR, >ZH_SPD2P_P2_ADDR
zh_speedAddr_lo:
.db <ZH_SPD1P_ADDR, <ZH_SPD2P_P1_ADDR, <ZH_SPD2P_P2_ADDR


;;
;; zh_drawOptPlayers
;;
;; Options title: draws the first character (single / two players) with rendering off.
;; PPUADDR was already set to the digit position by the caller (ignored). Returns A = nbPlayers
;;
zh_drawOptPlayers:
        lda nbPlayers
        asl A
        asl A
        tax                         ;(nbPlayers - 1) * 4 + 4
        lda #>ZH_OPT_PLAYERS_ADDR
        sta PPUADDR
        lda #<ZH_OPT_PLAYERS_ADDR
        sta PPUADDR
        lda zh_optPlayers-4,X
        sta PPUDATA
        lda zh_optPlayers-3,X
        sta PPUDATA
        lda #>(ZH_OPT_PLAYERS_ADDR+$20)
        sta PPUADDR
        lda #<(ZH_OPT_PLAYERS_ADDR+$20)
        sta PPUADDR
        lda zh_optPlayers-2,X
        sta PPUDATA
        lda zh_optPlayers-1,X
        sta PPUDATA
        lda nbPlayers
        rts


;;
;; zh_render_cutscene_txt
;;
;; Replaces render_cutscene_txt: types (then removes) the cutscene text one 2x2 character
;; per step. zh_cutsceneText holds 5-byte records: low byte of the $21xx address, then the
;; top and bottom tiles. Tile $00 = speed value (4 columns), $01 = level number (the address
;; is then its bottom row), a low byte of $FF ends the text.
;;
zh_render_cutscene_txt:
        lda cutsceneFrame               ;0 = nothing to do
        beq @exit
        cmp #$80                        ;$81 and up: remove the text
        bcs @remove
        lda frameCounter                ;One step every 8 frames
        and #txtScrollSpeed_cutscene
        bne @exit
        lda #sq0_letter_cutscene
        sta sfx_toPlay_sq0
        lda cutsceneFrame
        jsr zh_cutRecord
        bcs @finished
        jsr zh_cutDraw
        inc cutsceneFrame
    @exit:
        rts
    @remove:
        and #$7F
        jsr zh_cutRecord
        bcs @finished
        jsr zh_cutErase
        inc cutsceneFrame
        rts
    @finished:
        lda #$00
        sta cutsceneFrame
        rts

;A = record number -> X = record offset, carry set at the end of the text
zh_cutRecord:
        sta zh_tmp
        asl A
        asl A
        adc zh_tmp                       ;Carry is clear (frame < $40)
        tax
        lda zh_cutsceneText,X
        cmp #$FF
        rts

;Sets PPUADDR to the record's address (+$20 if Y = $20)
zh_cutAddr:
        lda #>cutsceneText_VRAMaddr
        sta PPUADDR
        tya
        clc
        adc zh_cutsceneText,X
        sta PPUADDR
        rts

zh_cutDraw:
        ldy #$00
        jsr zh_cutAddr
        lda zh_cutsceneText+1,X
        beq @speed
        cmp #$01
        beq @level
        sta PPUDATA
        lda zh_cutsceneText+2,X
        sta PPUDATA
        ldy #$20
        jsr zh_cutAddr
        lda zh_cutsceneText+3,X
        sta PPUDATA
        lda zh_cutsceneText+4,X
        sta PPUDATA
        rts
    @level:
        ldx currentP_level
        dex                             ;The level was increased before the cutscene
        lda levelForDisplay,X
        jmp renderLevelNb_2digits
    @speed:
        stx zh_tmp
        lda currentP
        and #$01
        tax
        lda currentP_speedSetting
        jsr speedTextOffset             ;0/4/8/12 -> 8 bytes per speed
        txa
        asl A
        tay
        ldx #$04
    @speedTop:
        lda zh_cutsceneSpeed,Y
        sta PPUDATA
        iny
        dex
        bne @speedTop
        tya
        pha
        ldx zh_tmp
        ldy #$20
        jsr zh_cutAddr
        pla
        tay
        ldx #$04
    @speedBottom:
        lda zh_cutsceneSpeed,Y
        sta PPUDATA
        iny
        dex
        bne @speedBottom
        rts

zh_cutErase:
        lda zh_cutsceneText+1,X         ;Width: 2 (character or level number) or 4 (speed)
        beq @wide
        cmp #$01
        beq @levelNb
        jsr @erase2
        ldy #$20
        jsr zh_cutAddr
        jmp @fill2
    @levelNb:
    @erase2:
        ldy #$00
        jsr zh_cutAddr
    @fill2:
        lda #$FF
        sta PPUDATA
        sta PPUDATA
        rts
    @wide:
        ldy #$00
        jsr zh_cutAddr
        jsr @fill4
        ldy #$20
        jsr zh_cutAddr
    @fill4:
        lda #$FF
        sta PPUDATA
        sta PPUDATA
        sta PPUDATA
        sta PPUDATA
        rts

endif
