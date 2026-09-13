#keys.py

from __future__ import annotations

from enum import Enum

import _cmd
import cl_main
import console
import host
import in_sdl
import menu
import quakedef
import vid


class keydest_t(Enum):
    key_game    = 0
    key_console = 1
    key_message = 2
    key_menu    = 3

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

    ('TAB', K_TAB),
    ('ENTER', K_ENTER),
    ('ESCAPE', K_ESCAPE),
    ('SPACE', K_SPACE),
    ('BACKSPACE', K_BACKSPACE),
    ('UPARROW', K_UPARROW),
    ('DOWNARROW', K_DOWNARROW),
    ('LEFTARROW', K_LEFTARROW),
    ('RIGHTARROW', K_RIGHTARROW),

    ('ALT', K_ALT),
    ('CTRL', K_CTRL),
    ('SHIFT', K_SHIFT),

#  ('KP_NUMLOCK', K_KP_NUMLOCK),
    ('KP_SLASH', K_KP_SLASH),
    ('KP_STAR', K_KP_STAR),
    ('KP_MINUS', K_KP_MINUS),
    ('KP_HOME', K_KP_HOME),
    ('KP_UPARROW', K_KP_UPARROW),
    ('KP_PGUP', K_KP_PGUP),
    ('KP_PLUS', K_KP_PLUS),
    ('KP_LEFTARROW', K_KP_LEFTARROW),
    ('KP_5', K_KP_5),
    ('KP_RIGHTARROW', K_KP_RIGHTARROW),
    ('KP_END', K_KP_END),
    ('KP_DOWNARROW', K_KP_DOWNARROW),
    ('KP_PGDN', K_KP_PGDN),
    ('KP_ENTER', K_KP_ENTER),
    ('KP_INS', K_KP_INS),
    ('KP_DEL', K_KP_DEL),

    ('F1', K_F1),
    ('F2', K_F2),
    ('F3', K_F3),
    ('F4', K_F4),
    ('F5', K_F5),
    ('F6', K_F6),
    ('F7', K_F7),
    ('F8', K_F8),
    ('F9', K_F9),
    ('F10', K_F10),
    ('F11', K_F11),
    ('F12', K_F12),

    ('INS', K_INS),
    ('DEL', K_DEL),
    ('PGDN', K_PGDN),
    ('PGUP', K_PGUP),
    ('HOME', K_HOME),
    ('END', K_END),

    ('COMMAND', K_COMMAND),

    ('MOUSE1', K_MOUSE1),
    ('MOUSE2', K_MOUSE2),
    ('MOUSE3', K_MOUSE3),
    ('MOUSE4', K_MOUSE4),
    ('MOUSE5', K_MOUSE5),

    ('JOY1', K_JOY1),
    ('JOY2', K_JOY2),
    ('JOY3', K_JOY3),
    ('JOY4', K_JOY4),

    ('AUX1', K_AUX1),
    ('AUX2', K_AUX2),
    ('AUX3', K_AUX3),
    ('AUX4', K_AUX4),
    ('AUX5', K_AUX5),
    ('AUX6', K_AUX6),
    ('AUX7', K_AUX7),
    ('AUX8', K_AUX8),
    ('AUX9', K_AUX9),
    ('AUX10', K_AUX10),
    ('AUX11', K_AUX11),
    ('AUX12', K_AUX12),
    ('AUX13', K_AUX13),
    ('AUX14', K_AUX14),
    ('AUX15', K_AUX15),
    ('AUX16', K_AUX16),
    ('AUX17', K_AUX17),
    ('AUX18', K_AUX18),
    ('AUX19', K_AUX19),
    ('AUX20', K_AUX20),
    ('AUX21', K_AUX21),
    ('AUX22', K_AUX22),
    ('AUX23', K_AUX23),
    ('AUX24', K_AUX24),
    ('AUX25', K_AUX25),
    ('AUX26', K_AUX26),
    ('AUX27', K_AUX27),
    ('AUX28', K_AUX28),
    ('AUX29', K_AUX29),
    ('AUX30', K_AUX30),
    ('AUX31', K_AUX31),
    ('AUX32', K_AUX32),

    ('PAUSE', K_PAUSE),

    ('MWHEELUP', K_MWHEELUP),
    ('MWHEELDOWN', K_MWHEELDOWN),

    ('SEMICOLON', ';'), # because a raw semicolon seperates commands

    ('BACKQUOTE', '`'), # because a raw backquote may toggle the console
    ('TILDE', '~'),     # because a raw tilde may toggle the console

    ('LTHUMB', K_LTHUMB),
    ('RTHUMB', K_RTHUMB),
    ('LSHOULDER', K_LSHOULDER),
    ('RSHOULDER', K_RSHOULDER),
    ('ABUTTON', K_ABUTTON),
    ('BBUTTON', K_BBUTTON),
    ('XBUTTON', K_XBUTTON),
    ('YBUTTON', K_YBUTTON),
    ('LTRIGGER', K_LTRIGGER),
    ('RTRIGGER', K_RTRIGGER),
    (None,      0)
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

class key_inputgrab_t:
    def __init__(self):
        self.active = False
        self.lastkey = 0
        self.lastchar = 0


key_inputgrab : key_inputgrab_t =  key_inputgrab_t()

key_dest = keydest_t.key_game

keybindings : list[str]  = ["" for _ in range(MAX_KEYS)]
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
        with open(f'{host.parms.userdir}/{HISTORY_FILE_NAME}', 'rt') as hf:
            key_lines = [ line.rstrip() for line in hf ]
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
    if not key:
        return

    if key < 0 or key >= MAX_KEYS:
        return

    # 2. Maintain keydown state
    # If the key is already down and we aren't in console, ignore repeats
    if down:
        if keydown[key]:
            if key_dest == keydest_t.key_game and not console.con_forcedup:
                return
        elif key >= 200 and not keybindings[key]:
            # Optional: Notify about unbound mouse/joy keys
            # console.Con_Printf(f'{Key_KeynumToString(key)} is unbound\n')
            pass
    elif not keydown[key]:
        return # Key was already up

    keydown[key] = down

    # 1. Handle Fullscreen Toggle (Alt + Enter)
    if down and (key == K_ENTER or key == K_KP_ENTER) and keydown[K_ALT]:
        vid.VID_Toggle()
        return

    if keydown[K_CTRL]:
        print('ctrl')
        if key == ord('l'):
            print('l')


    # 3. Handle Input Grab (for binding keys in a menu)
    if key_inputgrab.active:
        if down:
            key_inputgrab.lastkey = key
            if keycode > 0:
                key_inputgrab.lastchar = keycode
        return

    # 4. Handle Escape Key (Priority)
    if key == K_ESCAPE:
        if not down:
            return

        # Shift + Escape toggles console
        if keydown[K_SHIFT]:
            console.Con_ToggleConsole_f()
            return

        match key_dest:
            case keydest_t.key_message:
                Key_EndChat()
            case keydest_t.key_menu:
                menu.M_Keydown(key)
            case keydest_t.key_game | keydest_t.key_console:
                menu.M_ToggleMenu_f()
        return

    if key == ord('`') or key == ord('~'):
        if down:
            console.Con_ToggleConsole_f()
        return

    # 5. Handle Key Up Events
    if not down:
        kb = keybindings[key]
        if kb and isinstance(kb, str) and kb.startswith('+'):
            # Convert +moveup to -moveup
            cmd = f'-{kb[1:]} {key}\n'
            _cmd.Cbuf_AddText(cmd)
        return

    # 6. Console Redirection
    # If console is open and the key is a "console key" (typing character, enter, etc)
    # redirect it to the console buffer instead of the game bindings.
    if key_dest == keydest_t.key_console and consolekeys[key]:
        Key_Console(key)
        return

    # 7. Menu Redirection
    if key_dest == keydest_t.key_menu and menubound[key]:
        menu.M_Keydown(key)
        return

    # 8. Handle Game Bindings
    # If we are here, the key is either for the game or it's a key
    # the console/menu doesn't specifically claim.
    kb = keybindings[key]
    if kb:
        if kb.startswith('+'):
            # Action command (held down)
            cmd = f'{kb} {key}\n'
            _cmd.Cbuf_AddText(cmd)
        else:
            # Impulse/Instant command
            _cmd.Cbuf_AddText(kb)
            _cmd.Cbuf_AddText('\n')
        return

    # 9. Fallback for Chat/Message Mode
    if key_dest == keydest_t.key_message and down:
        # Key_Message(key) logic would go here
        pass


def Key_Init():
    global consolekeys, menubound, key_blinktime

    # Create clean lists of 256 False values
    consolekeys = [False] * 256
    menubound = [False] * 256

    # 1. Allow standard typing characters (Space through ~)
    for i in range(32, 127):
        consolekeys[i] = True

    # 2. Toggle keys must be FALSE so they don't print characters
    consolekeys[ord('`')] = False
    consolekeys[ord('~')] = False

    # 3. Special functional keys
    special_keys = [
        K_TAB, K_ENTER, K_ESCAPE, K_BACKSPACE, K_UPARROW, K_DOWNARROW,
        K_LEFTARROW, K_RIGHTARROW, K_CTRL, K_SHIFT, K_INS, K_DEL,
        K_PGDN, K_PGUP, K_HOME, K_END, K_KP_ENTER
    ]
    for k in special_keys:
        consolekeys[k] = True

    # Initialize menu keys
    menubound[K_ESCAPE] = True
    for i in range(12):
        menubound[K_F1 + i] = True

    History_Init()
    key_blinktime = host.realtime

    _cmd.Cmd_AddCommand('bindlist', Key_Bindlist_f)
    _cmd.Cmd_AddCommand('bind', Key_Bind_f)
    _cmd.Cmd_AddCommand('unbind', Key_Unbind_f)
    _cmd.Cmd_AddCommand('unbindall', Key_Unbindall_f)

def Key_Event(key, down):
    Key_EventWithKeycode(key, down, 0)

def Key_ClearStates():
    for i in range(MAX_KEYS):
        if keydown[i]:
            Key_Event(i, False)


def Key_KeynumToString(keynum):
    # 1. Handle standard printable characters
    if 32 < keynum < 127:
        return chr(keynum).upper()

    # 2. Check the special names table
    for name, num in keynames:
        if num == keynum:
            return name

    # 3. Fallback to raw number if not found
    return str(keynum)

def Key_StringToKeynum(string):
    if not string:
        return -1

    s_upper = string.upper()

    # 1. Check special names (TAB, ENTER, etc)
    for name, num in keynames:
        if name == s_upper:
            return num

    # 2. Check single characters (A-Z)
    if len(string) == 1:
        return ord(s_upper)

    return -1

def Key_Bindlist_f():
    global keybindings
    count = 0

    for i in range(MAX_KEYS):
        if keybindings[i]:
            console.Con_Printf(f'   {Key_KeynumToString(i)} {keybindings[i]}')
            count += 1

    console.Con_Printf(f'{count} bindings')

def Key_SetBinding(keynum, binding):
    global keybindings

    if keynum == -1:
        return

    if keybindings[keynum]:
        keybindings[keynum] = ''

    if binding:
        keybindings[keynum] = binding


def Key_Bind_f():
    c = _cmd.Cmd_Argc()

    if c < 2:
        console.Con_Printf('bind <key> [command]\n')
        return

    # 1. Get the key and strip any leading/trailing quotes
    key_name = _cmd.Cmd_Argv(1).strip('"')
    b = Key_StringToKeynum(key_name)

    if b == -1:
        console.Con_Printf(f'"{key_name}" isn\'t a valid key\n')
        return

    # 2. If only 2 args, show current binding
    if c == 2:
        binding = keybindings[b]
        if binding:
            console.Con_Printf(f'"{key_name}" = "{binding}"\n')
        else:
            console.Con_Printf(f'"{key_name}" is not bound\n')
        return

    # 3. Join all remaining tokens for the command
    # This handles "bind x say hello world" correctly
    args_list = []
    for i in range(2, c):
        args_list.append(_cmd.Cmd_Argv(i))

    # Join and clean quotes from the final command string
    binding = " ".join(args_list).strip('"')

    Key_SetBinding(b, binding)

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


def Key_Console(key):
    global key_linepos

    if key == K_PGUP:
        console.con_backscroll += 5
        console.con_backscroll = min(console.con_backscroll, console.con_totallines - 25)
        return True

    if key == K_PGDN:
        console.con_backscroll -= 5
        console.con_backscroll = max(console.con_backscroll, 0)
        return True

    # Reset scroll when user types or enters command
    if key == K_ENTER:
        console.con_backscroll = 0

    # Handle Backspace (127 or 8 depending on OS mapping)
    if key == K_BACKSPACE or key == 8:
        if len(console.con_input_buffer) > 0:
            console.con_input_buffer = console.con_input_buffer[:-1]
        return

    # Handle Enter
    if key == K_ENTER or key == K_KP_ENTER:
        # Add a newline to the console log for the user to see
        console.Con_Printf(f"] {console.con_input_buffer}\n")

        # Pass to the command buffer to actually DO something
        _cmd.Cbuf_AddText(f"{console.con_input_buffer}\n")

        # Clear the input line
        console.con_input_buffer = ""
        return

    # Handle standard characters
    if isinstance(key, int):
        if key < 32 or key > 127:
            return
        char = chr(key)
    else:
        char = key # already a string from Char_Event

    # Ignore the console toggle key so it doesn't type ` into the console
    if char == '`':
        return

    console.con_input_buffer += char


def Char_Event(ch):
    """
    Called by in_sdl.py when SDL_TEXTINPUT is triggered.
    This handles the actual translated character (like 'A' vs 'a').
    """
    if key_dest == keydest_t.key_console:
        Key_Console(ch)

def WriteBindings(file_handle):
    """Writes all current key bindings to the opened config file."""
    file_handle.write('// key bindings\n')

    active_binds = []

    for i in range(MAX_KEYS):
        # Assuming keybindings is a list of strings parallel to your keycodes
        if keybindings[i]:
            key_name = Key_KeynumToString(i)
            if key_name:
                active_binds.append((key_name, keybindings[i]))

    active_binds.sort()
    for bind_name, command in active_binds:
        file_handle.write(f'bind "{bind_name}" "{command}"\n')

def Key_UpdateForDest():
    global key_dest
    forced = False

    if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
        return

    match(key_dest):
        case keydest_t.key_console:
            if forced and cl_main.cls.state == quakedef.cactive_t.ca_connected:
                forced = False
                in_sdl.IN_Activate()
                key_dest = keydest_t.key_game
        case keydest_t.key_game:
            if cl_main.cls.state != quakedef.cactive_t.ca_connected:
                forced = True
                in_sdl.IN_Deactivate()
                key_dest = keydest_t.key_console

        case _:
            forced = False
