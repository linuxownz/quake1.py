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
import protocol
import quakedef
import screen
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
hipweapons = [quakedef.HIT_LASER_CANNON, quakedef.HIT_MJOLNIR_BIT, 4, quakedef.HIT_PROXIMITY_GUN_BIT]
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

    Sbar_DrawCharacter (x - ofs + l - 32, y, '/')
    Sbar_DrawCharacter (x - ofs + l - 24, y, '/')
    Sbar_DrawCharacter (x - ofs + l - 16, y, '/')
    Sbar_DrawString (x - ofs + l, y, string);

    gl.glDisable (gl.GL_SCISSOR_TEST);


def Sbar_DrawNum(x, y, num, digits, color):
    num = min(999, num)
    l = str(num)
    for char in l:
        c = ord(char)
        if c == ord('-'):
            c = 10
        else:
            c -= ord('0')

        Sbar_DrawPic(x, y, sb_nums[color][c])
        x += 24

def Sbar_SortFrags():
    raise NotImplementedError

def Sbar_ColorForMap(m):
    # return m < 128 ? m + 8 : m + 8 ?????????????
    return m + 8

def Sbar_SoloScoreboard():
    string = 'Kills: %i/%i' % (cl_main.cl.stats[quakedef.STAT_MONSTERS], cl_main.cl.stats[quakedef.STAT_TOTALMONSTERS])
    left = 8 + len(string) * 8
    Sbar_DrawString(8, 12, string)

    string = 'Secrets: %i/%i' % (cl_main.cl.stats[quakedef.STAT_SECRETS], cl_main.cl.stats[quakedef.STAT_TOTALSECRETS])
    right = 312 - len(str) * 8
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

def Sbar_Draw():
    global sb_updates

    if gl_screen.scr_con_current == gl_vidsdl._vid.height:
        return

    if cl_main.cl.intermission:
        return

    gl_clear = int(cvar.Cvar_GetCvar('gl_clear').value)
    vid_gamma = int(cvar.Cvar_GetCvar('vid_gamma').value)
    scr_sbaralpha = int(cvar.Cvar_GetCvar('scr_sbaralpha').value)
    scr_sbarscale = int(cvar.Cvar_GetCvar('scr_sbarscale').value)
    scr_viewsize = int(cvar.Cvar_GetCvar('scr_viewsize').value)

    if sb_updates >= gl_vidsdl._vid.numpages and gl_clear and scr_sbaralpha >= 1 \
        and not(gl_vidsdl.gl_glsl_gamma_able and vid_gamma != 1):
        return

    sb_updates += 1

    gl_draw.GL_SetCanvas(screen.canvastype.CANVAS_DEFAULT)

    w = common.CLAMP(320.0, scr_sbarscale * 320.0, gl_screen.glwidth)

    if ( sb_lines and gl_screen.glwidth > w):
        if scr_sbaralpha < 1:
            gl_draw.Draw_TileClear(0, gl_screen.glheight - sb_lines, gl_screen.glwidth, sb_lines)
        if cl_main.cl.gametype == protocol.GAME_DEATHMATCH:
            gl_draw.Draw_TileClear(w, gl_screen.glheight - sb_lines, gl_screen.glwidth - w, sb_lines)
        else:
            gl_draw.Draw_TileClear(0, gl_screen.glheight - sb_lines, (gl_screen.glwidth - w)/2, sb_lines)
            gl_draw.Draw_TileClear ((glwidth - w) / 2.0 + w, glheight - sb_lines, (glwidth - w) / 2.0, sb_lines)

    gl_draw.GL_SetCanvas(screen.canvastype.CANVAS_SBAR)

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
                if (cl.items & RIT_ARMOR3):
                    Sbar_DrawPic (0, 0, sb_armor[2])
                elif (cl.items & RIT_ARMOR2):
                    Sbar_DrawPic (0, 0, sb_armor[1])
                elif (cl.items & RIT_ARMOR1):
                    Sbar_DrawPic (0, 0, sb_armor[0])

            else:
                Sbar_DrawNum (24, 0, cl.stats[STAT_ARMOR], 3 , cl.stats[STAT_ARMOR] <= 25)
                if (cl.items & IT_ARMOR3):
                    Sbar_DrawPic (0, 0, sb_armor[2])
                elif (cl.items & IT_ARMOR2):
                    Sbar_DrawPic (0, 0, sb_armor[1])
                elif (cl.items & IT_ARMOR1):
                    Sbar_DrawPic (0, 0, sb_armor[0])

        Sbar_DrawFace()

        Sbar_DrawNum (136, 0, cl.stats[STAT_HEALTH], 3 , cl.stats[STAT_HEALTH] <= 25)

        if (rogue):
            if (cl.items & RIT_SHELLS):
                Sbar_DrawPic (224, 0, sb_ammo[0])
            elif (cl.items & RIT_NAILS):
                Sbar_DrawPic (224, 0, sb_ammo[1])
            elif (cl.items & RIT_ROCKETS):
                Sbar_DrawPic (224, 0, sb_ammo[2])
            elif (cl.items & RIT_CELLS):
                Sbar_DrawPic (224, 0, sb_ammo[3])
            elif (cl.items & RIT_LAVA_NAILS):
                Sbar_DrawPic (224, 0, rsb_ammo[0])
            elif (cl.items & RIT_PLASMA_AMMO):
                Sbar_DrawPic (224, 0, rsb_ammo[1])
            elif (cl.items & RIT_MULTI_ROCKETS):
                Sbar_DrawPic (224, 0, rsb_ammo[2])

        else:
            if (cl.items & IT_SHELLS):
                Sbar_DrawPic (224, 0, sb_ammo[0])
            elif (cl.items & IT_NAILS):
                Sbar_DrawPic (224, 0, sb_ammo[1])
            elif (cl.items & IT_ROCKETS):
                Sbar_DrawPic (224, 0, sb_ammo[2])
            elif (cl.items & IT_CELLS):
                Sbar_DrawPic (224, 0, sb_ammo[3])


        Sbar_DrawNum (248, 0, cl.stats[STAT_AMMO], 3, cl.stats[STAT_AMMO] <= 10)

        if (cl.gametype == GAME_DEATHMATCH):
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
    _cmd.Cmd_AddCommand('+showscores', Sbar_ShowScores)
    _cmd.Cmd_AddCommand('-showscores', Sbar_DontShowScores)

    Sbar_LoadPics()

