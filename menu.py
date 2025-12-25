#menu.py

from enum import Enum
from random import randint

import _cmd
import console
import cl_main
import cvar
import in_sdl
import keys
import gl_vidsdl
import vid

import sv_main


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

msgNumber = 0
m_quit_prestate: m_state_e = m_state_e.m_none
wasInMenus = False

def StartingGame():
    return m_multiplayer_cursor == 1

def JoiningGame():
    return m_multiplayer_cursor == 0

def TCPIPConfig():
    return m_net_cursor == 1


def M_ToggleMenu_f():
    global m_entersound
    global m_state

    m_entersound = True

    if keys.key_dest == keys.keydest_t.key_menu:
        if m_state != m_main:
            M_Menu_Main_f()
            return

        IN_Activate()
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
    IN_Deactivate(gl_vidsdl.modestate == gl_vidsdl.modestate_t.MS_WINDOWED)
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

    IN_Deactivate(gl_vidsdl.modestate == gl_vidsdl.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu

    M_ScanSaves()

def M_Menu_Setup_f():
    global m_entersound
    global m_state
    global setup_myname
    global setup_hostname
    global setup_top, setup_bottom, setup_oldtop, setup_oldbottom

    IN_Deactivate(gl_vidsdl.modestate == gl_vidsdl.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_setup
    m_entersound = True

    setup_myname   = cvar.Cvar_GetCvar('_cl_name').string
    setup_hostname = cvar.Cvar_GetCvar('hostname').string

    setup_top    = setup_oldtop    = cvar.Cvar_GetCvar('_cl_color').value >> 4
    setup_bottom = setup_oldbottom = cvar.Cvar_GetCvar('_cl_color').value & 15

def M_Menu_Options_f():
    global m_state, m_entersound

    IN_Deactivate(gl_vidsdl.modestate == gl_vidsdl.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_options
    m_entersound = True

def M_Menu_Keys_f():
    global m_state, m_entersound

    IN_Deactivate(gl_vidsdl.modestate == gl_vidsdl.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_state = m_state_e.m_options
    m_entersound = True

def M_Menu_Help_f():
    global m_state, m_entersound, help_page

    IN_Deactivate(gl_vidsdl.modestate == gl_vidsdl.modestate_t.MS_WINDOWED)
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
    IN_Deactivate(gl_vidsdl.modestate == gl_vidsdl.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    m_quit_prestate = m_state
    m_state = m_state_e.m_quit
    m_entersound = True
    msgNumber = randint(7)

def M_Menu_Credits_f():
    raise NotImplementedError

def M_Menu_Video_f():
    global vid_menucmdfn
    vid_menucmdfn()

def M_Video_Draw():
    global vid_menudrawfn
    vid_menudrawfn()

def M_Video_Key(key):
    global vid_menukeyfn
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