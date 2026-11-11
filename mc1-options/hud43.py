"""Midnight Club: Street Racing (SLUS-20063): keeps the driving HUD in 4:3 shapes on a 16:9 picture, each part at its own edge.

    python -I hud43.py        writes hud43.pnach (a PCSX2-style patch file, section [HUD 4:3])

The same method as MC2Recomp's mc2-options/hud43.py, with Midnight Club's addresses (found 2026-11-10 by reading the game's
code; it has no symbols):
  * 0x125C78 is the HUD's per-frame draw. It draws each part in turn: direct calls (`jal`, a0 = the HUD or the part) and
    virtual calls of the parts' Draw (vtable slot 2: `lh a0,16(v0); lw v1,20(v0); jalr ra,v1`, a0 = the part). Each call
    becomes `jal` to a small stub that loads the part's mark (and the function it calls) and goes on to WRAP. When the HUD
    option word at 0x000FFF04 is 1, WRAP adds one qword to the game's VIF1 packet chain before the part draws and one
    after: DMA tag cnt/0, VIF FLUSH, VIF MARK value. The toolkit's runtime (gif.cpp, hud_mark) squeezes the x of everything
    the part draws on PATH1/PATH2 while the mark is on, toward the part's edge, so the 16:9 picture shows it in 4:3 shape.
  * The packet chain: its write pointer is the scratchpad word 0x700005D0 and its end 0x700005D4; when the end is set and
    the next qword would pass it, the game calls 0x279A00 (sends the full buffer and starts the next) and reads the pointer
    again (the game's own pattern, e.g. at 0x102518).
  * mark = 0x8000 | part << 8 | side (1 left, 2 centre, 3 right, 0 the third its first drawing is in;
    PS2_HUD_LOG=1 prints each part's box).
Memory used, all below the game's load address 0x100000 (nothing there is used by the game or the runtime):
  0x000FF000..  the new code;  0x000FFF04 HUD option (16 bit).
"""
import os

R = {n: i for i, n in enumerate(['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
                                 's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra'])}
CAVE = 0x000FF000
HUD_OPTION = -0xFC  # 0x000FFF04, from 0x00100000
PACKET_AT, PACKET_END = 0x05D0, 0x05D4  # the game's VIF1 packet pointer and its end, in the scratchpad (0x70000000)
PACKET_FLUSH = 0x279A00  # sends the full buffer; the pointer is read again after it
NONE, LEFT, CENTRE, RIGHT = 0, 1, 2, 3
SKIP = None  # not hooked: drawn where the 3D world puts it, which the widescreen projection already places
JALR_V1 = 'jalr v1'

# The HUD's draw calls in 0x125C78 (part number = place in this list), what each calls, and the side each part belongs to,
# read off PS2_HUD_LOG=1 while driving in a cruise and a Waypoint race in New York (which third of the 640-pixel frame the
# part's box is in; the launcher sets PS2_HUD_WIDTH=640 for the runtime). Parts that drew nothing there keep NONE: the
# runtime then takes the third their first drawing is in.
SITES = [  # (address of the call, its target: a function address or JALR_V1, side)
    (0x125D4C, JALR_V1, NONE),    # 0   field 0x28, Draw (another mode's path)
    (0x125D64, JALR_V1, NONE),    # 1   field 0x2C, Draw (another mode's path)
    (0x125D6C, 0x1257E8, NONE),   # 2   the HUD's own 0x1257E8 (another mode's path)
    (0x125D88, 0x12F3B8, NONE),   # 3   field 0x18's 0x12F3B8 (another mode's path)
    (0x125DC4, JALR_V1, NONE),    # 4   field 0x30, Draw (another mode's path)
    (0x125DD4, 0x125FA0, SKIP),   # 5   the HUD's own 0x125FA0: the waypoint beacon in the street, x 188..282 as it moves
    (0x125DDC, 0x126B40, CENTRE), # 6   field 0x00: the waypoint arrow at the top, x 297..341 (race)
    (0x125DE4, 0x1277C8, RIGHT),  # 7   field 0x10: speedometer, x 367..567
    (0x125DEC, 0x127270, RIGHT),  # 8   field 0x0C: x 422..551
    (0x125DF4, 0x12BA58, LEFT),   # 9   field 0x14: the race timer, x 8..165 (race)
    (0x125E0C, JALR_V1, RIGHT),   # 10  field 0x08, Draw: position (Pos: 5/5), x 478..609 (race)
    (0x125E14, 0x12A658, LEFT),   # 11  field 0x04: the map, x 8..192 (clipped by its scissor)
    (0x125E2C, JALR_V1, NONE),    # 12  field 0x1C, Draw
    (0x125E44, JALR_V1, RIGHT),   # 13  field 0x20, Draw: gear, x 396..428
    (0x125E5C, JALR_V1, RIGHT),   # 14  field 0x24, Draw: damage and speed, x 434..563
    (0x125E64, 0x1257E8, CENTRE), # 15  the HUD's own 0x1257E8: messages in the middle, x 269..369 (race)
]


class Asm:
    def __init__(self, base):
        self.base, self.items, self.labels = base, [], {}

    def label(self, name):
        self.labels[name] = self.base + 4 * len(self.items)

    def emit(self, f):
        self.items.append(f)

    def r(self, fn, rd='zero', rs='zero', rt='zero', sa=0):
        self.emit(lambda L, pc: (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn)

    def i(self, op, rt, rs, imm):
        self.emit(lambda L, pc: (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF))

    def or_(self, d, s, t): self.r(37, d, s, t)
    def daddu(self, d, s, t): self.r(45, d, s, t)
    def sltu(self, d, s, t): self.r(43, d, s, t)
    def jr(self, s): self.r(8, 'zero', s)
    def jalr(self, s): self.r(9, 'ra', s)
    def nop(self): self.emit(lambda L, pc: 0)
    def addiu(self, t, s, imm): self.i(9, t, s, imm)
    def ori(self, t, s, imm): self.i(13, t, s, imm)
    def lui(self, t, imm): self.i(15, t, 'zero', imm)
    def lw(self, t, off, s): self.i(35, t, s, off)
    def lhu(self, t, off, s): self.i(37, t, s, off)
    def sw(self, t, off, s): self.i(43, t, s, off)

    def branch(self, op, s, t, target):
        self.emit(lambda L, pc: (op << 26) | (R[s] << 21) | (R[t] << 16) | (((L[target] - pc - 4) >> 2) & 0xFFFF))

    def beq(self, s, t, target): self.branch(4, s, t, target)
    def j(self, target): self.emit(lambda L, pc: (2 << 26) | (((L[target] if isinstance(target, str) else target) >> 2) & 0x3FFFFFF))
    def jal(self, target): self.emit(lambda L, pc: (3 << 26) | (((L[target] if isinstance(target, str) else target) >> 2) & 0x3FFFFFF))

    def words(self):
        return [(self.base + 4 * k, f(self.labels, self.base + 4 * k)) for k, f in enumerate(self.items)]


def build():
    a = Asm(CAVE)

    # WRAP (t8 = this part's mark, v0 = the function its call goes to; a0 = its argument, set by the call's delay slot)
    a.label('wrap')
    a.addiu('sp', 'sp', -32)
    a.sw('ra', 0, 'sp')
    a.sw('v0', 4, 'sp')
    a.sw('a0', 8, 'sp')
    a.sw('t8', 12, 'sp')
    a.lui('t9', 0x0010)
    a.lhu('t9', HUD_OPTION, 't9')
    a.beq('t9', 'zero', 'wrap_call')
    a.sw('t9', 16, 'sp')
    a.jal('mark')
    a.lw('a0', 12, 'sp')
    a.label('wrap_call')
    a.lw('v0', 4, 'sp')
    a.jalr('v0')
    a.lw('a0', 8, 'sp')
    a.lw('t9', 16, 'sp')
    a.beq('t9', 'zero', 'wrap_out')
    a.sw('v0', 4, 'sp')       # the part's own return value, kept for the caller
    a.jal('mark')
    a.daddu('a0', 'zero', 'zero')
    a.label('wrap_out')
    a.lw('v0', 4, 'sp')
    a.lw('ra', 0, 'sp')
    a.jr('ra')
    a.addiu('sp', 'sp', 32)

    # MARK (a0 = the value): one qword on the VIF1 chain, DMA tag cnt with no data, VIF FLUSH, VIF MARK a0
    a.label('mark')
    a.addiu('sp', 'sp', -16)
    a.sw('ra', 0, 'sp')
    a.sw('a0', 4, 'sp')
    a.lui('a3', 0x7000)
    a.lw('v1', PACKET_END, 'a3')
    a.beq('v1', 'zero', 'mark_write')    # no end set: the game does not check either
    a.lw('a2', PACKET_AT, 'a3')
    a.addiu('v0', 'a2', 16)
    a.sltu('v0', 'v1', 'v0')             # end < pointer + 16: full
    a.beq('v0', 'zero', 'mark_write')
    a.nop()
    a.jal(PACKET_FLUSH)
    a.nop()
    a.label('mark_write')
    a.lui('a3', 0x7000)
    a.lw('a2', PACKET_AT, 'a3')
    a.lui('v0', 0x1000)
    a.sw('v0', 0, 'a2')       # DMA tag: cnt, qwc 0 (its upper half goes to the VIF)
    a.sw('zero', 4, 'a2')
    a.lui('v0', 0x1100)
    a.sw('v0', 8, 'a2')       # VIF FLUSH
    a.lw('a0', 4, 'sp')
    a.lui('v0', 0x0700)
    a.or_('v0', 'v0', 'a0')
    a.sw('v0', 12, 'a2')      # VIF MARK value
    a.addiu('a2', 'a2', 16)
    a.sw('a2', PACKET_AT, 'a3')
    a.lw('ra', 0, 'sp')
    a.jr('ra')
    a.addiu('sp', 'sp', 16)

    # one stub per draw call: the function the call goes to in v0, the part's mark in t8, then WRAP
    hooks = []
    for k, (site, target, side) in enumerate(SITES):
        if side is SKIP:
            continue
        name = 'stub%d' % k
        a.label(name)
        if target == JALR_V1:
            a.daddu('v0', 'v1', 'zero')
        else:
            a.lui('v0', target >> 16)
            a.ori('v0', 'v0', target & 0xFFFF)
        a.j('wrap')
        a.ori('t8', 'zero', 0x8000 | (k << 8) | side)
        hooks.append((site, name))

    code = a.words()
    return code, [(site, (3 << 26) | ((a.labels[name] >> 2) & 0x3FFFFFF)) for site, name in hooks]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    code, hooks = build()
    lines = ['gametitle=Midnight Club - Street Racing (NTSC-U) SLUS-20063 DFD26C76', '', '[HUD 4:3]',
             'author=made for this recompilation (mc1-options/hud43.py)',
             'description=Keeps the driving HUD in 4:3 shapes at the screen edges with 16:9 on; switched by the 16-bit word at 000FFF04.']
    lines += ['patch=0,EE,%08X,word,%08X' % (addr, w) for addr, w in code]
    lines += ['patch=0,EE,%08X,word,%08X' % (addr, w) for addr, w in hooks]
    with open(os.path.join(here, 'hud43.pnach'), 'w', newline='\n') as out:
        out.write('\n'.join(lines) + '\n')
    print('%d words of new code at %08X..%08X, %d hooked draw calls' % (len(code), code[0][0], code[-1][0] + 4, len(hooks)))


main()
