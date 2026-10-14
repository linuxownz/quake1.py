#keys.py

from __future__ import annotations

from enum import Enum, IntEnum

import _cmd
import cl_main
import console
import gl_vidsdl
import host
import in_sdl
import keys
import menu
import pl_linux  # Or wherever PL_GetClipboardData is defined
import quakedef
import sys_sdl_unix
import vid


class keydest_t(Enum):
    key_game    = 0
    key_console = 1
    key_message = 2
    key_menu    = 3

# these are the key number
class Key(IntEnum):
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

MAXCMDLINE = 256

keynames = [

    ('TAB', Key.K_TAB),
    ('ENTER', Key.K_ENTER),
    ('ESCAPE', Key.K_ESCAPE),
    ('SPACE', Key.K_SPACE),
    ('BACKSPACE', Key.K_BACKSPACE),
    ('UPARROW', Key.K_UPARROW),
    ('DOWNARROW', Key.K_DOWNARROW),
    ('LEFTARROW', Key.K_LEFTARROW),
    ('RIGHTARROW', Key.K_RIGHTARROW),

    ('ALT', Key.K_ALT),
    ('CTRL', Key.K_CTRL),
    ('SHIFT', Key.K_SHIFT),

#  ('KP_NUMLOCK', K_KP_NUMLOCK),
    ('KP_SLASH', Key.K_KP_SLASH),
    ('KP_STAR', Key.K_KP_STAR),
    ('KP_MINUS', Key.K_KP_MINUS),
    ('KP_HOME', Key.K_KP_HOME),
    ('KP_UPARROW', Key.K_KP_UPARROW),
    ('KP_PGUP', Key.K_KP_PGUP),
    ('KP_PLUS', Key.K_KP_PLUS),
    ('KP_LEFTARROW', Key.K_KP_LEFTARROW),
    ('KP_5', Key.K_KP_5),
    ('KP_RIGHTARROW', Key.K_KP_RIGHTARROW),
    ('KP_END', Key.K_KP_END),
    ('KP_DOWNARROW', Key.K_KP_DOWNARROW),
    ('KP_PGDN', Key.K_KP_PGDN),
    ('KP_ENTER', Key.K_KP_ENTER),
    ('KP_INS', Key.K_KP_INS),
    ('KP_DEL', Key.K_KP_DEL),

    ('F1', Key.K_F1),
    ('F2', Key.K_F2),
    ('F3', Key.K_F3),
    ('F4', Key.K_F4),
    ('F5', Key.K_F5),
    ('F6', Key.K_F6),
    ('F7', Key.K_F7),
    ('F8', Key.K_F8),
    ('F9', Key.K_F9),
    ('F10', Key.K_F10),
    ('F11', Key.K_F11),
    ('F12', Key.K_F12),

    ('INS', Key.K_INS),
    ('DEL', Key.K_DEL),
    ('PGDN', Key.K_PGDN),
    ('PGUP', Key.K_PGUP),
    ('HOME', Key.K_HOME),
    ('END', Key.K_END),

    ('COMMAND', Key.K_COMMAND),

    ('MOUSE1', Key.K_MOUSE1),
    ('MOUSE2', Key.K_MOUSE2),
    ('MOUSE3', Key.K_MOUSE3),
    ('MOUSE4', Key.K_MOUSE4),
    ('MOUSE5', Key.K_MOUSE5),

    ('JOY1', Key.K_JOY1),
    ('JOY2', Key.K_JOY2),
    ('JOY3', Key.K_JOY3),
    ('JOY4', Key.K_JOY4),

    ('AUX1', Key.K_AUX1),
    ('AUX2', Key.K_AUX2),
    ('AUX3', Key.K_AUX3),
    ('AUX4', Key.K_AUX4),
    ('AUX5', Key.K_AUX5),
    ('AUX6', Key.K_AUX6),
    ('AUX7', Key.K_AUX7),
    ('AUX8', Key.K_AUX8),
    ('AUX9', Key.K_AUX9),
    ('AUX10', Key.K_AUX10),
    ('AUX11', Key.K_AUX11),
    ('AUX12', Key.K_AUX12),
    ('AUX13', Key.K_AUX13),
    ('AUX14', Key.K_AUX14),
    ('AUX15', Key.K_AUX15),
    ('AUX16', Key.K_AUX16),
    ('AUX17', Key.K_AUX17),
    ('AUX18', Key.K_AUX18),
    ('AUX19', Key.K_AUX19),
    ('AUX20', Key.K_AUX20),
    ('AUX21', Key.K_AUX21),
    ('AUX22', Key.K_AUX22),
    ('AUX23', Key.K_AUX23),
    ('AUX24', Key.K_AUX24),
    ('AUX25', Key.K_AUX25),
    ('AUX26', Key.K_AUX26),
    ('AUX27', Key.K_AUX27),
    ('AUX28', Key.K_AUX28),
    ('AUX29', Key.K_AUX29),
    ('AUX30', Key.K_AUX30),
    ('AUX31', Key.K_AUX31),
    ('AUX32', Key.K_AUX32),

    ('PAUSE', Key.K_PAUSE),

    ('MWHEELUP', Key.K_MWHEELUP),
    ('MWHEELDOWN', Key.K_MWHEELDOWN),

    ('SEMICOLON', ord(';')), # because a raw semicolon seperates commands

    ('BACKQUOTE', ord('`')), # because a raw backquote may toggle the console
    ('TILDE', ord('~')),     # because a raw tilde may toggle the console

    ('LTHUMB', Key.K_LTHUMB),
    ('RTHUMB', Key.K_RTHUMB),
    ('LSHOULDER', Key.K_LSHOULDER),
    ('RSHOULDER', Key.K_RSHOULDER),
    ('ABUTTON', Key.K_ABUTTON),
    ('BBUTTON', Key.K_BBUTTON),
    ('XBUTTON', Key.K_XBUTTON),
    ('YBUTTON', Key.K_YBUTTON),
    ('LTRIGGER', Key.K_LTRIGGER),
    ('RTRIGGER', Key.K_RTRIGGER),
    (None,      0)
]

NUM_KEY_LINES = 64
HISTORY_FILE_NAME = 'history.txt'
key_lines: list[bytearray] = [ bytearray(MAXCMDLINE) for _ in range(NUM_KEY_LINES) ]

key_linepos = 0
key_insert  = 0
key_blinktime = 0.0

edit_line = 0
history_line = 0

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
chat_buffer = ''
key_tabpartial = bytearray(MAXCMDLINE)
_current_line = bytearray(MAXCMDLINE)   # edit line saved while browsing history
_key_forced = False


def PasteToConsole() -> None:
    """Pastes clipboard text into the active console command line buffer at the current cursor position.

    C equivalent (keys.c):
    static void PasteToConsole (void)
    """
    if keys.key_linepos >= keys.MAXCMDLINE - 1:
        return

    cbd = pl_linux.PL_GetClipboardData()
    if cbd is None:
        return

    # Strip newlines, carriage returns, or backspaces at the first occurrence
    clean_text = ""
    for char in cbd:
        if char in ("\n", "\r", "\b"):
            break
        clean_text += char

    cbd_bytes = clean_text.encode("latin-1", errors="replace")
    inslen = len(cbd_bytes)

    # Truncate insert length if it exceeds the remaining command line buffer
    if inslen + keys.key_linepos > keys.MAXCMDLINE - 1:
        inslen = keys.MAXCMDLINE - 1 - keys.key_linepos

    if inslen <= 0:
        return

    # Retrieve current active console line (bytearray of length MAXCMDLINE)
    workline = keys.key_lines[keys.edit_line]

    # Calculate length of existing text after cursor
    # (Find null terminator or measure to end)
    current_tail = workline[keys.key_linepos :]
    null_idx = current_tail.find(b"\x00")
    if null_idx != -1:
        mvlen = null_idx
    else:
        mvlen = len(current_tail)

    # Clamp move length if tail overflows MAXCMDLINE - 1
    if mvlen + inslen + keys.key_linepos > keys.MAXCMDLINE - 1:
        mvlen = keys.MAXCMDLINE - 1 - keys.key_linepos - inslen
        mvlen = max(mvlen, 0)

    # memmove: shift existing trailing text to the right by inslen
    if mvlen > 0:
        src_start = keys.key_linepos
        src_end = keys.key_linepos + mvlen
        dst_start = keys.key_linepos + inslen
        dst_end = dst_start + mvlen
        workline[dst_start:dst_end] = workline[src_start:src_end]

    # memcpy: insert clipboard bytes at cursor
    workline[keys.key_linepos : keys.key_linepos + inslen] = cbd_bytes[:inslen]

    # Advance cursor position
    keys.key_linepos += inslen

    # Null-terminate line buffer
    term_pos = keys.key_linepos + mvlen
    if term_pos < keys.MAXCMDLINE:
        workline[term_pos] = 0


def _linelen(b) -> int:
    i = b.find(0)
    return len(b) if i < 0 else i

def _reset_line(b) -> None:
    b[:] = bytes(MAXCMDLINE)
    b[0] = ord(']')

def _userdir():
    p = getattr(host, 'host_parms', None) or getattr(host, 'parms', None)
    return getattr(p, 'userdir', None)

def History_Init():
    global edit_line, history_line, key_linepos
    userdir = _userdir()
    if userdir:
        try:
            with open(f'{userdir}/{HISTORY_FILE_NAME}', 'rt') as hf:
                for line in hf:
                    line = line.rstrip('\r\n')
                    if not line:
                        continue
                    buf = bytearray(MAXCMDLINE)
                    data = (']' + line).encode('latin-1', errors='replace')[:MAXCMDLINE - 1]
                    buf[:len(data)] = data
                    key_lines[edit_line] = buf
                    edit_line = (edit_line + 1) % NUM_KEY_LINES
        except OSError:
            pass

    history_line = edit_line
    _reset_line(key_lines[edit_line])
    key_linepos = 1


def History_Shutdown():
    userdir = _userdir()
    if not userdir:
        return
    try:
        with open(f'{userdir}/{HISTORY_FILE_NAME}', 'wt') as f:
            for k in range(1, NUM_KEY_LINES + 1):
                line = key_lines[(edit_line + k) % NUM_KEY_LINES]
                n = _linelen(line)
                if n > 1:
                    f.write(line[1:n].decode('latin-1') + '\n')
    except OSError:
        console.Con_Printf('failed to write history file\n')

def Key_TextEntry() -> bool:
    if key_inputgrab.active:
        return False

    match key_dest:
        case keydest_t.key_message:
            return True
        case keydest_t.key_menu:
            return menu.M_TextEntry()
        case keydest_t.key_game:
            return False
        case keydest_t.key_console:
            return True
        case _:
            return False

def Key_EventWithKeycode(key, down, keycode):
    if not key:
        return

    if isinstance(key, str):
        key = ord(key)

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
    if down and (key == keys.Key.K_ENTER or key == keys.Key.K_KP_ENTER) and keydown[keys.Key.K_ALT]:
        vid.VID_Toggle()
        return

    # 3. Handle Input Grab (for binding keys in a menu)
    if key_inputgrab.active:
        if down:
            key_inputgrab.lastkey = key
            if keycode > 0:
                key_inputgrab.lastchar = keycode
        return

    # 4. Handle Escape Key (Priority)
    if key == keys.Key.K_ESCAPE:
        if not down:
            return

        # Shift + Escape toggles console
        if keydown[keys.Key.K_SHIFT]:
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

    if key_dest == keydest_t.key_message:
        Key_Message(key)
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
    global consolekeys, menubound, key_blinktime, key_linepos

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
        Key.K_TAB, Key.K_ENTER, Key.K_ESCAPE, Key.K_BACKSPACE, Key.K_UPARROW, Key.K_DOWNARROW,
        Key.K_LEFTARROW, Key.K_RIGHTARROW, Key.K_CTRL, Key.K_SHIFT, Key.K_INS, Key.K_DEL,
        Key.K_PGDN, Key.K_PGUP, Key.K_HOME, Key.K_END, Key.K_KP_ENTER
    ]
    for k in special_keys:
        consolekeys[k] = True
    consolekeys[Key.K_MWHEELUP] = True
    consolekeys[Key.K_MWHEELDOWN] = True

    for line in key_lines:
        _reset_line(line)
    key_linepos = 1

    # Initialize menu keys
    menubound[Key.K_ESCAPE] = True
    for i in range(12):
        menubound[Key.K_F1 + i] = True

    History_Init()
    key_blinktime = host.realtime

    _cmd.Cmd_AddCommand('bindlist', Key_Bindlist_f)
    _cmd.Cmd_AddCommand('bind', Key_Bind_f)
    _cmd.Cmd_AddCommand('unbind', Key_Unbind_f)
    _cmd.Cmd_AddCommand('unbindall', Key_Unbindall_f)



def Key_BeginInputGrab():
    Key_ClearStates()

    key_inputgrab.active = True
    key_inputgrab.lastkey = -1
    key_inputgrab.lastchar = -1

    in_sdl.IN_UpdateInputMode()

def Key_EndInputGrab():
    Key_ClearStates()
    key_inputgrab.active = False
    in_sdl.IN_UpdateInputMode()

def Key_GetGrabbedInput() -> tuple[int, int]:
    return key_inputgrab.lastkey, key_inputgrab.lastchar




def Key_Event(key, down):
    Key_EventWithKeycode(key, down, 0)

def Key_ClearStates():
    for i in range(MAX_KEYS):
        if keydown[i]:
            Key_Event(i, False)


def Key_KeynumToString(keynum):
    # 1. Handle standard printable characters
    if 32 < keynum < 127:
        return chr(keynum)

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
        return ord(string.lower())

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
    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf('unbind <key> : remove commands from a key')
        return

    b = Key_StringToKeynum(_cmd.Cmd_Argv(1))
    if b == -1:
        console.Con_Printf(f'{_cmd.Cmd_Argv(1)} isnt a valid key')
        return

    Key_SetBinding(b, '')

def Key_Unbindall_f():
    global keybindings
    for i in range(MAX_KEYS):
        if keybindings[i]:
            Key_SetBinding(i, '')

def Key_Console(key):
    global key_linepos, edit_line, history_line, key_insert, key_blinktime

    workline = key_lines[edit_line]
    ctrl  = keydown[Key.K_CTRL]
    shift = keydown[Key.K_SHIFT]

    if key in (Key.K_ENTER, Key.K_KP_ENTER):
        key_tabpartial[0] = 0
        n = _linelen(workline)
        _cmd.Cbuf_AddText(workline[1:n].decode('latin-1'))   # skip the prompt
        _cmd.Cbuf_AddText('\n')
        console.Con_Printf(workline[:n].decode('latin-1') + '\n')
        edit_line = (edit_line + 1) % NUM_KEY_LINES
        history_line = edit_line
        _reset_line(key_lines[edit_line])
        key_linepos = 1
        return True

    if key == Key.K_BACKSPACE:
        key_tabpartial[0] = 0
        if key_linepos > 1:
            del workline[key_linepos - 1]
            workline.append(0)
            key_linepos -= 1
        return True

    if key == Key.K_DEL:
        key_tabpartial[0] = 0
        if key_linepos < _linelen(workline):
            del workline[key_linepos]
            workline.append(0)
        return True

    if key == Key.K_HOME:
        if ctrl:
            console.con_backscroll = max(console.con_totallines - 25, 0)
        else:
            key_linepos = 1
        return True

    if key == Key.K_END:
        if ctrl:
            console.con_backscroll = 0
        else:
            key_linepos = _linelen(workline)
        return True

    if key == Key.K_LEFTARROW:
        if key_linepos > 1:
            key_linepos -= 1
            key_blinktime = host.realtime
        return True

    if key == Key.K_RIGHTARROW:
        if key_linepos < _linelen(workline):
            key_linepos += 1
            key_blinktime = host.realtime
        return True

    if key == Key.K_UPARROW:
        if history_line == edit_line:
            _current_line[:] = workline
        while True:
            history_line = (history_line - 1) % NUM_KEY_LINES
            if history_line == edit_line or key_lines[history_line][1]:
                break
        if history_line == edit_line:
            history_line = (edit_line + 1) % NUM_KEY_LINES
        workline[:] = key_lines[history_line]
        key_linepos = _linelen(workline)
        return True

    if key == Key.K_DOWNARROW:
        if history_line == edit_line:
            return True
        while True:
            history_line = (history_line + 1) % NUM_KEY_LINES
            if history_line == edit_line or key_lines[history_line][1]:
                break
        if history_line == edit_line:
            workline[:] = _current_line
        else:
            workline[:] = key_lines[history_line]
        key_linepos = _linelen(workline)
        return True

    if key in (Key.K_PGUP, Key.K_MWHEELUP):
        console.con_backscroll = min(console.con_backscroll + (2 if key == Key.K_MWHEELUP else 5),
                                     console.con_totallines - 25)
        return True

    if key in (Key.K_PGDN, Key.K_MWHEELDOWN):
        console.con_backscroll = max(console.con_backscroll - (2 if key == Key.K_MWHEELDOWN else 5), 0)
        return True

    if key == Key.K_INS:
        if shift:
            PasteToConsole()
        else:
            key_insert = not key_insert
        return True

    if key == ord('v') and ctrl:
        PasteToConsole()
        return True

    # printable characters arrive through Char_Event (text input), not here
    return True

def Char_Console(key: int) -> None:
    """Appends or inserts a character byte into the console input line.
    C equivalent (keys.c):
    void Char_Console (int key)
    """
    workline = keys.key_lines[keys.edit_line]

    if keys.key_linepos < keys.MAXCMDLINE - 1:
        # qboolean endpos = !workline[key_linepos];
        endpos = workline[keys.key_linepos] == 0

        keys.key_tabpartial[0] = 0  # Reset tab completion buffer

        # If insert mode is enabled and not at the end of string, shift trailing text right
        if keys.key_insert and not endpos:
            workline[keys.MAXCMDLINE - 2] = 0

            # Find null terminator to determine string length (strlen(workline + key_linepos) + 1)
            tail = workline[keys.key_linepos :]
            null_idx = tail.find(b"\x00")
            if null_idx != -1:
                length = null_idx + 1
            else:
                length = len(tail)

            # memmove(workline + 1, workline, len);
            src_start = keys.key_linepos
            src_end = keys.key_linepos + length
            dst_start = keys.key_linepos + 1
            dst_end = dst_start + length

            # Prevent writing past MAXCMDLINE boundary
            if dst_end > keys.MAXCMDLINE:
                dst_end = keys.MAXCMDLINE
                src_end = dst_end - 1

            workline[dst_start:dst_end] = workline[src_start:src_end]

            # *workline = key;
            workline[keys.key_linepos] = key & 0xFF
        else:
            # Overwrite or append at current cursor position
            workline[keys.key_linepos] = key & 0xFF

            # Null terminate if at the end of string
            if endpos and (keys.key_linepos + 1) < keys.MAXCMDLINE:
                workline[keys.key_linepos + 1] = 0

        keys.key_linepos += 1

def Char_Event(ch):
    key = ord(ch) if isinstance(ch, str) else ch

    if key < 32 or key > 126:
        return

    if key in (ord('`'), ord('~')):    # console toggle keys are never typed
        return

    if keydown[Key.K_CTRL]:
        return

    if key_inputgrab.active:
        key_inputgrab.lastchar = key
        return

    match key_dest:
        case keydest_t.key_message:
            Char_Message(key)
        case keydest_t.key_menu:
            menu.M_Charinput(key)
        case keydest_t.key_game:
            pass
        case keydest_t.key_console:
            Char_Console(key)


def Key_WriteBindings(file_handle):
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
    global key_dest, _key_forced

    if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
        return

    match(key_dest):
        case keydest_t.key_console:
            if _key_forced and cl_main.cls.state == quakedef.cactive_t.ca_connected:
                _key_forced = False
                in_sdl.IN_Activate()
                key_dest = keydest_t.key_game
        case keydest_t.key_game:
            if cl_main.cls.state != quakedef.cactive_t.ca_connected:
                _key_forced = True
                in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
                key_dest = keydest_t.key_console

        case _:
            _key_forced = False


def Key_GetChatBuffer() -> str:
    return chat_buffer

def Key_GetChatMsgLen() -> int:
    return len(chat_buffer)

def Key_EndChat():
    global key_dest, chat_buffer
    key_dest = keydest_t.key_game
    chat_buffer = ''


def Key_Message(key: int):
    global chat_buffer

    if key in (Key.K_ENTER, Key.K_KP_ENTER):
        _cmd.Cbuf_AddText('say_team "' if chat_team else 'say "')
        _cmd.Cbuf_AddText(chat_buffer)
        _cmd.Cbuf_AddText('"\n')
        Key_EndChat()
    elif key == Key.K_ESCAPE:
        Key_EndChat()
    elif key == Key.K_BACKSPACE:
        chat_buffer = chat_buffer[:-1]

def Char_Message(key: int):
    global chat_buffer

    if len(chat_buffer) >= MAXCMDLINE - 1:
        return
    chat_buffer += chr(key)
