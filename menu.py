#menu.py

from dataclasses import dataclass
from enum import Enum
from random import randint

import _cmd
import cl_input
import cl_main
import common
import console
import cvar
import gl_draw
import gl_screen
import gl_vidsdl
import host
import host_cmd
import in_sdl
import keys
import net_main
import quakedef
import snd_dma
import sv_main
import vid
import wad

vid_menucmdfn = None
vid_menudrawfn = None
vid_menukeyfn = None

class m_state_e(Enum):
    m_none = 0
    m_main = 1
    m_singleplayer = 2
    m_load = 3
    m_save = 4
    m_multiplayer = 5
    m_setup = 6
    m_net = 7
    m_options = 8
    m_video = 9
    m_keys = 10
    m_help = 11
    m_quit = 12
    m_lanconfig = 13
    m_gameoptions = 14
    m_search = 15
    m_slist  = 16

class opt_items_e(Enum):
    OPT_CUSTOMIZE    = 1
    OPT_CONSOLE      = 2
    OPT_DEFAULTS     = 3
    OPT_SCALE        = 4
    OPT_SCRSIZE      = 5
    OPT_GAMMA        = 6
    OPT_CONTRAST     = 7
    OPT_MOUSESPEED   = 8
    OPT_SBALPHA      = 9
    OPT_SNDVOL       = 10
    OPT_MUSICVOL     = 11
    OPT_MUSICEXT     = 12
    OPT_ALWAYRUN     = 13
    OPT_INVMOUSE     = 14
    OPT_ALWAYSMLOOK  = 15
    OPT_LOOKSPRING   = 16
    OPT_LOOKSTRAFE   = 17
    OPT_VIDEO        = 18
    OPTIONS_ITEMS    = 19

class always_run_e(Enum):
    ALWAYSRUN_OFF        = 0,
    ALWAYSRUN_VANILLA    = 1,
    ALWAYSRUN_QUAKESPASM = 2
    ALWAYSRUN_ITEMS      = 3

bindnames = [
    ['+attack', 'attack'],
    ['impulse 10', 'next weapon'],
    ['impulse 12', 'prev weapon'],
    ['+jump', 'jump / swim up'],
    ['+forward', 'walk forward'],
    ['+back', 'backpedal'],
    ['+left', 'turn left'],
    ['+right', 'turn right'],
    ['+speed', 'run'],
    ['+moveleft', 'step left'],
    ['+moveright', 'step right'],
    ['+strafe', 'sidestep'],
    ['+lookup', 'look up'],
    ['+lookdown', 'look down'],
    ['centerview', 'center view'],
    ['+mlook', 'mouse look'],
    ['+klook', 'keyboard look'],
    ['+moveup', 'swim up'],
    ['+movedown', 'swim down'],
]

NUMCOMMANDS = len(bindnames)

@dataclass(slots=True, frozen=True)
class Level:
    name: str
    description: str

levels: tuple[Level, ...] = (
    Level("start", "Entrance"),  # 0
    Level("e1m1", "Slipgate Complex"),  # Episode 1
    Level("e1m2", "Castle of the Damned"),
    Level("e1m3", "The Necropolis"),
    Level("e1m4", "The Grisly Grotto"),
    Level("e1m5", "Gloom Keep"),
    Level("e1m6", "The Door To Chthon"),
    Level("e1m7", "The House of Chthon"),
    Level("e1m8", "Ziggurat Vertigo"),
    Level("e2m1", "The Installation"),  # Episode 2
    Level("e2m2", "Ogre Citadel"),
    Level("e2m3", "Crypt of Decay"),
    Level("e2m4", "The Ebon Fortress"),
    Level("e2m5", "The Wizard's Manse"),
    Level("e2m6", "The Dismal Oubliette"),
    Level("e2m7", "Underearth"),
    Level("e3m1", "Termination Central"),  # Episode 3
    Level("e3m2", "The Vaults of Zin"),
    Level("e3m3", "The Tomb of Terror"),
    Level("e3m4", "Satan's Dark Delight"),
    Level("e3m5", "Wind Tunnels"),
    Level("e3m6", "Chambers of Torment"),
    Level("e3m7", "The Haunted Halls"),
    Level("e4m1", "The Sewage System"),  # Episode 4
    Level("e4m2", "The Tower of Despair"),
    Level("e4m3", "The Elder God Shrine"),
    Level("e4m4", "The Palace of Hate"),
    Level("e4m5", "Hell's Atrium"),
    Level("e4m6", "The Pain Maze"),
    Level("e4m7", "Azure Agony"),
    Level("e4m8", "The Nameless City"),
    Level("end", "Shub-Niggurath's Pit"),  # End
    Level("dm1", "Place of Two Deaths"),  # Deathmatch
    Level("dm2", "Claustrophobopolis"),
    Level("dm3", "The Abandoned Base"),
    Level("dm4", "The Bad Place"),
    Level("dm5", "The Cistern"),
    Level("dm6", "The Dark Zone"),
)

# Number of entries constant for array iteration bounds
NUM_LEVELS: int = len(levels)

# Fixed array definition: level_t hipnoticlevels[]
hipnoticlevels: tuple[Level, ...] = (
    Level("start", "Command HQ"),  # 0
    Level("hip1m1", "The Pumping Station"),  # Episode 1
    Level("hip1m2", "Storage Facility"),
    Level("hip1m3", "The Lost Mine"),
    Level("hip1m4", "Research Facility"),
    Level("hip1m5", "Military Complex"),
    Level("hip2m1", "Ancient Realms"),  # Episode 2
    Level("hip2m2", "The Black Cathedral"),
    Level("hip2m3", "The Catacombs"),
    Level("hip2m4", "The Crypt"),
    Level("hip2m5", "Mortum's Keep"),
    Level("hip2m6", "The Gremlin's Domain"),
    Level("hip3m1", "Tur Torment"),  # Episode 3
    Level("hip3m2", "Pandemonium"),
    Level("hip3m3", "Limbo"),
    Level("hip3m4", "The Gauntlet"),
    Level("hipend", "Armagon's Lair"),  # End
    Level("hipdm1", "The Edge of Oblivion"),  # Deathmatch
)

NUM_HIPNOTIC_LEVELS: int = len(hipnoticlevels)

# Fixed array definition: level_t roguelevels[]
roguelevels: tuple[Level, ...] = (
    Level("start", "Split Decision"),  # Start hub
    Level("r1m1", "Deviant's Domain"),  # Episode 1
    Level("r1m2", "Dread Portal"),
    Level("r1m3", "Judgement Call"),
    Level("r1m4", "Cave of Death"),
    Level("r1m5", "Towers of Wrath"),
    Level("r1m6", "Temple of Pain"),
    Level("r1m7", "Tomb of the Overlord"),
    Level("r2m1", "Tempus Fugit"),  # Episode 2
    Level("r2m2", "Elemental Fury I"),
    Level("r2m3", "Elemental Fury II"),
    Level("r2m4", "Curse of Osiris"),
    Level("r2m5", "Wizard's Keep"),
    Level("r2m6", "Blood Sacrifice"),
    Level("r2m7", "Last Bastion"),
    Level("r2m8", "Source of Evil"),
    Level("ctf1", "Division of Change"),  # Capture The Flag
)

NUM_ROGUE_LEVELS: int = len(roguelevels)

@dataclass(slots=True, frozen=True)
class Episode:
    description: str
    firstLevel: int
    levels: int


episodes: tuple[Episode, ...] = (
    Episode("Welcome to Quake", 0, 1),
    Episode("Doomed Dimension", 1, 8),
    Episode("Realm of Black Magic", 9, 7),
    Episode("Netherworld", 16, 7),
    Episode("The Elder World", 23, 8),
    Episode("Final Level", 31, 1),
    Episode("Deathmatch Arena", 32, 6),
)

hipnoticepisodes: tuple[Episode, ...] = (
    Episode("Scourge of Armagon", 0, 1),
    Episode("Fortress of the Dead", 1, 5),
    Episode("Dominion of Darkness", 6, 6),
    Episode("The Rift", 12, 4),
    Episode("Final Level", 16, 1),
    Episode("Deathmatch Arena", 17, 1),
)

rogueepisodes: tuple[Episode, ...] = (
    Episode("Introduction", 0, 1),
    Episode("Hell's Fortress", 1, 7),
    Episode("Corridors of Time", 8, 8),
    Episode("Deathmatch Arena", 16, 1),
)

NUM_EPISODES: int = len(episodes)
NUM_HIPNOTIC_EPISODES: int = len(hipnoticepisodes)
NUM_ROGUE_EPISODES: int = len(rogueepisodes)

startepisode = 0
startlevel = 0
maxplayers = 0

m_serverInfoMessage = False
m_serverInfoMessageTime = 0.0

gameoptions_cursor_table = [40, 56, 64, 72, 80, 88, 96, 112, 120]
NUM_GAMEOPTIONS = 9
gameoptions_cursor = 0


SLIDER_RANGE = 10

options_cursor = 0
keys_cursor = 0
slist_cursor = 0
slist_sorted = False

bind_grab = False

m_state : m_state_e = m_state_e.m_none

m_entersound = False
m_recursiveDraw = False

m_return_state : m_state_e = m_state_e.m_none
m_return_onerror = False
m_return_reason = ''

m_singleplayer_cursor = 0
SINGLEPLAYER_ITEMS = 3

setup_cursor = 4
setup_cursor_table = [40, 56, 80, 104, 140]

setup_hostname = ''
setup_myname   = ''
setup_oldtop   = 0
setup_oldbottom= 0
setup_top      = 0
setup_bottom   = 0

NUM_SETUP_CMDS = 5

help_page = 0
NUM_HELP_PAGES = 6
MAIN_ITEMS = 5

msgNumber = 0
m_quit_prestate: m_state_e = m_state_e.m_none
wasInMenus = False

m_multiplayer_cursor = 0
MULTIPLAYER_ITEMS = 3
m_net_cursor = 0
m_net_items = 0

m_save_demonum = 0
m_main_cursor = 0

MAX_SAVEGAMES = 20
m_filenames: list[str] = ['' for _ in range (MAX_SAVEGAMES)]
loadable: list[int] = [0 for _ in range(MAX_SAVEGAMES)]

load_cursor = 0

lanConfig_cursor = -1
lanConfig_cursor_table = [72, 92, 124]
NUM_LANCONFIG_CMDS = 3

lanConfig_port = 0
lanConfig_portname = ''
lanConfig_joinname = ''

net_helpMessage = [
    '(LAN = Local Area Network)',
    'Commonly used to play',
    'over the Internet, but',
    'also used on a Local',
    'Area Network',
]

searchComplete = False
searchCompleteTime = 0.0

def StartingGame():
    return m_multiplayer_cursor == 1

def JoiningGame():
    return m_multiplayer_cursor == 0

def TCPIPConfig():
    return m_net_cursor == 1


def M_DrawCharacter(cx, line, num):
    gl_draw.Draw_Character(cx, line, num)


def M_Print(cx: int, cy: int, string: str | bytes | bytearray) -> None:
    # Convert string input to bytes if necessary to handle character codes safely
    if isinstance(string, str):
        char_bytes = string.encode("latin-1", errors="replace")
    else:
        char_bytes = string

    for char_code in char_bytes:
        # Shift character code by +128 to sample menu font glyphs
        M_DrawCharacter(cx, cy, (char_code + 128) & 0xFF)
        cx += 8

def M_PrintWhite(cx, cy, _str):
    for chr in _str:
        M_DrawCharacter(cx, cy, chr)
        cx += 8

def M_DrawTransPic(x, y, pic: wad.qpic_t):
    gl_draw.Draw_Pic(x, y, pic)

def M_DrawPic(x, y, pic:wad.qpic_t):
    gl_draw.Draw_Pic(x, y, pic)

def M_DrawTransPicTranslate(x, y, pic, top, bottom):
    gl_draw.Draw_TransPicTranslate(x, y, pic, top, bottom)

def M_DrawTextBox(x, y, width, lines):
    cx = x; cy = y
    p: wad.qpic_t = gl_draw.Draw_CachePic('gfx/box_tl.lmp')
    M_DrawTransPic(cx, cy, p)
    p = gl_draw.Draw_CachePic('gfx/box_ml.lmp')

    for n in range(lines):
        cy += 8
        M_DrawTransPic(cx, cy + 8, p)

    p = gl_draw.Draw_CachePic('gfx/box_bl.lmp')
    M_DrawTransPic(cx, cy + 8, p)

    cx += 8
    while width > 0:
        cy = y
        p = gl_draw.Draw_CachePic('gfx/box_tm.lmp')
        M_DrawTransPic(cx, cy, p)
        p = gl_draw.Draw_CachePic('gfx/box_mm.lmp')

        for n in range(lines):
            cy += 8
            if n == 1:
                p = gl_draw.Draw_CachePic('gfx/box_mm2.lmp')
            M_DrawTransPic(cx, cy, p)
        p = gl_draw.Draw_CachePic(cx, cy + 8, p)
        width -= 2
        cx += 16

    cy = y
    p = gl_draw.Draw_CachePic('gfx/box_tr.lmp')
    M_DrawTransPic(cx, cy, p)
    p = gl_draw.Draw_CachePic('gfx/box_mr.lmp')

    for n in range(lines):
        cy += 8
        M_DrawTransPic(cx, cy, p)

    p = gl_draw.Draw_CachePic('gfx/box_br.lmp')
    M_DrawTransPic(cx, cy + 8, p)


def M_ToggleMenu_f():
    global m_entersound
    global m_state

    m_entersound = True

    if keys.key_dest == keys.keydest_t.key_menu:
        if m_state != m_state_e.m_main:
            M_Menu_Main_f()
            return

        in_sdl.IN_Activate()
        keys.key_dest = keys.keydest_t.key_game
        m_state = m_state_e.m_none
        return

    if keys.key_dest == keys.keydest_t.key_console:
        console.Con_ToggleConsole_f()
    else:
        M_Menu_Main_f()


def M_Menu_Main_f():
    global m_save_demonum
    global m_entersound
    global m_state

    if keys.key_dest != keys.keydest_t.key_menu:
        m_save_demonum = cl_main.cls.demonum
        cl_main.cls.demonum = -1

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_main
    m_entersound = True

def M_Menu_SinglePlayer_f():
    global m_entersound
    global m_state

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_singleplayer
    m_entersound = True

def M_Menu_MultiPlayer_f():
    global m_state, m_entersound

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_multiplayer
    m_entersound = True


def M_Menu_Load_f():
    global m_entersound
    global m_state

    m_entersound = True
    m_state = m_state_e.m_load
    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    M_ScanSaves()

def M_Menu_Save_f():
    global m_entersound
    global m_state

    if not sv_main.sv.active:
        return
    if cl_main.cl.intermission:
        return
    if sv_main.svs.maxclients != 1:
        return

    m_entersound = True
    m_state = m_state_e.m_save

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu

    M_ScanSaves()

def M_Menu_Setup_f():
    global m_entersound
    global m_state
    global setup_myname
    global setup_hostname
    global setup_top, setup_bottom, setup_oldtop, setup_oldbottom

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_setup
    m_entersound = True

    setup_myname   = cvar.Cvar_GetCvar('_cl_name').string
    setup_hostname = cvar.Cvar_GetCvar('hostname').string

    setup_top    = setup_oldtop    = cvar.Cvar_GetCvar('_cl_color').value >> 4
    setup_bottom = setup_oldbottom = cvar.Cvar_GetCvar('_cl_color').value & 15

def M_Menu_Options_f():
    global m_state, m_entersound

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_options
    m_entersound = True

def M_Menu_Keys_f():
    global m_state, m_entersound

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_options
    m_entersound = True

def M_Menu_Help_f():
    global m_state, m_entersound, help_page

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_help
    m_entersound = True
    help_page = 0

def M_Menu_Quit_f():
    global m_state, m_entersound
    global wasInMenus
    global m_quit_prestate
    global msgNumber

    if m_state == m_state_e.m_quit:
        return

    wasInMenus = (keys.key_dest == keys.keydest_t.key_menu)
    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_quit_prestate = m_state
    m_state = m_state_e.m_quit
    m_entersound = True
    msgNumber = randint(7)

def M_Menu_Credits_f():
    raise NotImplementedError

def M_Menu_Video_f():
    vid_menucmdfn()

def M_Video_Draw():
    vid_menudrawfn()

def M_Video_Key(key):
    vid_menukeyfn(key)

def M_Init():

    _cmd.Cmd_AddCommand('togglemenu', M_ToggleMenu_f)

    _cmd.Cmd_AddCommand('menu_main', M_Menu_Main_f)
    _cmd.Cmd_AddCommand('menu_singleplayer', M_Menu_SinglePlayer_f)
    _cmd.Cmd_AddCommand('menu_load', M_Menu_Load_f)
    _cmd.Cmd_AddCommand('menu_save', M_Menu_Save_f)
    _cmd.Cmd_AddCommand('menu_multiplayer', M_Menu_MultiPlayer_f)
    _cmd.Cmd_AddCommand('menu_setup', M_Menu_Setup_f)
    _cmd.Cmd_AddCommand('menu_options', M_Menu_Options_f)
    _cmd.Cmd_AddCommand('menu_keys', M_Menu_Keys_f)
    _cmd.Cmd_AddCommand('menu_video', M_Menu_Video_f)
    _cmd.Cmd_AddCommand('help', M_Menu_Help_f)
    _cmd.Cmd_AddCommand('menu_quit', M_Menu_Quit_f)
    _cmd.Cmd_AddCommand('menu_credits', M_Menu_Credits_f)


def M_Draw():
    global m_recursiveDraw, m_entersound
    if m_state == m_state_e.m_none or keys.key_dest != keys.keydest_t.key_menu:
        return

    if not m_recursiveDraw:
        if gl_screen.scr_con_current:
            gl_draw.Draw_ConsoleBackground()
            snd_dma.S_ExtraUpdate()

        gl_draw.Draw_FadeScreen()

    else:
        m_recursiveDraw = False

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_MENU)

    match m_state:
        case m_state_e.m_none:
            pass
        case m_state_e.m_main:
            M_Main_Draw()
        case m_state_e.m_singleplayer:
            M_SinglePlayer_Draw()
        case m_state_e.m_load:
            M_Load_Draw()
        case m_state_e.m_save:
            M_Save_Draw()
        case m_state_e.m_multiplayer:
            M_MultiPlayer_Draw()
        case m_state_e.m_setup:
            M_Setup_Draw()
        case m_state_e.m_net:
            M_Net_Draw()
        case m_state_e.m_options:
            M_Options_Draw()
        case m_state_e.m_keys:
            M_Keys_Draw()
        case m_state_e.m_video:
            M_Video_Draw()
        case m_state_e.m_help:
            M_Help_Draw()
        case m_state_e.m_quit:
            if not common.fitzmode:
                keys.key_dest = keys.keydest_t.key_console
                host_cmd.Host_Quit_f()
            M_Quit_Draw()
        case m_state_e.m_lanconfig:
            M_LanConfig_Draw()
        case m_state_e.m_gameoptions:
            M_GameOptions_Draw()
        case m_state_e.m_search:
            M_Search_Draw()
        case m_state_e.m_slist:
            M_ServerList_Draw()

    if m_entersound:
        snd_dma.S_LocalSound('misc/menu2.wav')
        m_entersound = False

    snd_dma.S_ExtraUpdate()


def M_Main_Draw():
    p: wad.qpic_t = None
    M_DrawTransPic(16, 4, gl_draw.Draw_CachePic('gfx/qplaque.lmp'))
    p = gl_draw.Draw_CachePic('gfx/ttl_main.lmp')
    M_DrawPic( (320-p.width)/2, 4, p)
    M_DrawTransPic(72, 32, gl_draw.Draw_CachePic('gfx/mainmenu.lmp'))

    f = int(host.realtime * 10) % 6
    M_DrawTransPic (54, 32 + m_main_cursor * 20, gl_draw.Draw_CachePic( f"gfx/menudot{f+1}.lmp"))

def M_Main_Key(k: int):
    global m_entersound, m_state, m_main_cursor
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            in_sdl.IN_Activate()
            keys.key_dest = keys.keydest_t.key_game
            m_state = m_state_e.m_none
            cl_main.cls.demonum = m_save_demonum

            if not common.fitzmode and not cvar.Cvar_GetCvar('cl_startdemos').value:
                pass
            elif cl_main.cls.demonum != -1 and not cl_main.cls.demoplayback and cl_main.cls.state != quakedef.cactive_t.ca_connected:
                cl_main.CL_NextDemo()
        case keys.Key.K_DOWNARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            m_main_cursor += 1
            if m_main_cursor >= MAIN_ITEMS:
                m_main_cursor = 0
        case keys.Key.K_UPARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            m_main_cursor -= 1
            if m_main_cursor < 0:
                m_main_cursor = MAIN_ITEMS - 1
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            m_entersound = True

            match m_main_cursor:
                case 0:
                    M_Menu_SinglePlayer_f()
                case 1:
                    M_Menu_MultiPlayer_f()
                case 2:
                    M_Menu_Options_f()
                case 3:
                    M_Menu_Help_f()
                case 4:
                    M_Menu_Quit_f()

def M_SinglePlayer_Draw():
    p: wad.qpic_t = None
    M_DrawTransPic(16, 4, gl_draw.Draw_CachePic('gfx/qplaque.lmp'))
    p = gl_draw.Draw_CachePic('gfx/ttl_sgl.lmp')
    M_DrawPic((320-p.width)/2, 4, p)
    M_DrawTransPic (72, 32, gl_draw.Draw_CachePic ("gfx/sp_menu.lmp") )

    f = int(host.realtime * 10 ) % 6

    M_DrawTransPic(54, 32, + m_singleplayer_cursor * 20, gl_draw.Draw_CachePic(f'gfx/menudot{f+1}.lmp'))

def M_SinglePlayer_Key(k: int):
    global m_entersound
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_Main_f()
        case keys.Key.K_DOWNARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            m_singleplayer_cursor += 1
            if m_singleplayer_cursor >= SINGLEPLAYER_ITEMS:
                m_singleplayer_cursor = 0
        case keys.Key.K_UPARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            m_singleplayer_cursor -= 1
            if m_singleplayer_cursor < 0:
                m_singleplayer_cursor = SINGLEPLAYER_ITEMS - 1
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            m_entersound = True

            match m_singleplayer_cursor:
                case 0:
                    if sv_main.sv.active:
                        if not gl_screen.SCR_ModalMessage('Are you sure you want to \nstart a new game (y/n)\n', 0.0):
                            return
                    in_sdl.IN_Activate()
                    keys.key_dest = keys.keydest_t.key_game
                    if sv_main.sv.active:
                        _cmd.Cbuf_AddText('disconnect\n')
                    _cmd.Cbuf_AddText('maxplayers 1\n')
                    _cmd.Cbuf_AddText('deathmatch 0\n')
                    _cmd.Cbuf_AddText('coop 0\n')
                    _cmd.Cbuf_AddText('map start\n')
                case 1:
                    M_Menu_Load_f()
                case 2:
                    M_Menu_Save_f()

def M_ScanSaves():
    for i in range(MAX_SAVEGAMES):
        m_filenames[i] = '--- UNUSED SLOT ---'
        loadable[i] = False
        name = f'{common.com_gamedir}/s{i}.sav'

        try:
            with open(name, 'r') as f:
                version = f.readline()
                if version != '5':
                    console.Con_Warning('version of save file not equal 5')
                name = f.readline()
                m_filenames[i] = name
                m_filenames[i].replace('_', ' ')
                loadable[i] = True
        except OSError:
            console.Con_Warning('failed to open/read save file')
            continue


def M_Load_Draw():
    p: wad.qpic_t = gl_draw.Draw_CachePic('gfx/p_load.lmp')
    M_DrawPic((320-p.width)/2, 4, p)

    for i in range(MAX_SAVEGAMES):
        M_Print(16, 32 + 8 * i, m_filenames[i])

    M_DrawCharacter(8, 32 + load_cursor * 8, 12 + int(host.realtime * 4) & 1)

def M_Save_Draw():
    p: wad.qpic_t = gl_draw.Draw_CachePic('gfx/p_save.lmp')
    M_DrawPic( (320-p.width)/2, 4, p)

    for i in range(MAX_SAVEGAMES):
        M_Print(16, 32 + 8*i, m_filenames[i])

    M_DrawCharacter(8, 32 + load_cursor * 8, 12 + int(host.realtime * 4) & 1)


def M_Load_Key(k):
    global m_state, load_cursor
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_SinglePlayer_f()
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            snd_dma.S_LocalSound('misc/menu2.wav')
            if not loadable[load_cursor]:
                return
            m_state = m_state_e.m_none
            keys.key_dest = keys.keydest_t.key_game
            gl_screen.SCR_BeginLoadingPlaque()
            _cmd.Cbuf_AddText(f'load s{load_cursor}')
        case keys.Key.K_UPARROW | keys.Key.K_LEFTARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            load_cursor -= 1
            if load_cursor < 0:
                load_cursor = MAX_SAVEGAMES - 1
        case keys.Key.K_DOWNARROW | keys.Key.K_RIGHTARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            load_cursor += 1
            if load_cursor >= MAX_SAVEGAMES:
                load_cursor = 0

def M_Save_Key(k):
    global m_state, load_cursor
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_SinglePlayer_f()
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            m_state = m_state_e.m_none
            in_sdl.IN_Activate()
            keys.key_dest = keys.keydest_t.key_game
            _cmd.Cbuf_AddText(f'save s{load_cursor}\n')
        case keys.Key.K_UPARROW | keys.Key.K_LEFTARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            load_cursor -= 1
            if load_cursor < 0:
                load_cursor = MAX_SAVEGAMES - 1
        case keys.Key.K_DOWNARROW | keys.Key.K_RIGHTARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            load_cursor += 1
            if load_cursor >= MAX_SAVEGAMES:
                load_cursor = 0


def M_MultiPlayer_Draw():
    p:wad.qpic_t = None

    M_DrawTransPic(16, 4, gl_draw.Draw_CachePic('gfx/qplaque.lmp'))
    p = gl_draw.Draw_CachePic('gfx/p_multi.lmp')
    M_DrawPic((320-p.width)/2, 4, p)
    M_DrawTransPic(72, 32, gl_draw.Draw_CachePic('gfx/mp_menu.lmp'))

    f = int(host.realtime * 10) % 6

    M_DrawTransPic(54, 32 + m_multiplayer_cursor * 20,gl_draw.Draw_CachePic( f"gfx/menudot{f+1}.lmp" ))
    if net_main.tcpipAvailable:
        return

    M_PrintWhite ((320/2) - ((27*8)/2), 148, "No Communications Available")

def M_MultiPlayer_Key(k):
    global m_multiplayer_cursor, m_entersound
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_Main_f()
        case keys.Key.K_DOWNARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            m_multiplayer_cursor += 1
            if m_multiplayer_cursor >= MULTIPLAYER_ITEMS:
                m_multiplayer_cursor = 0
        case keys.Key.K_UPARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            m_multiplayer_cursor -= 1
            if m_multiplayer_cursor < 0:
                m_multiplayer_cursor = MULTIPLAYER_ITEMS - 1
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            m_entersound = True
            match m_multiplayer_cursor:
                case 0:
                    if net_main.tcpipAvailable:
                        M_Menu_Net_f()
                case 1:
                    if net_main.tcpipAvailable:
                        M_Menu_Net_f()
                case 2:
                    M_Menu_Setup_f()

def M_Setup_Draw():
    p: wad.qpic_t = None

    M_DrawTransPic (16, 4, gl_draw.Draw_CachePic ("gfx/qplaque.lmp") )
    p = gl_draw.Draw_CachePic ("gfx/p_multi.lmp")
    M_DrawPic ( (320-p.width)/2, 4, p)

    M_Print (64, 40, "Hostname")
    M_DrawTextBox (160, 32, 16, 1)
    M_Print (168, 40, setup_hostname)

    M_Print (64, 56, "Your name")
    M_DrawTextBox (160, 48, 16, 1)
    M_Print (168, 56, setup_myname)

    M_Print (64, 80, "Shirt color")
    M_Print (64, 104, "Pants color")

    M_DrawTextBox (64, 140-8, 14, 1)
    M_Print (72, 140, "Accept Changes")

    p = gl_draw.Draw_CachePic ("gfx/bigbox.lmp")
    M_DrawTransPic (160, 64, p)
    p = gl_draw.Draw_CachePic ("gfx/menuplyr.lmp")
    M_DrawTransPicTranslate (172, 72, p, setup_top, setup_bottom)

    M_DrawCharacter (56, setup_cursor_table [setup_cursor], 12+(int(host.realtime*4)&1))

    if setup_cursor == 0:
        M_DrawCharacter (168 + 8*len(setup_hostname), setup_cursor_table [setup_cursor], 10+(int(host.realtime*4)&1))

    if setup_cursor == 1:
        M_DrawCharacter (168 + 8*len(setup_myname), setup_cursor_table [setup_cursor], 10+(int(host.realtime*4)&1))


def M_Setup_Key(k):
    global setup_cursor, setup_bottom, setup_top, m_entersound, setup_myname, setup_hostname
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_MultiPlayer_f()
        case keys.Key.K_UPARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            setup_cursor -= 1
            if setup_cursor < 0:
                setup_cursor = NUM_SETUP_CMDS - 1
        case keys.Key.K_DOWNARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            setup_cursor += 1
            if setup_cursor >= NUM_SETUP_CMDS:
                setup_cursor = 0
        case keys.Key.K_LEFTARROW:
            if setup_cursor < 2:
                return
            snd_dma.S_LocalSound('misc/menu3.wav')
            if setup_cursor == 2:
                setup_top = setup_top - 1
            if setup_cursor == 3:
                setup_bottom = setup_bottom - 1
        case keys.Key.K_RIGHTARROW:
            if setup_cursor < 2:
                return
            snd_dma.S_LocalSound('misc/menu3.wav')
            if setup_cursor == 2:
                setup_top += 1
            if setup_cursor == 3:
                setup_bottom += 1
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            if setup_cursor == 0 or setup_cursor == 1:
                return
            if setup_cursor == 2 or setup_cursor == 3:
                snd_dma.S_LocalSound('misc/menu3.wav')
                if setup_cursor == 2:
                    setup_top += 1
                if setup_cursor == 3:
                    setup_bottom += 1
            if setup_cursor == 4:
                if cvar.Cvar_GetCvar('_cl_name').string == setup_myname:
                    _cmd.Cbuf_AddText(f'name "{setup_myname}"\n')
                if cvar.Cvar_GetCvar('hostname').string == setup_hostname:
                    cvar.Cvar_Set('hostname', setup_hostname)
                if setup_top != setup_oldtop or setup_bottom != setup_oldbottom:
                    _cmd.Cbuf_AddText(f'color {setup_top} {setup_bottom}\n')
                m_entersound = True
                M_Menu_MultiPlayer_f()
        case keys.Key.K_BACKSPACE:
            if setup_cursor == 0:
                if len(setup_hostname):
                    setup_hostname = setup_hostname[:-1]
            if setup_cursor == 1:
                if len(setup_myname):
                    setup_myname = setup_myname[:-1]

    if setup_top > 13:
        setup_top = 0
    if setup_top < 0:
        setup_top = 13
    if setup_bottom > 13:
        setup_bottom = 0
    if setup_bottom < 0:
        setup_bottom = 13

def M_Setup_Char(k):
    global setup_hostname, setup_myname

    l: int = 0
    match setup_cursor:
        case 0:
            l = len(setup_hostname)
            if l < 15:
                setup_hostname = setup_hostname + k
        case 1:
            l = len(setup_myname)
            if l < 15:
                setup_myname = setup_myname + k


def M_Setup_TextEntry():
    return setup_cursor in [0, 1]


def M_Menu_Net_f():
    global m_state, m_entersound, m_net_cursor, m_net_items

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_net
    m_entersound = True
    m_net_items = 2

    if m_net_cursor >= m_net_items:
        m_net_cursor = 0

    m_net_cursor -= 1
    M_Net_Key(keys.Key.K_DOWNARROW)

def M_Net_Draw():
    p:wad.qpic_t = None

    M_DrawTransPic( 16, 4, gl_draw.Draw_CachePic('gfx/qplaque.lmp'))
    p = gl_draw.Draw_CachePic('gfx/p_multi.lmp')
    M_DrawPic( (320-p.width)/2, 4, p)

    f = 32

    if False:
        p = gl_draw.Draw_CachePic ("gfx/netmen3.lmp")
    else:
        p = gl_draw.Draw_CachePic ("gfx/dim_ipx.lmp")
    M_DrawTransPic(72, f, p)

    f += 19
    if net_main.tcpipAvailable:
        p = gl_draw.Draw_CachePic ("gfx/netmen4.lmp")
    else:
        p = gl_draw.Draw_CachePic ("gfx/dim_tcp.lmp")
    M_DrawTransPic(72, f, p)

    f = (320-26*8)/2

    M_DrawTextBox(f, 96, 24, 4)

    f += 8
    M_Print (f, 104, net_helpMessage[m_net_cursor*4+0])
    M_Print (f, 112, net_helpMessage[m_net_cursor*4+1])
    M_Print (f, 120, net_helpMessage[m_net_cursor*4+2])
    M_Print (f, 128, net_helpMessage[m_net_cursor*4+3])

    f = int(host.realtime * 10) % 6
    M_DrawTransPic(54, 32 + m_net_cursor * 20, gl_draw.Draw_CachePic( f"gfx/menudot{f+1}.lmp"))


def M_Net_Key(k):
    global m_net_cursor, m_entersound
    again = True

    while again:
        match k:
            case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
                M_Menu_MultiPlayer_f()
            case keys.Key.K_DOWNARROW:
                snd_dma.S_LocalSound('misc/menu1.wav')
                m_net_cursor += 1
                if m_net_cursor >= m_net_items:
                    m_net_cursor = 0
            case keys.Key.K_UPARROW:
                snd_dma.S_LocalSound('misc/menu1.wav')
                m_net_cursor -= 1
                if m_net_cursor < 0:
                    m_net_cursor = m_net_items - 1
            case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
                m_entersound = True
                M_Menu_LanConfig_f()

        if m_net_cursor == 1 and not net_main.tcpipAvailable:
            pass
        else:
            again = False


def M_AdjustSliders(dir):
    f = 0.0
    l = 0.0

    snd_dma.S_LocalSound('misc/menu3.wav')

    match options_cursor:
        case opt_items_e.OPT_SCALE:
            l = ((gl_vidsdl._vid.width + 31) / 32) / 10.0
            f = cvar.Cvar_GetCvar('scr_conscale').value + dir * .1
            if f < 1:
                f = 1
            elif f > l:
                f = l
            cvar.Cvar_SetValue('scr_conscale', f)
            cvar.Cvar_SetValue('scr_menuscale', f)
            cvar.Cvar_SetValue('scr_sbarscale', f)
        case opt_items_e.OPT_SCRSIZE:
            f = cvar.Cvar_GetCvar('scr_viewsize').value + dir * 10
            if f > 120:
                f = 120
            elif f < 30:
                f = 30
            cvar.Cvar_SetValue('viewsize', f)
        case opt_items_e.OPT_GAMMA:
            f = cvar.Cvar_GetCvar('vid_gamma').value - dir * 0.05
            if f < 0.5:
                f = 0.5
            elif f > 1:
                f = 1
            cvar.Cvar_SetValue('gamma', f)
        case opt_items_e.OPT_CONTRAST:
            f = cvar.Cvar_GetCvar('vid_contrast').value + dir * 0.1
            if f < 1:
                f = 1
            elif f > 2:
                f = 2
            cvar.Cvar_SetValue('contrast', f)
        case opt_items_e.OPT_MOUSESPEED:
            f = cvar.Cvar_GetCvar('sensitivity').value + dir * 0.5
            if f > 11:
                f = 11
            elif f < 1:
                f = 1
            cvar.Cvar_SetValue('sensitivity', f)
        case opt_items_e.OPT_SBALPHA:
            f = cvar.Cvar_GetCvar('scr_sbaralpha').value - dir * 0.05
            if f < 0:
                f = 0
            elif f > 1:
                f = 1
            cvar.Cvar_SetValue('scr_sbaralpha', f)
        case opt_items_e.OPT_MUSICVOL:
            f = cvar.Cvar_GetCvar('bgmvolume').value + dir * 0.1
            if f < 0:
                f = 0
            elif f > 1:
                f = 1
            cvar.Cvar_SetValue('bgmvolume', f)
        case opt_items_e.OPT_MUSICEXT:
            f = cvar.Cvar_GetCvar('bgm_extmusic').value
            cvar.Cvar_Set('bgm_extmusic', "0" if f else "1")
        case opt_items_e.OPT_SNDVOL:
            f = cvar.Cvar_GetCvar('sfxvolume').value + dir * 0.1
            if f < 0:
                f = 0
            elif f > 1:
                f = 1
            cvar.Cvar_SetValue('volume', f)
        case opt_items_e.OPT_ALWAYRUN:
            if cvar.Cvar_GetCvar('cl_alwaysrun').value:
                curr_alwaysrun = always_run_e.ALWAYSRUN_QUAKESPASM
            elif cvar.Cvar_GetCvar('cl_forwardspeed').value > 200:
                curr_alwaysrun = always_run_e.ALWAYSRUN_VANILLA
            else:
                curr_alwaysrun = always_run_e.ALWAYSRUN_OFF

            target_alwaysrun = (always_run_e.ALWAYSRUN_ITEMS + curr_alwaysrun + dir) % always_run_e.ALWAYSRUN_ITEMS

            if target_alwaysrun == always_run_e.ALWAYSRUN_VANILLA:
                cvar.Cvar_SetValue('cl_alwaysrun', 0)
                cvar.Cvar_SetValue('cl_forwardspeed', 400)
                cvar.Cvar_SetValue('cl_backspeed', 400)
            elif target_alwaysrun == always_run_e.ALWAYSRUN_QUAKESPASM:
                cvar.Cvar_SetValue('cl_alwaysrun', 1)
                cvar.Cvar_SetValue('cl_forwardspeed', 200)
                cvar.Cvar_SetValue('cl_backspeed', 200)
            else:
                cvar.Cvar_SetValue('cl_alwaysrun', 0)
                cvar.Cvar_SetValue('cl_forwardspeed', 200)
                cvar.Cvar_SetValue('cl_backspeed', 200)
        case opt_items_e.OPT_INVMOUSE:
            cvar.Cvar_SetValue('m_pitch', -cvar.Cvar_GetCvar('m_pitch').value)
        case opt_items_e.OPT_ALWAYSMLOOK:
            if cl_input.in_mlook.state & 1:
                _cmd.Cbuf_AddText('-mlook')
            else:
                _cmd.Cbuf_AddText('+mlook')
        case opt_items_e.OPT_LOOKSPRING:
            cvar.Cvar_Set('lookspring', '0' if cvar.Cvar_GetCvar('lookspring').value else '1')
        case opt_items_e.OPT_LOOKSTRAFE:
            cvar.Cvar_Set('lookspring', '0' if cvar.Cvar_GetCvar('lookspring').value else '1')


def M_DrawSlider(x:int, y:int, rng:float, value:float, format:str):
    if rng < 0:
        rng = 0
    elif rng > 1:
        rng = 1

    M_AdjustSliders(x - 8, y, 128)
    for i in range(SLIDER_RANGE):
        M_DrawCharacter(x + i * 8, y, 129)
    M_DrawCharacter(x + i * 8, y, 130)
    M_DrawCharacter(x + (SLIDER_RANGE-1)*8 * range, y, 131)
    string = format % value
    M_Print(x + (SLIDER_RANGE + 1) * 8, y, string)

def M_DrawCheckbox(x, y, on):
    if on:
        M_Print(x, y, 'on')
    else:
        M_Print(x, y, 'off')

def M_Options_Draw():
    M_DrawTransPic (16, 4, gl_draw.Draw_CachePic ("gfx/qplaque.lmp") )
    p:wad.qpic_t = gl_draw.Draw_CachePic ("gfx/p_option.lmp")
    M_DrawPic ( (320-p.width)/2, 4, p)

    M_Print (16, 32,            "              Controls")
    M_Print (16, 32 + 8*opt_items_e.OPT_CONSOLE,    "          Goto console")
    M_Print (16, 32 + 8*opt_items_e.OPT_DEFAULTS,   "          Reset config")

    M_Print (16, 32 + 8*opt_items_e.OPT_SCALE,      "                 Scale")
    l = (vid.width / 320.0) - 1
    r = (cvar.Cvar_GetCvar('scr_conscale').value - 1) / l if l > 0 else 0
    M_DrawSlider (220, 32 + 8*opt_items_e.OPT_SCALE, r, cvar.Cvar_GetCvar('scr_conscale').value, "%.1f")

    M_Print (16, 32 + 8*opt_items_e.OPT_SCRSIZE,    "           Screen size")
    r = (cvar.Cvar_GetCvar('scr_viewsize').value - 30) / (120 - 30)
    M_DrawSlider (220, 32 + 8*opt_items_e.OPT_SCRSIZE, r, cvar.Cvar_GetCvar('scr_viewsize').value, "%.0f")

    M_Print (16, 32 + 8*opt_items_e.OPT_GAMMA,      "            Brightness")
    r = (1.0 - cvar.Cvar_GetCvar('vid_gamma').value) / 0.5
    M_DrawSlider (220, 32 + 8*opt_items_e.OPT_GAMMA, r, cvar.Cvar_GetCvar('vid_gamma').value, "%.2f")

    M_Print (16, 32 + 8*opt_items_e.OPT_CONTRAST,   "              Contrast")
    r = cvar.Cvar_GetCvar('vid_contrast').value - 1.0
    M_DrawSlider (220, 32 + 8*opt_items_e.OPT_CONTRAST, r, cvar.Cvar_GetCvar('vid_contrast').value, "%.1f")

    M_Print (16, 32 + 8*opt_items_e.OPT_MOUSESPEED, "           Mouse Speed")
    r = (cvar.Cvar_GetCvar('sensitivity').value - 1)/10
    M_DrawSlider (220, 32 + 8*opt_items_e.OPT_MOUSESPEED, r, cvar.Cvar_GetCvar('sensitivity').value, "%.1f")

    M_Print (16, 32 + 8*opt_items_e.OPT_SBALPHA,    "       Statusbar alpha")
    r = (1.0 - cvar.Cvar_GetCvar('scr_sbaralpha').value)
    M_DrawSlider (220, 32 + 8*opt_items_e.OPT_SBALPHA, r, cvar.Cvar_GetCvar('scr_sbaralpha').value, "%.2f")

    M_Print (16, 32 + 8*opt_items_e.OPT_SNDVOL,     "          Sound Volume")
    r = cvar.Cvar_GetCvar('sfxvolume').value
    M_DrawSlider (220, 32 + 8*opt_items_e.OPT_SNDVOL, r, cvar.Cvar_GetCvar('sfxvolume').value, "%.1f")

    M_Print (16, 32 + 8*opt_items_e.OPT_MUSICVOL,   "          Music Volume")
    r = cvar.Cvar_GetCvar('bgmvolume').value
    M_DrawSlider (220, 32 + 8*opt_items_e.OPT_MUSICVOL, r, cvar.Cvar_GetCvar('bgmvolume').value, "%.1f")

    M_Print (16, 32 + 8*opt_items_e.OPT_MUSICEXT,   "        External Music")
    M_DrawCheckbox (220, 32 + 8*opt_items_e.OPT_MUSICEXT, cvar.Cvar_GetCvar('bgm_extmusic').value)

    M_Print (16, 32 + 8*opt_items_e.OPT_ALWAYRUN,   "            Always Run")
    if (cvar.Cvar_GetCvar('cl_alwaysrun').value):
        M_Print (220, 32 + 8*opt_items_e.OPT_ALWAYRUN, "quakespasm")
    elif (cvar.Cvar_GetCvar('cl_forwardspeed').value > 200.0):
        M_Print (220, 32 + 8*opt_items_e.OPT_ALWAYRUN, "vanilla")
    else:
        M_Print (220, 32 + 8*opt_items_e.OPT_ALWAYRUN, "off")


    M_Print (16, 32 + 8*opt_items_e.OPT_INVMOUSE,   "          Invert Mouse")
    M_DrawCheckbox (220, 32 + 8*opt_items_e.OPT_INVMOUSE, cvar.Cvar_GetCvar('m_pitch').value < 0)

    M_Print (16, 32 + 8*opt_items_e.OPT_ALWAYSMLOOK,    "            Mouse Look")
    M_DrawCheckbox (220, 32 + 8*opt_items_e.OPT_ALWAYSMLOOK, cvar.Cvar_GetCvar('in_mlook').state & 1)

    M_Print (16, 32 + 8*opt_items_e.OPT_LOOKSPRING, "            Lookspring")
    M_DrawCheckbox (220, 32 + 8*opt_items_e.OPT_LOOKSPRING, cvar.Cvar_GetCvar('lookspring').value)

    M_Print (16, 32 + 8*opt_items_e.OPT_LOOKSTRAFE, "            Lookstrafe")
    M_DrawCheckbox (220, 32 + 8*opt_items_e.OPT_LOOKSTRAFE, cvar.Cvar_GetCvar('lookstrafe').value)

    if (vid_menudrawfn):
        M_Print (16, 32 + 8*opt_items_e.OPT_VIDEO,  "         Video Options")

    M_DrawCharacter(200, 32 + options_cursor * 8, 12 + ( int(host.realtime * 4) & 1))

def M_Options_Key(k):
    global m_entersound, m_state, options_cursor
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_Main_f()
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            m_entersound = True
            match options_cursor:
                case opt_items_e.OPT_CUSTOMIZE:
                    M_Menu_Keys_f()
                case opt_items_e.OPT_CONSOLE:
                    m_state = m_state_e.m_none
                    console.Con_ToggleConsole_f()
                case opt_items_e.OPT_DEFAULTS:
                    if gl_screen.SCR_ModalMessage('This will reset all controls\nand s tored cvars. Continue (y/n)\n', 15.0):
                        _cmd.Cbuf_AddText('resetcfg\n')
                        _cmd.Cbuf_AddText('exec default.cfg\n')
                case opt_items_e.OPT_VIDEO:
                    M_Menu_Video_f()
                case _:
                    M_AdjustSliders(1)
        case keys.Key.K_UPARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            options_cursor -= 1
            if options_cursor < 0:
                options_cursor = opt_items_e.OPTIONS_ITEMS - 1

        case keys.Key.K_DOWNARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            options_cursor += 1
            if options_cursor >= opt_items_e.OPTIONS_ITEMS:
                options_cursor = 0

        case keys.Key.K_LEFTARROW:
            M_AdjustSliders(-1)
        case keys.Key.K_RIGHTARROW:
            M_AdjustSliders(1)

    if options_cursor == opt_items_e.OPTIONS_ITEMS - 1 and vid_menudrawfn is None:
        if k == keys.Key.K_UPARROW:
            options_cursor = opt_items_e.OPTIONS_ITEMS - 2
        else:
            options_cursor = 0


def M_FindKeysForCommand(command: str, threekeys: list[int]):
    threekeys[0] = threekeys[1] = threekeys[2] = -1
    l = len(command)
    count = 0

    for j in range(keys.MAX_KEYS):
        b = keys.keybindings[j]

        if not b:
            continue

        if b == command:
            threekeys[count] = j
            count += 1
            if count == 3:
                break

def M_UnbindCommand(command: str):
    for j in keys.MAX_KEYS:
        b = keys.keybindings[j]
        if not b:
            continue
        if b == command:
            keys.Key_SetBinding(j, None)


def M_Keys_Draw():
    _keys: list[int] = [0, 0, 0]
    p:wad.qpic_t = gl_draw.Draw_CachePic('gfx/ttl_cstm.lmp')
    M_DrawPic((320-p.width)/2, 4, p)

    if bind_grab:
        M_Print (12, 32, "Press a key or button for this action")
    else:
        M_Print (18, 32, "Enter to change, backspace to clear")

    for i in range(NUMCOMMANDS):
        y = 48 + 8 * i

        M_Print (16, y, bindnames[i][1])

        M_FindKeysForCommand(bindnames[i], _keys)

        if keys[0] == -1:
            M_Print(140, y, '???')
        else:
            name = keys.Key_KeynumToString(_keys[0])
            M_Print (140, y, name)
            x = len(name) * 8
            if _keys[1] != -1:
                name = keys.Key_KeynumToString(_keys[1])
                M_Print (140 + x + 8, y, "or");
                M_Print (140 + x + 32, y, name)
                x = x + 32 + len(name) * 8
                if _keys[2] != -1:
                    M_Print (140 + x + 8, y, "or");
                    M_Print (140 + x + 32, y, keys.Key_KeynumToString (_keys[2]))

    if bind_grab:
        M_DrawCharacter (130, 48 + keys_cursor*8, '=')
    else:
        M_DrawCharacter (130, 48 + keys_cursor*8, 12+(int(host.realtime*4)&1))


def M_Keys_Key(k):
    global keys_cursor, bind_grab

    cmd: str = ''
    _keys: list[int] = [0, 0, 0]

    if bind_grab:
        snd_dma.S_LocalSound('misc/menu1.wav')
        if ( k != keys.Key.K_ESCAPE ) and ( k != '`'):
            cmd = f'bind "{keys.Key_KeynumToString(k)}" "{bindnames[keys_cursor][0]}\n'
            _cmd.Cbuf_AddText(cmd)

        bind_grab = False
        in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
        return

    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_Options_f();
        case keys.Key.K_LEFTARROW | keys.Key.K_UPARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            keys_cursor -= 1
            if keys_cursor < 0:
                keys_cursor = NUMCOMMANDS - 1
        case keys.Key.K_DOWNARROW | keys.Key.K_RIGHTARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            keys_cursor += 1
            if keys_cursor >= NUMCOMMANDS:
                keys_cursor = 0

        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            M_FindKeysForCommand( bindnames[keys_cursor][0], _keys)
            snd_dma.S_LocalSound('misc/menu2.wav')
            if _keys[2] != -1:
                M_UnbindCommand( bindnames[keys_cursor][0])
            bind_grab = True
            in_sdl.IN_Activate()
        case keys.Key.K_BACKSPACE | keys.Key.K_DEL:
            snd_dma.S_LocalSound('misc/menu2.wav')
            M_UnbindCommand(bindnames[keys_cursor][0])


def M_Help_Draw():
    M_DrawPic(0, 0, gl_draw.Draw_CachePic ( f"gfx/help{help_page}.lmp"))

def M_Help_Key(k):
    global m_entersound
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_Main_f()
        case keys.Key.K_UPARROW | keys.Key.K_RIGHTARROW:
            m_entersound = True
            help_page += 1
            if help_page >= NUM_HELP_PAGES:
                help_page = 0
        case keys.Key.K_DOWNARROW | keys.Key.K_LEFTARROW:
            m_entersound = True
            help_page -= 1
            if help_page < 0:
                help_page = NUM_HELP_PAGES - 1


def M_Quit_Key(k):
    global m_state, m_entersound

    if k == keys.Key.K_ESCAPE:
        if wasInMenus:
            m_state = m_quit_prestate
            m_entersound = True
        else:
            in_sdl.IN_Activate()
            keys.key_dest = keys.keydest_t.key_game
            m_state = m_state_e.m_none


def M_Quit_Char(k):
    global m_state, m_entersound

    k = chr(k & 0xff)
    match k:
        case _ if k in ['n', 'N']:
            if wasInMenus:
                m_state = m_quit_prestate
                m_entersound = True
            else:
                in_sdl.IN_Activate()
                keys.key_dest = keys.keydest_t.key_game
                m_state = m_state_e.m_none
        case _ if k in ['y', 'Y']:
            in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
            keys.key_dest = keys.keydest_t.key_console
            host_cmd.Host_Quit_f()


def M_Quit_TextEntry():
    return True

def M_Quit_Draw():
    global m_state, m_recursiveDraw
    msg1 = 'QuakeSpasm.py ' + quakedef.QUAKESPASM_VER_STRING
    msg2 = 'by Ozkan Sezer,Eric Wasylishen,Mr.HolyShit,others'
    msg3 = 'Preses y to quit'

    if wasInMenus:
        m_state = m_quit_prestate
        m_recursiveDraw = True
        M_Draw()
        m_state = m_state_e.m_quit

    boxlen = max( (  len(msg1), len(msg2), len(msg3) ) )
    M_DrawTextBox   (160-4*(boxlen+2), 76, boxlen, 4);
    M_Print         (160-4*(len(msg1)-1), 88, msg1);
    M_Print         (160-4*(len(msg2)-1), 96, msg2);
    M_PrintWhite    (160-4*(len(msg3)-1), 104, msg3);



def M_Keydown(key):
    match m_state:
        case m_state_e.m_none:
            pass
        case m_state_e.m_main:
            M_Main_Key (key)
        case m_state_e.m_singleplayer:
            M_SinglePlayer_Key (key)
        case m_state_e.m_load:
            M_Load_Key (key)
        case m_state_e.m_save:
            M_Save_Key (key)
        case m_state_e.m_multiplayer:
            M_MultiPlayer_Key (key)
        case m_state_e.m_setup:
            M_Setup_Key (key)
        case m_state_e.m_net:
            M_Net_Key (key)
        case m_state_e.m_options:
            M_Options_Key (key)
        case m_state_e.m_keys:
            M_Keys_Key (key)
        case m_state_e.m_video:
            M_Video_Key (key)
        case m_state_e.m_help:
            M_Help_Key (key)
        case m_state_e.m_quit:
            M_Quit_Key (key)
        case m_state_e.m_lanconfig:
            M_LanConfig_Key (key)
        case m_state_e.m_gameoptions:
            M_GameOptions_Key (key)
        case m_state_e.m_search:
            M_Search_Key (key)
        case m_state_e.m_slist:
            M_ServerList_Key (key)


def M_Charinput(key):
    match m_state:
        case m_state_e.m_setup:
            M_Setup_Char(key)
        case m_state_e.m_quit:
            M_Quit_Char(key)
        case m_state_e.m_lanconfig:
            M_LanConfig_Char(key)

def M_TextEntry() -> bool:
    match m_state:
        case m_state_e.m_setup:
            return M_Setup_TextEntry()
        case m_state_e.m_quit:
            return M_Quit_TextEntry()
        case m_state_e.m_lanconfig:
            return M_LanConfig_TextEntry()

def M_ConfigureNetSubsystem():
    _cmd.Cbuf_AddText('stopdemo\n')

    if TCPIPConfig:
        net_main.net_hostport = lanConfig_port

def M_Menu_LanConfig_f():
    global m_state, m_entersound, lanConfig_cursor, m_return_onerror, m_return_reason
    global lanConfig_port, lanConfig_portname
    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_lanconfig
    m_entersound = True

    if lanConfig_cursor == -1:
        if JoiningGame() and TCPIPConfig():
            lanConfig_cursor = 2
        else:
            lanConfig_cursor = 1

    if StartingGame() and lanConfig_cursor == 2:
        lanConfig_cursor = 1

    lanConfig_port = net_main.DEFAULTnet_hostport
    lanConfig_portname = str(lanConfig_port)

    m_return_onerror = False
    m_return_reason = ''

def M_LanConfig_Draw():
    basex: int = 0
    M_DrawTransPic(16, 4, gl_draw.Draw_CachePic('gfx/qplaque.lmp'))
    p:wad.qpic_t = gl_draw.Draw_CachePic('gfx/p_multi.lmp')
    basex = ( 320 - p.width ) / 2
    M_DrawPic(basex, 4, p)

    basex = 72

    if StartingGame():
        startJoin = 'New Game'
    else:
        startJoin = 'Join Game'

    protocol = 'TCP/IP'

    M_Print(basex, 32, f'{startJoin} - {protocol}')
    basex += 8

    M_Print(basex, 52, 'Address:')
    M_Print(basex + 9 * 8, 52, net_main.my_tcpip_address)

    M_Print(basex, lanConfig_cursor_table[0], 'Port')
    M_DrawTextBox(basex + 8 * 8, lanConfig_cursor_table[0] - 8, 6, 1)
    M_Print(basex + 9 * 8, lanConfig_cursor_table[0], lanConfig_portname)

    if JoiningGame():
        M_Print(basex, lanConfig_cursor_table[1], 'Searching for local games...')
        M_Print(basex, 108, 'Join game at:')
        M_DrawTextBox(basex+8, lanConfig_cursor_table[2]-8, 22, 1)
        M_Print(basex+16, lanConfig_cursor_table[2], lanConfig_joinname)
    else:
        M_DrawTextBox(basex, lanConfig_cursor_table[1]-8, 2, 1)
        M_Print(basex + 8, lanConfig_cursor_table[1], 'OK')

    M_DrawCharacter(basex-8, lanConfig_cursor_table [lanConfig_cursor], 12+(int(host.realtime*4)&1))

    if lanConfig_cursor == 0:
        M_DrawCharacter (basex+9*8 + 8*len(lanConfig_portname), lanConfig_cursor_table [0], 10+(int(host.realtime*4)&1))

    if lanConfig_cursor == 2:
        M_DrawCharacter (basex+16*8 + 8*len(lanConfig_joinname), lanConfig_cursor_table [2], 10+(int(host.realtime*4)&1))

    if m_return_reason:
        M_PrintWhite(basex, 148, m_return_reason)

def M_LanConfig_Key(k):
    global lanConfig_cursor, m_entersound, m_return_state, m_state
    global m_return_onerror, lanConfig_port, lanConfig_portname, lanConfig_joinname
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_Net_f()
        case keys.Key.K_UPARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            lanConfig_cursor -= 1
            if lanConfig_cursor < 0:
                lanConfig_cursor = NUM_LANCONFIG_CMDS - 1
        case keys.Key.K_DOWNARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            lanConfig_cursor += 1
            if lanConfig_cursor >= NUM_LANCONFIG_CMDS:
                lanConfig_cursor = 0
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            if lanConfig_cursor != 0:
                m_entersound = True

                M_ConfigureNetSubsystem()

                if lanConfig_cursor == 1:
                    if StartingGame():
                        M_Menu_GameOptions_f()
                    else:
                        M_Menu_Search_f()
                elif lanConfig_cursor == 2:
                    m_return_state = m_state
                    m_return_onerror = True
                    in_sdl.IN_Activate()
                    keys.key_dest = keys.keydest_t.key_game
                    m_state = m_state_e.m_none
                    _cmd.Cbuf_AddText(f'connect "{lanConfig_joinname}"\n')
        case keys.Key.K_BACKSPACE:
            if lanConfig_cursor == 0:
                if lanConfig_portname:
                    lanConfig_portname = lanConfig_portname[:-1]
            if lanConfig_cursor == 2:
                if lanConfig_joinname:
                    lanConfig_joinname = lanConfig_joinname[:-1]

    if StartingGame() and lanConfig_cursor == 2:
        if k == keys.Key.K_UPARROW:
            lanConfig_cursor = 1
        else:
            lanConfig_cursor = 0

    l = int(lanConfig_portname)
    if l > 65535:
        l = lanConfig_port
    else:
        lanConfig_port = l
    lanConfig_portname = str(lanConfig_port)

def M_LanConfig_Char(k):
    global lanConfig_portname, lanConfig_joinname
    match lanConfig_cursor:
        case 0:
            if k < '0' or k > '9':
                return
            l = len(lanConfig_portname)
            if l < 5:
                lanConfig_portname = lanConfig_portname + k
        case 2:
            l = len(lanConfig_joinname)
            if l < 21:
                lanConfig_joinname = lanConfig_joinname + k

def M_LanConfig_TextEntry() -> bool:
    return lanConfig_cursor == 0 or lanConfig_cursor == 2

def M_Menu_GameOptions_f():
    global m_state, m_entersound

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_gameoptions
    m_entersound = True

    if maxplayers == 0:
        maxplayers = sv_main.svs.maxclients
    if maxplayers < 2:
        maxplayers = sv_main.svs.maxclientslimit


def M_GameOptions_Draw():
    global m_serverInfoMessage

    M_DrawTransPic (16, 4, gl_draw.Draw_CachePic ("gfx/qplaque.lmp") )
    p = gl_draw.Draw_CachePic ("gfx/p_multi.lmp")
    M_DrawPic ( (320-p.width)/2, 4, p)

    M_DrawTextBox (152, 32, 10, 1)
    M_Print (160, 40, "begin game")

    M_Print (0, 56, "      Max players")
    M_Print (160, 56, f"{maxplayers}" )

    M_Print (0, 64, "        Game Type")
    if cvar.Cvar_GetCvar('coop').value:
        M_Print (160, 64, "Cooperative")
    else:
        M_Print (160, 64, "Deathmatch")

    M_Print (0, 72, "        Teamplay")

    msg = 'Off'
    if common.rogue:
        match int(cvar.Cvar_GetCvar('teamplay').value):
            case 1: msg = 'No Friendly Fire'
            case 2: msg = 'Friendly Fire'
            case 3: msg = 'Tag'
            case 4: msg = 'Capture the Flag'
            case 5: msg = 'One Flag CTF'
            case 5: msg = 'Three Team CTF'
        M_Print(160, 72, msg)
    else:
        match int(cvar.Cvar_GetCvar('teamplay').value):
            case 1: msg = 'No Friendly Fire'
            case 2: msg = 'Friendly Fire'
        M_Print(160, 72, msg)

        skill = int(cvar.Cvar_GetCvar('skill').value)

        M_Print (0, 80, "            Skill")
        if (skill == 0):
            M_Print (160, 80, "Easy difficulty")
        elif (skill == 1):
            M_Print (160, 80, "Normal difficulty")
        elif (skill.value == 2):
            M_Print (160, 80, "Hard difficulty")
        else:
            M_Print (160, 80, "Nightmare difficulty")

        M_Print (0, 88, "       Frag Limit")

        fraglimit = int(cvar.Cvar_GetCvar('fraglimit').value)
        if (fraglimit == 0):
            M_Print (160, 88, "none")
        else:
            M_Print (160, 88, f"{fraglimit} frags")

        timelimit = int(cvar.Cvar_GetCvar('timelimit').value)
        M_Print (0, 96, "       Time Limit")
        if (timelimit == 0):
            M_Print (160, 96, "none")
        else:
            M_Print (160, 96, f"{timelimit} minutes", timelimit)

        M_Print (0, 112, "         Episode")
        if (common.hipnotic):
            M_Print (160, 112, hipnoticepisodes[startepisode].description)
        elif (common.rogue):
            M_Print (160, 112, rogueepisodes[startepisode].description)
        else:
            M_Print (160, 112, episodes[startepisode].description)

        M_Print (0, 120, "           Level")
        if (common.hipnotic):
            M_Print (160, 120, hipnoticlevels[hipnoticepisodes[startepisode].firstLevel + startlevel].description)
            M_Print (160, 128, hipnoticlevels[hipnoticepisodes[startepisode].firstLevel + startlevel].name)
        elif (common.rogue):
            M_Print (160, 120, roguelevels[rogueepisodes[startepisode].firstLevel + startlevel].description)
            M_Print (160, 128, roguelevels[rogueepisodes[startepisode].firstLevel + startlevel].name)
        else:
            M_Print (160, 120, levels[episodes[startepisode].firstLevel + startlevel].description)
            M_Print (160, 128, levels[episodes[startepisode].firstLevel + startlevel].name)

        M_DrawCharacter(144, gameoptions_cursor_table[gameoptions_cursor], 12+(int(host.realtime*4)&1))

        if m_serverInfoMessage:
            if host.realtime - m_serverInfoMessageTime < 5.0:
                x = ( 320 - 26 * 8) / 2
                M_DrawTextBox(x, 138, 24, 4)
                x += 8
                M_Print (x, 146, "  More than 4 players   ")
                M_Print (x, 154, " requires using command ")
                M_Print (x, 162, "line parameters; please ")
                M_Print (x, 170, "   see techinfo.txt.    ")
            else:
                m_serverInfoMessage = False

def M_NetStart_Change(dir):
    global maxplayers, startlevel, startepisode
    global m_serverInfoMessage, m_serverInfoMessageTime

    match gameoptions_cursor:
        case 1:
            maxplayers += dir
            if maxplayers > sv_main.svs.maxclientslimit:
                maxplayers = sv_main.svs.maxclientslimit
                m_serverInfoMessage = True
                m_serverInfoMessageTime = host.realtime
            if maxplayers < 2:
                maxplayers = 2
        case 2:
            cvar.Cvar_Set('coop', '0' if cvar.Cvar_GetCvar('coop').value else '1')
        case 3:
            count = 6 if common.rogue else 2
            f = cvar.Cvar_GetCvar('teamplay').value + dir
            if f > count:
                f = 0
            elif f < 0:
                f = count
            cvar.Cvar_SetValue('teamplay', f)
        case 4:
            f = cvar.Cvar_GetCvar('skill').value + dir
            if f > 3:
                f = 3
            elif f < 0:
                f = 3
            cvar.Cvar_SetValue('skill', f)
        case 5:
            f = cvar.Cvar_GetCvar('fraglimit').value + dir * 10
            if f > 100:
                f = 0
            elif f < 0:
                f = 100
            cvar.Cvar_SetValue('fraglimit', f)
        case 7:
            startepisode += dir
            if common.hipnotic:
                count = 6
            elif common.rogue:
                count = 4
            elif cvar.Cvar_GetCvar('registered').value:
                count = 7
            else:
                count = 2

            if startepisode < 0:
                startepisode = count - 1
            if startepisode >= count:
                startepisode = 0

            startlevel = 0
        case 8:
            startlevel += dir
            if common.hipnotic:
                count = hipnoticepisodes[startepisode].levels
            elif common.rogue:
                count = rogueepisodes[startepisode].levels
            else:
                count = episodes[startepisode].levels
            if startlevel < 0:
                startlevel = count - 1
            if startlevel >= count:
                startlevel = 0


def M_GameOptions_Key(k):
    global gameoptions_cursor
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_Net_f()
        case keys.Key.K_UPARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            gameoptions_cursor -= 1
            if gameoptions_cursor < 0:
                gameoptions_cursor = NUM_GAMEOPTIONS - 1
        case keys.Key.K_DOWNARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            gameoptions_cursor += 1
            if gameoptions_cursor >= NUM_GAMEOPTIONS:
                gameoptions_cursor = 0
        case keys.Key.K_LEFTARROW:
            if gameoptions_cursor == 0:
                return
            snd_dma.S_LocalSound('misc/menu3.wav')
            M_NetStart_Change(-1)
        case keys.Key.K_RIGHTARROW:
            if gameoptions_cursor == 0:
                return
            snd_dma.S_LocalSound('misc/menu3.wav')
            M_NetStart_Change(1)
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            snd_dma.S_LocalSound('misc/menu2.wav')
            if gameoptions_cursor == 0:
                if sv_main.sv.active:
                    _cmd.Cbuf_AddText('disconnect\n')
                _cmd.Cbuf_AddText('listen 0\n')
                _cmd.Cbuf_AddText(f'maxplayers {maxplayers}\n')

                gl_screen.SCR_BeginLoadingPlaque()
                if (common.hipnotic):
                    _cmd.Cbuf_AddText ( f"map {hipnoticlevels[hipnoticepisodes[startepisode].firstLevel + startlevel].name}\n" )
                elif (common.rogue):
                    _cmd.Cbuf_AddText ( f"map {roguelevels[rogueepisodes[startepisode].firstLevel + startlevel].name}\n" );
                else:
                    _cmd.Cbuf_AddText ( f"map {levels[episodes[startepisode].firstLevel + startlevel].name}\n" );
                return
            M_NetStart_Change(1)


def M_Menu_Search_f():
    global m_state, m_entersound, slistSilent, slistLocal, searchComplete
    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_search
    m_entersound = False
    slistSilent = True
    slistLocal = False
    searchComplete = False
    net_main.NET_Slist_f()


def M_Search_Draw():
    global searchComplete, searchCompleteTime

    p = gl_draw.Draw_CachePic('gfx/p_multi.lmp')
    M_DrawPic((320-p.width)/2, 4, p)
    x = (320/2) - ((12*8)/2) + 4
    M_DrawTextBox(x-8, 32, 12, 1)
    M_Print(x, 40, 'Searching ...')

    if net_main.slistInProgress:
        net_main.NET_Poll()
        return

    if not searchComplete:
        searchComplete = True
        searchCompleteTime = host.realtime

    if net_main.hostCacheCount:
        M_Menu_ServerList_f()
        return

    M_PrintWhite((320/2) - ((22*8)/2), 64, "No Quake servers found")
    if ( host.realtime - searchCompleteTime ) < 3.0:
        return

    M_Menu_LanConfig_f()

def M_Search_Key(k):
    pass

def M_Menu_ServerList_f():
    global m_state, m_entersound, slist_cursor, m_return_onerror, m_return_reason, slist_sorted

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_slist
    m_entersound = True
    slist_cursor = 0
    m_return_onerror = False
    m_return_reason = ''
    slist_sorted = False

def M_ServerList_Draw():
    global slist_sorted

    if not slist_sorted:
        slist_sorted = True
        net_main.NET_SlistSort()

    p = gl_draw.Draw_CachePic('gfx/p_multi.lmp')
    M_DrawPic( (320-p.width)/2, 4, p)

    for n in range(net_main.hostCacheCount):
        M_Print(16, 32 + 8*n, net_main.NET_SlistPrintServer(n))
    M_DrawCharacter (0, 32 + slist_cursor*8, 12+(int(host.realtime*4)&1))

    if m_return_reason:
        M_PrintWhite(16, 148, m_return_reason)

def M_ServerList_Key(k):
    global slist_cursor, m_return_state, m_return_onerror, slist_sorted, m_state
    match k:
        case keys.Key.K_ESCAPE | keys.Key.K_BBUTTON:
            M_Menu_LanConfig_f ();
        case keys.Key.K_SPACE:
            M_Menu_Search_f ();
        case keys.Key.K_UPARROW | keys.Key.K_LEFTARROW:
            snd_dma.S_LocalSound ("misc/menu1.wav");
            slist_cursor -= 1
            if (slist_cursor < 0):
                slist_cursor = net_main.hostCacheCount - 1;
        case keys.Key.K_DOWNARROW | keys.Key.K_RIGHTARROW:
            snd_dma.S_LocalSound ("misc/menu1.wav");
            slist_cursor += 1
            if (slist_cursor >= net_main.hostCacheCount):
                slist_cursor = 0;
        case keys.Key.K_ENTER | keys.Key.K_KP_ENTER | keys.Key.K_ABUTTON:
            snd_dma.S_LocalSound ("misc/menu2.wav");
            m_return_state = m_state;
            m_return_onerror = True;
            slist_sorted = False;
            in_sdl.IN_Activate();
            keys.key_dest = keys.keydest_t.key_game;
            m_state = m_state_e.m_none;
            _cmd.Cbuf_AddText ( f"connect \"{net_main.NET_SlistPrintServerName(slist_cursor)}\"\n")










