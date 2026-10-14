#sbar.py

import OpenGL.GL as gl

import _cmd
import cl_main
import common
import cvar
import gl_draw
import gl_screen
import gl_vidsdl
import host
import menu
import protocol
import quakedef
import wad

sb_updates : int = 0

STAT_MINUS = 10

sb_nums : list[list[wad.qpic_t]] = [[None for j in range(11)] for i in range(2)]
sb_color : wad.qpic_t = None
sb_slash : wad.qpic_t = None
sb_ibar  : wad.qpic_t = None
sb_sbar  : wad.qpic_t = None
sb_scorebar : wad.qpic_t = None

sb_weapons : list[list[wad.qpic_t]] = [[None for j in range(8)] for i in range(7)]
sb_ammo    : list[wad.qpic_t] = [None for i in range(4)]
sb_sigil : list[wad.qpic_t] = [None for i in range(4)]
sb_armor : list[wad.qpic_t] = [None for i in range(3)]
sb_items : list[wad.qpic_t] = [None for i in range(32)]

sb_faces : list[list[wad.qpic_t]] = [[None for j in range(2)]for i in range(7)]
sb_face_invis : wad.qpic_t = None
sb_face_quad : wad.qpic_t = None
sb_face_invuln : wad.qpic_t = None
sb_face_invis_invuln : wad.qpic_t = None

sb_showscores = False
sb_lines = 0
fragsort = []
scoreboardlines = 0

rsb_invbar : list[wad.qpic_t] = [None for j in range(2)]
rsb_weapons : list[wad.qpic_t] = [None for j in range(5)]
rsb_items : list[wad.qpic_t] = [None for j in range(2)]
rsb_ammo : list[wad.qpic_t] = [None for j in range(3)]
rsb_teambord : wad.qpic_t = None

hsb_weapons : list[list[wad.qpic_t]] = [[None for j in range(7)] for i in range(5)]
hsb_items : list[wad.qpic_t] = [None for i in range(2)]

def Sbar_ShowScores():
    global sb_showscores, sb_updates
    if sb_showscores:
        return

    sb_showscores = True
    sb_updates = 0

def Sbar_DontShowScores():
    global sb_showscores, sb_updates

    sb_showscores = False
    sb_updates = 0

def Sbar_Changed():
    global sb_updates

    sb_updates = 0


def Sbar_DrawPic(x, y, pic: wad.qpic_t):
    gl_draw.Draw_Pic ( x, y + 24,  pic)

def Sbar_DrawPicAlpha(x, y, pic: wad.qpic_t, alpha):
    gl.glDisable(gl.GL_ALPHA_TEST)
    gl.glEnable(gl.GL_BLEND)
    gl.glColor(1, 1, 1, alpha)

    gl_draw.Draw_Pic(x, y + 24,  pic)

    gl.glColor(1, 1, 1, 1)
    gl.glDisable(gl.GL_BLEND)
    gl.glEnable(gl.GL_ALPHA_TEST)

def Sbar_DrawCharacter(x, y, num):
    gl_draw.Draw_Character(x, y + 24, num)

def Sbar_DrawString(x, y, string: str):
    gl_draw.Draw_String(x, y + 24, string)

def Sbar_DrawScrollString(x, y, width, string):

    scr_sbarscale = int(cvar.Cvar_GetCvar('scr_sbarscale').value)

    scale = common.CLAMP(1.0, scr_sbarscale, gl_screen.glwidth / 320.0)
    left = x * scale
    if cl_main.cl.gametype != protocol.GAME_DEATHMATCH:
        left += ( gl_screen.glwidth - 320.0 * scale ) / 2

    gl.glEnable(gl.GL_SCISSOR_TEST)
    gl.glScissor(left, 0, width * scale, gl_screen.glheight)

    l = len(string) * 8 + 40
    ofs  = ( host.realtime*30) % l

    Sbar_DrawString(x - ofs, y, string)

    Sbar_DrawCharacter (x - ofs + l - 32, y, ord('/'))
    Sbar_DrawCharacter (x - ofs + l - 24, y, ord('/'))
    Sbar_DrawCharacter (x - ofs + l - 16, y, ord('/'))
    Sbar_DrawString (x - ofs + l, y, string);

    gl.glDisable (gl.GL_SCISSOR_TEST);


def Sbar_DrawNum(x, y, num, digits, color):
    num = min(999, num)
    l = str(int(num))

    if len(l) > digits:
        l = l[len(l) - digits:]
    if len(l) < digits:
        x += (digits - len(l)) * 24

    for char in l:
        if char == '-':
            c = STAT_MINUS
        else:
            c = ord(char) - ord('0')

        Sbar_DrawPic(x, y, sb_nums[int(color)][c])
        x += 24

def Sbar_SortFrags() -> None:
    """
    Populates client.fragsort with active client indices sorted descending
    by frags, updating client.scoreboardlines.
    """
    # Filter active client indices and sort descending by frags
    active_indices = sorted(
        (i for i in range(cl_main.cl.maxclients) if cl_main.cl.scores[i].name),
        key=lambda i: cl_main.cl.scores[i].frags,
        reverse=True,
    )

    # Update global scoreboard state
    cl_main.scoreboardlines = len(active_indices)
    cl_main.fragsort[: cl_main.scoreboardlines] = active_indices


def Sbar_ColorForMap(m):
    # return m < 128 ? m + 8 : m + 8 ?????????????
    return ( m + 8 ) & 0xff

def Sbar_SoloScoreboard():
    string = 'Kills: %i/%i' % (cl_main.cl.stats[quakedef.STAT_MONSTERS], cl_main.cl.stats[quakedef.STAT_TOTALMONSTERS])
    left = 8 + len(string) * 8
    Sbar_DrawString(8, 12, string)

    string = 'Secrets: %i/%i' % (cl_main.cl.stats[quakedef.STAT_SECRETS], cl_main.cl.stats[quakedef.STAT_TOTALSECRETS])
    right = 312 - len(string) * 8
    Sbar_DrawString(right, 12, string)

    if not common.fitzmode:
        skill = int(cvar.Cvar_GetCvar('skill').value)
        string = 'skill %i' % skill

        Sbar_DrawString((left + right) / 2 - len(string) * 4 , 12, string)

        string = '%s (%s)' % (cl_main.cl.levelname, cl_main.cl.mapname)
        length = len(string)

        if ( length > 40 ):
            Sbar_DrawScrollString(0, 4, 320, string)
        else:
            Sbar_DrawString(160 - length * 4, 4, string)
        return

    minutes = cl_main.cl.time / 60
    seconds = cl_main.cl.time - 60 * minutes
    tens    = seconds / 10
    units   = seconds - 10 * tens
    string  = '%i:%i%i' % (minutes, tens, units)
    Sbar_DrawString(160-len(string)*4, 12, string)

    length = len(cl_main.cl.levelname)
    if length > 40:
        Sbar_DrawScrollString(0, 4, 320, cl_main.cl.levelname)
    else:
        Sbar_DrawString(160 - length * 4, 4, cl_main.cl.levelname)

def Sbar_DrawScoreboard():
    Sbar_SoloScoreboard()

    if cl_main.cl.gametype == protocol.GAME_DEATHMATCH:
        Sbar_DeathmatchOverlay()


def Sbar_DrawInventory():
    global sb_updates
    scr_sbaralpha = cvar.Cvar_GetCvar('scr_sbaralpha').value

    if common.rogue:
        if cl_main.cl.stats[quakedef.STAT_ACTIVEWEAPON] >= quakedef.RIT_LAVA_NAILGUN:
            Sbar_DrawPicAlpha (0, -24, rsb_invbar[0], scr_sbaralpha)
        else:
            Sbar_DrawPicAlpha (0, -24, rsb_invbar[1], scr_sbaralpha)

    for i in range(7):
        if cl_main.cl.items & ( quakedef.IT_SHOTGUN << i ):
            time = cl_main.cl.item_gettime[i]
            flashon = int((cl_main.cl.time - time) * 10)
            if flashon >= 10:
                if cl_main.cl.stats[quakedef.STAT_ACTIVEWEAPON] == ( quakedef.IT_SHOTGUN << i):
                    flashon = 1
                else:
                    flashon = 0
            else:
                flashon = (flashon % 5) + 2

            Sbar_DrawPic(i * 24, -16, sb_weapons[flashon][i])

            if flashon > 1:
                sb_updates = 0

    if common.hipnotic:
        grenadeflashing = 0

        for i in range(4):
            if cl_main.cl.items & ( 1 << hipweapons[i] ):
                time = cl_main.cl.item_gettime[hipweapons[i]]
                flashon = int((cl_main.cl.time - time) * 10)
                if flashon >= 10:
                    if cl_main.cl.stats[quakedef.STAT_ACTIVEWEAPON] == ( 1 << hipweapons[i]):
                        flashon = 1
                    else:
                        flashon = 0
                else:
                    flashon = (flashon % 5) + 2

                if i == 2:
                    if cl_main.cl.items & quakedef.HIT_PROXIMITY_GUN:  # noqa: SIM102
                        if flashon:
                            grenadeflashing = 1
                            Sbar_DrawPic(96, -16, hsb_weapons[flashon][2])
                elif i == 3:
                    if cl_main.cl.items & ( quakedef.IT_SHOTGUN << 4):
                        if flashon and not grenadeflashing:
                            Sbar_DrawPic (96, -16, hsb_weapons[flashon][3])
                        elif not grenadeflashing:
                            Sbar_DrawPic (96, -16, hsb_weapons[0][3])
                    else:
                        Sbar_DrawPic (96, -16, hsb_weapons[flashon][4])
                else:
                    Sbar_DrawPic (176 + (i*24), -16, hsb_weapons[flashon][i])

                if flashon > 1:
                    sb_updates = 0

    if common.rogue:  # noqa: SIM102
        if cl_main.cl.stats[quakedef.STAT_ACTIVEWEAPON] >= quakedef.RIT_LAVA_NAILGUN:
            for i in range(5):
                if cl_main.cl.stats[quakedef.STAT_ACTIVEWEAPON] == (quakedef.RIT_LAVA_NAILGUN << i):
                    Sbar_DrawPic ((i+2)*24, -16, rsb_weapons[i])


    for i in range(4):
        val = cl_main.cl.stats[quakedef.STAT_SHELLS + i]
        val = 0 if val < 0 else min(999, val)
        num = f'{val:3d}'   # C: sprintf (num, "%3i", val) -- space padded

        if num[0] != ' ':
            Sbar_DrawCharacter ( (6*i+1)*8 + 2, -24, 18 + ord(num[0]) - ord('0'))
        if num[1] != ' ':
            Sbar_DrawCharacter ( (6*i+2)*8 + 2, -24, 18 + ord(num[1]) - ord('0'))
        if num[2] != ' ':
            Sbar_DrawCharacter ( (6*i+3)*8 + 2, -24, 18 + ord(num[2]) - ord('0'))

    flashon = 0

    for i in range(6):
        if cl_main.cl.items & ( 1 << ( 17 + i )):
            time = cl_main.cl.item_gettime[17+i]
            if time and time < cl_main.cl.time - 2 and flashon:
                sb_updates = 0
            else:
                if not common.hipnotic or i > 1:
                    Sbar_DrawPic (192 + i*16, -16, sb_items[i])

            if time and  time > cl_main.cl.time - 2:
                sb_updates = 0

    if common.hipnotic:
        for i in range(2):
            if cl_main.cl.items & (1<<(24+i)):
                time = cl_main.cl.item_gettime[24 + i]
                if time and time > cl_main.cl.time - 2 and flashon:
                    sb_updates = 0
                else:
                    Sbar_DrawPic (288 + i*16, -16, hsb_items[i])

                if time and time > cl_main.cl.time - 2:
                    sb_updates = 0

    if common.rogue:
        for i in range(2):
            if cl_main.cl.items & (1<<(29+i)):
                time = cl_main.cl.item_gettime[29+i]
                if time and time > cl_main.cl.time - 2 and flashon:
                    sb_updates = 0
                else:
                    Sbar_DrawPic (288 + i*16, -16, rsb_items[i])
                if time and time > cl_main.cl.time - 2:
                    sb_updates = 0

    else:
        for i in range(4):
            if cl_main.cl.items & (1<<(28+i)):
                time = cl_main.cl.item_gettime[28+i]
                if time and time > cl_main.cl.time - 2 and flashon:
                    sb_updates = 0
                else:
                    Sbar_DrawPic (320-32 + i*8, -16, sb_sigil[i])

                if time and time > cl_main.cl.time - 2:
                    sb_updates = 0

def Sbar_DrawFrags():
    Sbar_SortFrags()

    numscores = min(scoreboardlines, 4)

    x = 184
    for i in range(numscores):
        s = cl_main.cl.scores[fragsort[i]]
        if not s.name:
            continue

        color = s.colors & 0xf0
        color = Sbar_ColorForMap (color)
        gl_draw.Draw_Fill (x + 10, 1, 28, 4, color, 1)

        color = (s.colors & 15)<<4
        color = Sbar_ColorForMap (color)
        gl_draw.Draw_Fill (x + 10, 5, 28, 3, color, 1)

        num = f'{s.frags:3d}'
        Sbar_DrawCharacter (x + 12, -24, ord(num[0]))
        Sbar_DrawCharacter (x + 20, -24, ord(num[1]))
        Sbar_DrawCharacter (x + 28, -24, ord(num[2]))

        if fragsort[i] == cl_main.cl.viewentity - 1:
            Sbar_DrawCharacter (x + 6, -24, 16)
            Sbar_DrawCharacter (x + 32, -24, 17)

        x += 32

def Sbar_DrawFace():
    global sb_updates
    teamplay = cvar.Cvar_GetCvar('teamplay').value

    if common.rogue and (cl_main.cl.maxclients != 1) and teamplay >3 and teamplay < 7:
        s = cl_main.cl.scores[cl_main.cl.viewentity - 1]
        top = s.colors & 0xf0
        bottom = (s.colors & 15 ) << 4
        top = Sbar_ColorForMap(top)
        bottom = Sbar_ColorForMap(bottom)

        if cl_main.cl.gametype == protocol.GAME_DEATHMATCH:
            xofs = 113
        else:
            xofs = ((gl_vidsdl._vid.width - 320)>>1) + 113

        Sbar_DrawPic (112, 0, rsb_teambord)
        gl_draw.Draw_Fill (xofs,24+3, 22, 9, top, 1)
        gl_draw.Draw_Fill (xofs,24+12, 22, 9, bottom, 1)

        f = s.frags
        num = f'{f:3d}'

        if top == 8:
            if num[0] != ' ':
                Sbar_DrawCharacter(113, 3, 18 + ord(num[0]) - ord('0'))
            if num[1] != ' ':
                Sbar_DrawCharacter(120, 3, 18 + ord(num[1]) - ord('0'))
            if num[2] != ' ':
                Sbar_DrawCharacter(127, 3, 18 + ord(num[2]) - ord('0'))
        else:
            Sbar_DrawCharacter (113, 3, ord(num[0]))
            Sbar_DrawCharacter (120, 3, ord(num[1]))
            Sbar_DrawCharacter (127, 3, ord(num[2]))
        return

    if cl_main.cl.items & (quakedef.IT_INVISIBILITY | quakedef.IT_INVULNERABILITY) == (quakedef.IT_INVISIBILITY | quakedef.IT_INVULNERABILITY):
        Sbar_DrawPic (112, 0, sb_face_invis_invuln)
        return
    if cl_main.cl.items & quakedef.IT_QUAD:
        Sbar_DrawPic (112, 0, sb_face_quad )
        return
    if cl_main.cl.items & quakedef.IT_INVISIBILITY:
        Sbar_DrawPic (112, 0, sb_face_invis )
        return
    if cl_main.cl.items & quakedef.IT_INVULNERABILITY:
        Sbar_DrawPic (112, 0, sb_face_invuln)
        return

    if cl_main.cl.stats[quakedef.STAT_HEALTH] >= 100:
        f = 4
    else:
        f = cl_main.cl.stats[quakedef.STAT_HEALTH] // 20

    if f < 0:
        f = 0

    if cl_main.cl.time <=cl_main.cl.faceanumtime:
        anim = 1
        sb_updates = 0
    else:
        anim = 0

    Sbar_DrawPic (112, 0, sb_faces[f][anim])



def Sbar_Draw():
    global sb_updates

    if gl_screen.scr_con_current == gl_vidsdl._vid.height:
        return

    if cl_main.cl.intermission:
        return

    gl_clear = int(cvar.Cvar_GetCvar('gl_clear').value)
    vid_gamma = int(cvar.Cvar_GetCvar('gamma').value)
    scr_sbaralpha = int(cvar.Cvar_GetCvar('scr_sbaralpha').value)
    scr_sbarscale = int(cvar.Cvar_GetCvar('scr_sbarscale').value)
    scr_viewsize = int(cvar.Cvar_GetCvar('viewsize').value)

    if sb_updates >= gl_vidsdl._vid.numpages and gl_clear and scr_sbaralpha >= 1 \
        and not(gl_vidsdl.gl_glsl_gamma_able and vid_gamma != 1):
        return

    sb_updates += 1

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_DEFAULT)

    w = common.CLAMP(320.0, scr_sbarscale * 320.0, gl_screen.glwidth)

    if ( sb_lines and gl_screen.glwidth > w):
        if scr_sbaralpha < 1:
            gl_draw.Draw_TileClear(0, gl_screen.glheight - sb_lines, gl_screen.glwidth, sb_lines)
        if cl_main.cl.gametype == protocol.GAME_DEATHMATCH:
            gl_draw.Draw_TileClear(w, gl_screen.glheight - sb_lines, gl_screen.glwidth - w, sb_lines)
        else:
            gl_draw.Draw_TileClear(0, gl_screen.glheight - sb_lines, (gl_screen.glwidth - w)/2, sb_lines)
            gl_draw.Draw_TileClear ((gl_screen.glwidth - w) / 2.0 + w, gl_screen.glheight - sb_lines, (gl_screen.glwidth - w) / 2.0, sb_lines)

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_SBAR)

    if scr_viewsize < 110 :
        Sbar_DrawInventory()
        if cl_main.cl.maxclients != 1:
            Sbar_DrawFrags()

    if sb_showscores or cl_main.cl.stats[quakedef.STAT_HEALTH] <= 0:
        Sbar_DrawPicAlpha(0, 0, sb_scorebar, scr_sbaralpha)
        Sbar_DrawScoreboard()
        sb_updates = 0

    elif scr_viewsize < 120:
        Sbar_DrawPicAlpha(0, 0, sb_sbar, scr_sbaralpha)

        if common.hipnotic:
            if cl_main.cl.items & quakedef.IT_KEY1:
                Sbar_DrawPic(209, 3, sb_items[0])
            if cl_main.cl.items & quakedef.IT_KEY2:
                Sbar_DrawPic(209, 12, sb_items[1])

        if cl_main.cl.items & quakedef.IT_INVULNERABILITY:
            Sbar_DrawNum(24, 0, 666, 3, 1)
            Sbar_DrawPic(0, 0, gl_draw.draw_disc)
        else:
            if common.rogue:
                Sbar_DrawNum(24, 0, cl_main.cl.stats[quakedef.STAT_ARMOR], 3, cl_main.cl.stats[quakedef.STAT_ARMOR] <= 25)
                if (cl_main.cl.items & quakedef.RIT_ARMOR3):
                    Sbar_DrawPic (0, 0, sb_armor[2])
                elif (cl_main.cl.items & quakedef.RIT_ARMOR2):
                    Sbar_DrawPic (0, 0, sb_armor[1])
                elif (cl_main.cl.items & quakedef.RIT_ARMOR1):
                    Sbar_DrawPic (0, 0, sb_armor[0])

            else:
                Sbar_DrawNum (24, 0, cl_main.cl.stats[quakedef.STAT_ARMOR], 3 , cl_main.cl.stats[quakedef.STAT_ARMOR] <= 25)
                if (cl_main.cl.items & quakedef.IT_ARMOR3):
                    Sbar_DrawPic (0, 0, sb_armor[2])
                elif (cl_main.cl.items & quakedef.IT_ARMOR2):
                    Sbar_DrawPic (0, 0, sb_armor[1])
                elif (cl_main.cl.items & quakedef.IT_ARMOR1):
                    Sbar_DrawPic (0, 0, sb_armor[0])

        Sbar_DrawFace()

        Sbar_DrawNum (136, 0, cl_main.cl.stats[quakedef.STAT_HEALTH], 3 , cl_main.cl.stats[quakedef.STAT_HEALTH] <= 25)

        if (common.rogue):
            if (cl_main.cl.items & quakedef.RIT_SHELLS):
                Sbar_DrawPic (224, 0, sb_ammo[0])
            elif (cl_main.cl.items & quakedef.RIT_NAILS):
                Sbar_DrawPic (224, 0, sb_ammo[1])
            elif (cl_main.cl.items & quakedef.RIT_ROCKETS):
                Sbar_DrawPic (224, 0, sb_ammo[2])
            elif (cl_main.cl.items & quakedef.RIT_CELLS):
                Sbar_DrawPic (224, 0, sb_ammo[3])
            elif (cl_main.cl.items & quakedef.RIT_LAVA_NAILS):
                Sbar_DrawPic (224, 0, rsb_ammo[0])
            elif (cl_main.cl.items & quakedef.RIT_PLASMA_AMMO):
                Sbar_DrawPic (224, 0, rsb_ammo[1])
            elif (cl_main.cl.items & quakedef.RIT_MULTI_ROCKETS):
                Sbar_DrawPic (224, 0, rsb_ammo[2])

        else:
            if (cl_main.cl.items & quakedef.IT_SHELLS):
                Sbar_DrawPic (224, 0, sb_ammo[0])
            elif (cl_main.cl.items & quakedef.IT_NAILS):
                Sbar_DrawPic (224, 0, sb_ammo[1])
            elif (cl_main.cl.items & quakedef.IT_ROCKETS):
                Sbar_DrawPic (224, 0, sb_ammo[2])
            elif (cl_main.cl.items & quakedef.IT_CELLS):
                Sbar_DrawPic (224, 0, sb_ammo[3])


        Sbar_DrawNum (248, 0, cl_main.cl.stats[quakedef.STAT_AMMO], 3, cl_main.cl.stats[quakedef.STAT_AMMO] <= 10)

        if (cl_main.cl.gametype == protocol.GAME_DEATHMATCH):
            Sbar_MiniDeathmatchOverlay ()


def Sbar_LoadPics():
    global sb_nums, sb_colon, sb_slash
    global sb_weapons, sb_ammo, sb_armor
    global sb_items, sb_faces, sb_face_invis, sb_face_quad
    global sb_face_invuln, sb_face_invis_invuln
    global sb_sbar, sb_ibar, sb_scorebar
    global hsb_weapons, hsb_items
    global rsb_weapons, rsb_items, rsb_teambord

    for i in range(10):
        sb_nums[0][i] = gl_draw.Draw_PicFromWad('num_%i' % i)
        sb_nums[1][i] = gl_draw.Draw_PicFromWad('anum_%i' % i)

    sb_nums[0][10] = gl_draw.Draw_PicFromWad('num_minus')
    sb_nums[1][10] = gl_draw.Draw_PicFromWad('anum_minus')

    sb_colon = gl_draw.Draw_PicFromWad ("num_colon")
    sb_slash = gl_draw.Draw_PicFromWad ("num_slash")

    sb_weapons[0][0] = gl_draw.Draw_PicFromWad ("inv_shotgun")
    sb_weapons[0][1] = gl_draw.Draw_PicFromWad ("inv_sshotgun")
    sb_weapons[0][2] = gl_draw.Draw_PicFromWad ("inv_nailgun")
    sb_weapons[0][3] = gl_draw.Draw_PicFromWad ("inv_snailgun")
    sb_weapons[0][4] = gl_draw.Draw_PicFromWad ("inv_rlaunch")
    sb_weapons[0][5] = gl_draw.Draw_PicFromWad ("inv_srlaunch")
    sb_weapons[0][6] = gl_draw.Draw_PicFromWad ("inv_lightng")

    sb_weapons[1][0] = gl_draw.Draw_PicFromWad ("inv2_shotgun")
    sb_weapons[1][1] = gl_draw.Draw_PicFromWad ("inv2_sshotgun")
    sb_weapons[1][2] = gl_draw.Draw_PicFromWad ("inv2_nailgun")
    sb_weapons[1][3] = gl_draw.Draw_PicFromWad ("inv2_snailgun")
    sb_weapons[1][4] = gl_draw.Draw_PicFromWad ("inv2_rlaunch")
    sb_weapons[1][5] = gl_draw.Draw_PicFromWad ("inv2_srlaunch")
    sb_weapons[1][6] = gl_draw.Draw_PicFromWad ("inv2_lightng")

    for i in range(5):
        sb_weapons[2+i][0] = gl_draw.Draw_PicFromWad ("inva%i_shotgun"%(i+1))
        sb_weapons[2+i][1] = gl_draw.Draw_PicFromWad ("inva%i_sshotgun"%(i+1))
        sb_weapons[2+i][2] = gl_draw.Draw_PicFromWad ("inva%i_nailgun"%(i+1))
        sb_weapons[2+i][3] = gl_draw.Draw_PicFromWad ("inva%i_snailgun"%(i+1))
        sb_weapons[2+i][4] = gl_draw.Draw_PicFromWad ("inva%i_rlaunch"%(i+1))
        sb_weapons[2+i][5] = gl_draw.Draw_PicFromWad ("inva%i_srlaunch"%(i+1))
        sb_weapons[2+i][6] = gl_draw.Draw_PicFromWad ("inva%i_lightng"%(i+1))

    sb_ammo[0] = gl_draw.Draw_PicFromWad ("sb_shells")
    sb_ammo[1] = gl_draw.Draw_PicFromWad ("sb_nails")
    sb_ammo[2] = gl_draw.Draw_PicFromWad ("sb_rocket")
    sb_ammo[3] = gl_draw.Draw_PicFromWad ("sb_cells")

    sb_armor[0] = gl_draw.Draw_PicFromWad ("sb_armor1")
    sb_armor[1] = gl_draw.Draw_PicFromWad ("sb_armor2")
    sb_armor[2] = gl_draw.Draw_PicFromWad ("sb_armor3")

    sb_items[0] = gl_draw.Draw_PicFromWad ("sb_key1")
    sb_items[1] = gl_draw.Draw_PicFromWad ("sb_key2")
    sb_items[2] = gl_draw.Draw_PicFromWad ("sb_invis")
    sb_items[3] = gl_draw.Draw_PicFromWad ("sb_invuln")
    sb_items[4] = gl_draw.Draw_PicFromWad ("sb_suit")
    sb_items[5] = gl_draw.Draw_PicFromWad ("sb_quad")

    sb_sigil[0] = gl_draw.Draw_PicFromWad ("sb_sigil1")
    sb_sigil[1] = gl_draw.Draw_PicFromWad ("sb_sigil2")
    sb_sigil[2] = gl_draw.Draw_PicFromWad ("sb_sigil3")
    sb_sigil[3] = gl_draw.Draw_PicFromWad ("sb_sigil4")

    sb_faces[4][0] = gl_draw.Draw_PicFromWad ("face1")
    sb_faces[4][1] = gl_draw.Draw_PicFromWad ("face_p1")
    sb_faces[3][0] = gl_draw.Draw_PicFromWad ("face2")
    sb_faces[3][1] = gl_draw.Draw_PicFromWad ("face_p2")
    sb_faces[2][0] = gl_draw.Draw_PicFromWad ("face3")
    sb_faces[2][1] = gl_draw.Draw_PicFromWad ("face_p3")
    sb_faces[1][0] = gl_draw.Draw_PicFromWad ("face4")
    sb_faces[1][1] = gl_draw.Draw_PicFromWad ("face_p4")
    sb_faces[0][0] = gl_draw.Draw_PicFromWad ("face5")
    sb_faces[0][1] = gl_draw.Draw_PicFromWad ("face_p5")

    sb_face_invis = gl_draw.Draw_PicFromWad ("face_invis")
    sb_face_invuln = gl_draw.Draw_PicFromWad ("face_invul2")
    sb_face_invis_invuln = gl_draw.Draw_PicFromWad ("face_inv2")
    sb_face_quad = gl_draw.Draw_PicFromWad ("face_quad")

    sb_sbar = gl_draw.Draw_PicFromWad ("sbar")
    sb_ibar = gl_draw.Draw_PicFromWad ("ibar")
    sb_scorebar = gl_draw.Draw_PicFromWad ("scorebar")

    if common.hipnotic:
        hsb_weapons[0][0] = gl_draw.Draw_PicFromWad ("inv_laser")
        hsb_weapons[0][1] = gl_draw.Draw_PicFromWad ("inv_mjolnir")
        hsb_weapons[0][2] = gl_draw.Draw_PicFromWad ("inv_gren_prox")
        hsb_weapons[0][3] = gl_draw.Draw_PicFromWad ("inv_prox_gren")
        hsb_weapons[0][4] = gl_draw.Draw_PicFromWad ("inv_prox")

        hsb_weapons[1][0] = gl_draw.Draw_PicFromWad ("inv2_laser")
        hsb_weapons[1][1] = gl_draw.Draw_PicFromWad ("inv2_mjolnir")
        hsb_weapons[1][2] = gl_draw.Draw_PicFromWad ("inv2_gren_prox")
        hsb_weapons[1][3] = gl_draw.Draw_PicFromWad ("inv2_prox_gren")
        hsb_weapons[1][4] = gl_draw.Draw_PicFromWad ("inv2_prox")

        for i in range(5):
            hsb_weapons[2+i][0] = gl_draw.Draw_PicFromWad ("inva%i_laser"%(i+1))
            hsb_weapons[2+i][1] = gl_draw.Draw_PicFromWad ("inva%i_mjolnir"%(i+1))
            hsb_weapons[2+i][2] = gl_draw.Draw_PicFromWad ("inva%i_gren_prox"%(i+1))
            hsb_weapons[2+i][3] = gl_draw.Draw_PicFromWad ("inva%i_prox_gren"%(i+1))
            hsb_weapons[2+i][4] = gl_draw.Draw_PicFromWad ("inva%i_prox"%(i+1))

        hsb_items[0] = gl_draw.Draw_PicFromWad ("sb_wsuit")
        hsb_items[1] = gl_draw.Draw_PicFromWad ("sb_eshld")


    if (common.rogue):
        rsb_invbar[0] = gl_draw.Draw_PicFromWad ("r_invbar1")
        rsb_invbar[1] = gl_draw.Draw_PicFromWad ("r_invbar2")

        rsb_weapons[0] = gl_draw.Draw_PicFromWad ("r_lava")
        rsb_weapons[1] = gl_draw.Draw_PicFromWad ("r_superlava")
        rsb_weapons[2] = gl_draw.Draw_PicFromWad ("r_gren")
        rsb_weapons[3] = gl_draw.Draw_PicFromWad ("r_multirock")
        rsb_weapons[4] = gl_draw.Draw_PicFromWad ("r_plasma")

        rsb_items[0] = gl_draw.Draw_PicFromWad ("r_shield1")
        rsb_items[1] = gl_draw.Draw_PicFromWad ("r_agrav1")

        rsb_teambord = gl_draw.Draw_PicFromWad ("r_teambord")

        rsb_ammo[0] = gl_draw.Draw_PicFromWad ("r_ammolava")
        rsb_ammo[1] = gl_draw.Draw_PicFromWad ("r_ammomulti")
        rsb_ammo[2] = gl_draw.Draw_PicFromWad ("r_ammoplasma")

def Sbar_Init():
    global hipweapons

    hipweapons = [quakedef.HIT_LASER_CANNON_BIT, quakedef.HIT_MJOLNIR_BIT, 4, quakedef.HIT_PROXIMITY_GUN_BIT]
    _cmd.Cmd_AddCommand('+showscores', Sbar_ShowScores)
    _cmd.Cmd_AddCommand('-showscores', Sbar_DontShowScores)

    Sbar_LoadPics()

def Sbar_IntermissionNumber(x, y, num, digits, color):
    num_str = str(num)

    for char in num_str:
        if char == "-":
            frame = STAT_MINUS
        else:
            frame = int(char)

        gl_draw.Draw_Pic(x, y, sb_nums[color][frame])
        x += 24


def Sbar_IntermissionPicForChar(c: int, color) -> wad.qpic_t:
    char = chr(c) if isinstance(c, int) else c

    if char.isdigit():
        return sb_nums[color][int(char)]
    if char == "/":
        return sb_slash
    if char == ":":
        return sb_colon
    if char == "-":
        return sb_nums[color][STAT_MINUS]

    return None

def Sbar_IntermissionTextWidth(_str: str, color) -> int:
    len = 0
    for char in _str:
        pic: wad.qpic_t = Sbar_IntermissionPicForChar(char, color)
        len += pic.width if pic else 24
    return len

def Sbar_IntermissionText(x, y, _str: str, color):
    for char in _str:
        pic: wad.qpic_t = Sbar_IntermissionPicForChar(char, color)
        if not pic:
            continue
        gl_draw.Draw_Pic(x, y, pic)
        x += pic.width if pic else 24

def Sbar_DeathmatchOverlay():

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_MENU)

    pic = gl_draw.Draw_CachePic('gfx/ranking.lmp')
    menu.M_DrawPic((320-pic.width)/2, 8, pic)

    Sbar_SortFrags()

    l = scoreboardlines

    x = 80
    y = 40

    for i in range(l):
        k = fragsort[i]
        s = cl_main.cl.scores[k]
        if not s.name:
            continue

        top = s.colors & 0xf0
        bottom = (s.colors & 15)<<4
        top = Sbar_ColorForMap (top)
        bottom = Sbar_ColorForMap (bottom)

        gl_draw.Draw_Fill ( x, y, 40, 4, top, 1)
        gl_draw.Draw_Fill ( x, y+4, 40, 4, bottom, 1)

        f = s.frags
        num = f'{f:3d}'

        gl_draw.Draw_Character ( x+8 , y,  ord(num[0]));
        gl_draw.Draw_Character ( x+16 , y, ord(num[1]))
        gl_draw.Draw_Character ( x+24 , y, ord(num[2]))

        if k == cl_main.cl.viewentity - 1:
            gl_draw.Draw_Character( x - 8, y, 12)

        menu.M_Print(x+64, y, s.name)

        y += 10
    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_SBAR)



def Sbar_MiniDeathmatchOverlay():
    scr_sbarscale = cvar.Cvar_GetCvar('scr_sbarscale').value
    scr_viewsize  = cvar.Cvar_GetCvar('viewsize').value


    scale = common.CLAMP(1.0, scr_sbarscale, gl_screen.glwidth / 320.)

    if gl_screen.glwidth / scale < 512 or scr_viewsize >= 120:
        return


    Sbar_SortFrags()

    numlines = 3 if scr_viewsize >= 110 else 6

    for i in range(scoreboardlines):
        if fragsort[i] == cl_main.cl.viewentity - 1:
            break

    if i == scoreboardlines:
        i = 0
    else:
        i = i - numlines / 2

    if i > scoreboardlines - numlines:
        i = scoreboardlines - numlines

    if i < 0:
        i = 0

    x = 324
    y = 24 if scr_viewsize >= 110 else 0

    for i in range(scoreboardlines):
        if y > 48:
            break
        k = fragsort[i]
        s = cl_main.cl.scores[k]
        if not s.name:
            continue
        y += 8

        top = s.colors & 0xf0;
        bottom = (s.colors & 15)<<4;
        top = Sbar_ColorForMap (top);
        bottom = Sbar_ColorForMap (bottom);

        gl_draw.Draw_Fill (x, y+1, 40, 4, top, 1);
        gl_draw.Draw_Fill (x, y+5, 40, 3, bottom, 1)

        f = s.frags;
        num = f'{f:3d}'
        gl_draw.Draw_Character (x+ 8, y, ord(num[0]))
        gl_draw.Draw_Character (x+16, y, ord(num[1]))
        gl_draw.Draw_Character (x+24, y, ord(num[2]))

        if k == cl_main.cl.viewentity - 1:
            gl_draw.Draw_Character(x, y, 16)
            gl_draw.Draw_Character(x + 32, y, 17)

        gl_draw.Draw_String (x+48, y, s.name)


def Sbar_IntermissionOverlay():

    if cl_main.cl.gametype == protocol.GAME_DEATHMATCH:
        Sbar_DeathmatchOverlay()
        return

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_MENU)

    time = f'{cl_main.cl.completed_time / 60}: {cl_main.cl.completed_time % 60:02}'
    secrets  = f'{cl_main.cl.stats[quakedef.STAT_SECRETS]}/{cl_main.cl.stats[quakedef.STAT_TOTALSECRETS]}'
    monsters = f'{cl_main.cl.stats[quakedef.STAT_MONSTERS]}/{cl_main.cl.stats[quakedef.STAT_TOTALMONSTERS]}'

    ltime     = Sbar_IntermissionTextWidth (time, 0)
    lsecrets  = Sbar_IntermissionTextWidth (secrets, 0)
    lmonsters = Sbar_IntermissionTextWidth (monsters, 0)

    total = max (ltime, lsecrets)
    total = max (lmonsters, total)

    pic = gl_draw.Draw_CachePic ("gfx/inter.lmp")
    total += pic.width + 24
    total = min (320, total)
    gl_draw.Draw_Pic (160 - total / 2, 56, pic)

    pic = gl_draw.Draw_CachePic ("gfx/complete.lmp")
    gl_draw.Draw_Pic (160 - pic.width / 2, 24, pic)

    Sbar_IntermissionText (160 + total / 2 - ltime, 64, time, 0)
    Sbar_IntermissionText (160 + total / 2 - lsecrets, 104, secrets, 0)
    Sbar_IntermissionText (160 + total / 2 - lmonsters, 144, monsters, 0)


def Sbar_FinaleOverlay():
    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_MENU)
    pic = gl_draw.Draw_CachePic('glx/finale.lmp')
    gl_draw.Draw_Pic((320 - pic.width)/2, 16, pic)
