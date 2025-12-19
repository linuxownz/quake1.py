#keys.py 

from __future__ import annotations
from enum import Enum

import host
import _cmd
import client
import console
import vid
import menu

# these are the key number
K_TAB           = 9
K_ENTER         = 13
K_ESCAPE        = 27
K_SPACE         = 32


K_BACKSPACE     = 127
K_UPARROW       = 128
K_DOWNARROW     = 129
K_LEFTARROW     = 130
K_RIGHTARROW    = 131

K_ALT           = 132
K_CTRL          = 133
K_SHIFT         = 134
K_F1            = 135
K_F2            = 136
K_F3            = 137
K_F4            = 138
K_F5            = 139
K_F6            = 140
K_F7            = 141
K_F8            = 142
K_F9            = 143
K_F10           = 144
K_F11           = 145
K_F12           = 146
K_INS           = 147
K_DEL           = 148
K_PGDN          = 149
K_PGUP          = 150
K_HOME          = 151
K_END           = 152

K_KP_NUMLOCK    = 153
K_KP_SLASH      = 154
K_KP_STAR       = 155
K_KP_MINUS      = 156
K_KP_HOME       = 157
K_KP_UPARROW    = 158
K_KP_PGUP       = 159
K_KP_PLUS       = 160
K_KP_LEFTARROW  = 161
K_KP_5          = 162
K_KP_RIGHTARROW = 163
K_KP_END        = 164
K_KP_DOWNARROW  = 165
K_KP_PGDN       = 166
K_KP_ENTER      = 167
K_KP_INS        = 168
K_KP_DEL        = 169

K_COMMAND       = 170

K_PAUSE         = 255

K_MOUSE1        = 200
K_MOUSE2        = 201
K_MOUSE3        = 202

K_JOY1          = 203
K_JOY2          = 204
K_JOY3          = 205
K_JOY4          = 206

K_AUX1          = 207
K_AUX2          = 208
K_AUX3          = 209
K_AUX4          = 210
K_AUX5          = 211
K_AUX6          = 212
K_AUX7          = 213
K_AUX8          = 214
K_AUX9          = 215
K_AUX10         = 216
K_AUX11         = 217
K_AUX12         = 218
K_AUX13         = 219
K_AUX14         = 220
K_AUX15         = 221
K_AUX16         = 222
K_AUX17         = 223
K_AUX18         = 224
K_AUX19         = 225
K_AUX20         = 226
K_AUX21         = 227
K_AUX22         = 228
K_AUX23         = 229
K_AUX24         = 230
K_AUX25         = 231
K_AUX26         = 232
K_AUX27         = 233
K_AUX28         = 234
K_AUX29         = 235
K_AUX30         = 236
K_AUX31         = 237
K_AUX32         = 238

K_MWHEELUP      = 239
K_MWHEELDOWN    = 240

K_MOUSE4        = 241
K_MOUSE5        = 242

# sdl2 game controller keys
K_LTHUMB        = 243
K_RTHUMB        = 244
K_LSHOULDER     = 245
K_RSHOULDER     = 246
K_ABUTTON       = 247
K_BBUTTON       = 248
K_XBUTTON       = 249
K_YBUTTON       = 250
K_LTRIGGER      = 251
K_RTRIGGER      = 252

MAX_KEYS        = 256

keynames = [

    {'TAB', K_TAB},
    {'ENTER', K_ENTER},
    {'ESCAPE', K_ESCAPE},
    {'SPACE', K_SPACE},
    {'BACKSPACE', K_BACKSPACE},
    {'UPARROW', K_UPARROW},
    {'DOWNARROW', K_DOWNARROW},
    {'LEFTARROW', K_LEFTARROW},
    {'RIGHTARROW', K_RIGHTARROW},

    {'ALT', K_ALT},
    {'CTRL', K_CTRL},
    {'SHIFT', K_SHIFT},

#  {'KP_NUMLOCK', K_KP_NUMLOCK},
    {'KP_SLASH', K_KP_SLASH},
    {'KP_STAR', K_KP_STAR},
    {'KP_MINUS', K_KP_MINUS},
    {'KP_HOME', K_KP_HOME},
    {'KP_UPARROW', K_KP_UPARROW},
    {'KP_PGUP', K_KP_PGUP},
    {'KP_PLUS', K_KP_PLUS},
    {'KP_LEFTARROW', K_KP_LEFTARROW},
    {'KP_5', K_KP_5},
    {'KP_RIGHTARROW', K_KP_RIGHTARROW},
    {'KP_END', K_KP_END},
    {'KP_DOWNARROW', K_KP_DOWNARROW},
    {'KP_PGDN', K_KP_PGDN},
    {'KP_ENTER', K_KP_ENTER},
    {'KP_INS', K_KP_INS},
    {'KP_DEL', K_KP_DEL},

    {'F1', K_F1},
    {'F2', K_F2},
    {'F3', K_F3},
    {'F4', K_F4},
    {'F5', K_F5},
    {'F6', K_F6},
    {'F7', K_F7},
    {'F8', K_F8},
    {'F9', K_F9},
    {'F10', K_F10},
    {'F11', K_F11},
    {'F12', K_F12},

    {'INS', K_INS},
    {'DEL', K_DEL},
    {'PGDN', K_PGDN},
    {'PGUP', K_PGUP},
    {'HOME', K_HOME},
    {'END', K_END},

    {'COMMAND', K_COMMAND},

    {'MOUSE1', K_MOUSE1},
    {'MOUSE2', K_MOUSE2},
    {'MOUSE3', K_MOUSE3},
    {'MOUSE4', K_MOUSE4},
    {'MOUSE5', K_MOUSE5},

    {'JOY1', K_JOY1},
    {'JOY2', K_JOY2},
    {'JOY3', K_JOY3},
    {'JOY4', K_JOY4},

    {'AUX1', K_AUX1},
    {'AUX2', K_AUX2},
    {'AUX3', K_AUX3},
    {'AUX4', K_AUX4},
    {'AUX5', K_AUX5},
    {'AUX6', K_AUX6},
    {'AUX7', K_AUX7},
    {'AUX8', K_AUX8},
    {'AUX9', K_AUX9},
    {'AUX10', K_AUX10},
    {'AUX11', K_AUX11},
    {'AUX12', K_AUX12},
    {'AUX13', K_AUX13},
    {'AUX14', K_AUX14},
    {'AUX15', K_AUX15},
    {'AUX16', K_AUX16},
    {'AUX17', K_AUX17},
    {'AUX18', K_AUX18},
    {'AUX19', K_AUX19},
    {'AUX20', K_AUX20},
    {'AUX21', K_AUX21},
    {'AUX22', K_AUX22},
    {'AUX23', K_AUX23},
    {'AUX24', K_AUX24},
    {'AUX25', K_AUX25},
    {'AUX26', K_AUX26},
    {'AUX27', K_AUX27},
    {'AUX28', K_AUX28},
    {'AUX29', K_AUX29},
    {'AUX30', K_AUX30},
    {'AUX31', K_AUX31},
    {'AUX32', K_AUX32},

    {'PAUSE', K_PAUSE},

    {'MWHEELUP', K_MWHEELUP},
    {'MWHEELDOWN', K_MWHEELDOWN},

    {'SEMICOLON', ';'}, # because a raw semicolon seperates commands

    {'BACKQUOTE', '`'}, # because a raw backquote may toggle the console
    {'TILDE', '~'},     # because a raw tilde may toggle the console

    {'LTHUMB', K_LTHUMB},
    {'RTHUMB', K_RTHUMB},
    {'LSHOULDER', K_LSHOULDER},
    {'RSHOULDER', K_RSHOULDER},
    {'ABUTTON', K_ABUTTON},
    {'BBUTTON', K_BBUTTON},
    {'XBUTTON', K_XBUTTON},
    {'YBUTTON', K_YBUTTON},
    {'LTRIGGER', K_LTRIGGER},
    {'RTRIGGER', K_RTRIGGER},
    {None,      0}
]

HISTORY_FILE_NAME = 'history.txt'
key_lines = []

key_linepos = 0
key_insert  = 0
key_blinktime = 0.0

edit_line = 0
history_line = 0

class keydest_t(Enum):
    key_game    = 0
    key_console = 1 
    key_message = 2
    key_menu    = 3

class key_inputgrab_t():
    def __init__(self):
        self.active = False
        self.lastkey = 0
        self.lastchar = 0


key_inputgrab : key_inputgrab_t =  key_inputgrab_t()

key_dest = keydest_t.key_game

keybindings : list[bool] = [False for _ in range(256)]
consolekeys : list[bool] = [False for _ in range(256)]
menubound   : list[bool] = [False for _ in range(256)]
keydown     : list[bool] = [False for _ in range(256)]

chat_team = False
chat_buffer = []

def Key_EndChat():
    global key_dest

    key_dest = keydest_t.key_game
    chat_buffer = []

def History_Init():
    global key_lines
    try:
        with open(f'{parms.userdir}/{HISTORY_FILE_NAME}', 'rt') as hf:
            key_lines = [ line.rstrip() for line in hf.readlines() ]
        key_lines.insert(0, ']')
    except:
        pass

def Key_TextEntry() -> bool:
    if key_inputgrab.active:
        return False

    match key_dest:
        case keydest_t.key_message:
            return True
        case keydest_t.key_menu:
            return M_TextEntry()
        case keydest_t.key_game:
            return False
        case keydest_t.key_console:
            return True
        case _:
            return False

def Key_EventWithKeycode(key, down, keycode):
    if key < 0 or key >= MAX_KEYS:
        return
    
    if down and ( key == K_ENTER or key == K_KP_ENTER) and keydown[K_ALT]:
        vid.VID_Toggle()
        return

    if down:
        if keydown[key]:
            if key_dest == keydest_t.key_game and not console.con_forcedup:
                return
        elif key >= 200 and not keybindings[key]:
            console.Con_Printf(f'{Key_KeynumToString(key)} is unbound, hit F4 to set\n')
    elif not keydown[key]:
        return

    keydown[key] = down

    if key_inputgrab.active:
        if down:
            key_inputgrab.lastkey = key
            if keycode > 0:
                key_inputgrab.lastchar = keycode
        return

    if key == K_ESCAPE:
        if not down:
            return
        
        if keydown[K_SHIFT]:
            console.Con_ToggleConsole_f()
            return

        match key_dest:
            case keydest_t.key_message:
                Key_Message(key)
            case keydest_t.key_menu:
                menu.M_Keydown(key)
            case keydest_t.key_game | keydest_t.key_console:
                menu.M_ToggleMenu_f()
            case _:
                Sys_Error('Bad key_dest')
        
        return
    
    if not down:
        kb = keybindings[key]
        if kb and kb[0] == '+':
            cmd = f'-{kb[1:]} {key}\n'
            Cbuf_AddText(cmd)
        
        return

    if client.cls.demoplayback and down and consolekeys[key] and key_dest == keydest_t.key_game and key != K_TAB:
        menu.M_ToggleMenu_f()
        return

    if (key_dest == keydest_t.key_menu and menubound[key]) or (key_dest == keydest_t.key_console and not consolekeys[key]) or (key_dest == keydest_t.key_game and ( not console.con_forcedup or not consolekeys[key])):
        kb = keybindings[key]
        if kb:
            if kb[0] == '+':
                cmd = f'{kb} {key}\n'
                Cbuf_AddText(cmd)
            else:
                Cbuf_AddText(kb)
                Cbuf_AddText('\n')
        return

    if not down:
        return

    match key_dest:
        case keydest_t.key_message:
            Key_Message(key)
        case keydest_t.key_menu:
            menu.M_Keydown(key)
        case keydest_t.key_game | keydest_t.key_console:
            Key_Console(key)
        case _:
            Sys_Error('bad key_dest')

        




    






def Key_Event(key, down):
    Key_EventWithKeycode(key, down, 0)

def Key_ClearStates():
    for i in range(MAX_KEYS):
        if keydown[i]:
            Key_Event(i, False)

def Key_Init():
    global consolekeys
    global menubound

    global key_blinktime

    #from main_sdl import parms

    History_Init()

    key_blinktime = host.realtime

    for i in range (256):
        consolekeys.append(False)

    for i in range(32, 127):
        consolekeys[i] = True

    consolekeys[ord('`')] = False;
    consolekeys[ord('~')] = False;
    consolekeys[K_TAB] = True;
    consolekeys[K_ENTER] = True;
    consolekeys[K_ESCAPE] = True;
    consolekeys[K_BACKSPACE] = True;
    consolekeys[K_UPARROW] = True;
    consolekeys[K_DOWNARROW] = True;
    consolekeys[K_LEFTARROW] = True;
    consolekeys[K_RIGHTARROW] = True;
    consolekeys[K_CTRL] = True;
    consolekeys[K_SHIFT] = True;
    consolekeys[K_INS] = True;
    consolekeys[K_DEL] = True;
    consolekeys[K_PGDN] = True;
    consolekeys[K_PGUP] = True;
    consolekeys[K_HOME] = True;
    consolekeys[K_END] = True;
    consolekeys[K_KP_NUMLOCK] = True;
    consolekeys[K_KP_SLASH] = True;
    consolekeys[K_KP_STAR] = True;
    consolekeys[K_KP_MINUS] = True;
    consolekeys[K_KP_HOME] = True;
    consolekeys[K_KP_UPARROW] = True;
    consolekeys[K_KP_PGUP] = True;
    consolekeys[K_KP_PLUS] = True;
    consolekeys[K_KP_LEFTARROW] = True;
    consolekeys[K_KP_5] = True;
    consolekeys[K_KP_RIGHTARROW] = True;
    consolekeys[K_KP_END] = True;
    consolekeys[K_KP_DOWNARROW] = True;
    consolekeys[K_KP_PGDN] = True;
    consolekeys[K_KP_ENTER] = True;
    consolekeys[K_KP_INS] = True;
    consolekeys[K_KP_DEL] = True;
    consolekeys[K_MWHEELUP] = True;
    consolekeys[K_MWHEELDOWN] = True;

    for i in range (256):
        menubound.append(False)

    menubound[K_ESCAPE] = True
    for i in range(12):
        menubound[K_F1 + i] = True

    _cmd.Cmd_AddCommand('bindlist', Key_Bindlist_f)
    _cmd.Cmd_AddCommand('bind', Key_Bind_f)
    _cmd.Cmd_AddCommand('unbind', Key_Unbind_f)
    _cmd.Cmd_AddCommand('unbindall', Key_Unbindall_f)


def Key_KeynumToString(keynum):
    global keynames
    if keynum == -1:
        return '<KEY NOT FOUND>'

    if keynum > 32 and keynum < 127:
        return chr(keynum)

    for kn in keynames:
        l = list(kn)
        if l[1] == keynum:
            return l[0]
    
def Key_StringToKeynum(string):
    global keynames
    for kn in keynames:
        l = list(kn)
        if l[0] == string:
            return l[1]
    return -1

def Key_Bindlist_f():
    global keybindings
    count = 0

    for i in range(MAX_KEYS):
        if keybindings[i]:
            console.Con_SafePrintf(f'   {Key_KeynumToString(i)} {keybindings[i]}')
            count += 1

    console.Con_SafePrintf(f'{count} bindings')

def Key_SetBinding(keynum, binding):
    global keybindings

    if keynum == -1:
        return

    if keybindings[keynum]:
        keybindings[keynum] = ''

    if binding:
        keybindings[keynum] = binding


def Key_Bind_f():
    global keybindings

    c = Cmd_Argc()

    if c != 2 and c != 3:
        console.Con_Printf('bind <key> [command] : attach a command to a key')
        return

    b = Key_StringToKeynum(Cmd_Argv(1))
    if b == -1:
        console.Con_Printf(f'{Cmd_Argv(1)} isnt a valid key')
        return

    if c == 2:
        if keybindings[b]:
            console.Con_Printf(f'{Cmd_Argv(1)} = {keybindings[b]}') 
        else:
            console.Con_Printf(f'{Cmd_Argv(1)} is unbound')
        return

    cmd = ''
    for i in range(2, c):
        cmd += Cmd_Argv(i)

        if i != (c-1):
            cmd += ' '

    Key_SetBinding(b, cmd)

def Key_Unbind_f():
    if Cmd_Argc() != 2:
        console.Con_Printf('unbind <key> : remove commands from a key')
        return

    b = Key_StringToKeynum(Cmd_Argv(1))
    if b == -1:
        console.Con_Printf(f'{Cmd_Argv(1)} isnt a valid key')
        return

    Key_SetBinding(b, '')

def Key_Unbindall_f():
    global keybindings
    for i in range(MAX_KEYS):
        if keybindings[i]:
            Key_SetBinding(i, '')


