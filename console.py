#console.py

import sys
from datetime import datetime

import OpenGL.GL as gl

import _cmd
import cl_main
import common
import cvar
import gl_draw
import gl_screen
import gl_vidsdl
import host
import in_sdl
import keys
import quakedef
import sys_sdl_unix
import vid

# class keydest_t(Enum):
#     key_game    = 0
#     key_console = 1
#     key_message = 2
#     key_menu    = 3

NUM_CON_TIMES = 4
log_file = None

# key_dest : keys.keydest_t = keys.keydest_t.key_console

con_linewidth = 38
con_cursorspeed = 4

con_buffersize = 0
con_forcedup = False

con_totallines = 0
con_columns    = 0
con_backscroll = 0
con_current    = 0
con_x          = 0
con_text       = None
con_input_buffer = ""

con_lastcenterstring = ''

con_times : list[float] = []
con_vislines = 0
con_debuglog = False
con_initialized = False

con_displaylines = 0    # This MUST match the name in Con_CheckResize
console_is_open = True  # SET TO TRUE so it slides down automatically on start
CON_SPEED = 24

def Con_Quakebar(length: int) -> str:
    if length < 1:
        return ""
    if length == 1:
        return "\x1d"
    if length == 2:
        return "\x1d\x1f"

    # \x1d (left cap), \x1e repeated for middle, \x1f (right cap)
    return "\x1d" + ("\x1e" * (length - 2)) + "\x1f"


def LOG_Init():
    global log_file
    global con_debuglog

    if '-condebug' in sys.argv:
        con_debuglog = True

    if not con_debuglog:
        return

    log_file = open('qconsole.log', 'w')
    Con_DebugLog('Initializing Log file\n')

def LOG_Close():
    if log_file != None:
        log_file.close();

def Con_DebugLog(msg):
    global log_file

    if not log_file:
        return

    now = datetime.now()
    log_file.write(now.strftime('%Y:%m:%d %H:%M:%S : '))
    log_file.write(msg + '\n')

def Con_Printf(text:str):
    global con_text

    text += '\n'

    if con_text is None:
        print('con_text is None\n')
        return

    cols = 80
    # Handle multiple lines if the text contains \n
    lines = text.split('\n')

    for line in lines:
        if line == "" and text.count('\n') == 0:
            continue

        # 1. Scroll: Move everything up by one line
        con_text[:-cols] = con_text[cols:]

        # 2. Clear the bottom line
        con_text[-cols:] = b' ' * cols

        # 3. Write the current line to the bottom
        last_line_start = (con_totallines - 1) * cols
        for i, char in enumerate(line[:cols-1]):
            con_text[last_line_start + i] = ord(char)

    print(text.strip())

def Con_Warning(msg):
    print('Warning: ', msg)

def Con_DPrintf(msg):
    if cvar.Cvar_GetCvar('developer').value:
        print(msg)

def Con_ToggleConsole_f():
    global console_is_open

    # Use the global state from keys.py
    if keys.key_dest == keys.keydest_t.key_console:
        # Close console
        keys.key_dest = keys.keydest_t.key_game
        console_is_open = False
    else:
        # Open console
        keys.key_dest = keys.keydest_t.key_console
        console_is_open = True

def Con_CenterPrintf(linewidth: int, fmt: str, *args) -> None:
    """
    Formats a message, splits it into lines, centers each line relative to linewidth
    (bounded by con_linewidth), and prints to the console.
    """
    # 1. Handle C-style string formatting via variadic *args
    msg = fmt % args if args else fmt

    # 2. Bound linewidth to global console width (matches q_min(linewidth, con_linewidth))
    effective_width = min(linewidth, con_linewidth)

    # 3. Process and print line by line
    for line in msg.split('\n'):
        line_len = len(line)

        if line_len < effective_width:
            padding = (effective_width - line_len) // 2
            spaces = ' ' * padding
            Con_Printf(f"{spaces}{line}\n")
        else:
            Con_Printf(f"{line}\n")


def Con_LogCenterPrint(s: str):
    global con_lastcenterstring
    if s == con_lastcenterstring:
        return

    con_logcenterprint = cvar.Cvar_GetCvar('con_logcenterprint').value

    if cl_main.cl.gametype == protocol.GAME_DEATHMATCH and con_logcenterprint != 2:
        return

    con_lastcenterstring = s

    if con_logcenterprint:
        Con_Printf(Con_Quakebar(40))
        Con_CenterPrintf(40, '%s\n', s)
        Con_Printf(Con_Quakebar(40))
        Con_ClearNotify()


def Con_MessageMode_f():
    global key_dest

    if cl_main.cls.state != quakedef.cactive_t.ca_connected or cl_main.cls.demoplayback:
        return

    keys.chat_team = False
    key_dest = keys.keydest_t.key_message

def Con_MessageMode2_f():
    global key_dest

    if cl_main.cls.state != quakedef.cactive_t.ca_connected or cl_main.cls.demoplayback:
        return

    keys.chat_team = True
    key_dest = keys.keydest_t.key_message

def Con_Clear_f():
    global con_backscroll, con_text
    if con_text is not None:
        con_text[:] = b' ' * (con_totallines * 80)
    con_backscroll = 0

def Con_ClearNotify():
    global con_times
    con_times = []

def Con_Dump_f():
    file = f'{common.com_gamedir}/condump.txt'
    try:
        with open(file, 'wt') as f:
            for line in con_text:
                f.write(line, '\n')
        Con_Printf(f'Dumped console text to {file}')
    except OSError:
        Con_Printf(f'failed to open {file} for writing in Con_Dump_f')
        return


def Con_Init():
    ''' -consize ignored '''

    global con_initialized
    global con_linewidth
    global con_backscroll
    global con_current
    global con_totallines
    global con_text

    con_linewidth = 38
    con_columns =   80
    con_backscroll = 0
    con_totallines = 1000


    # Fill the buffer with spaces (ASCII 32) so it looks empty
    con_text = bytearray([32] * (con_totallines * con_columns))

    _cmd.Cmd_AddCommand('toggleconsole', Con_ToggleConsole_f)
    _cmd.Cmd_AddCommand('messagemode', Con_MessageMode_f)
    _cmd.Cmd_AddCommand('messagemode2', Con_MessageMode2_f)
    _cmd.Cmd_AddCommand('clear', Con_Clear_f)
    _cmd.Cmd_AddCommand('condump', Con_Dump_f)

    Con_Printf('Console Initialized\n')

    con_notifytime     = {'name': 'con_notifytime',     'value':'3', 'flags':cvar.CVAR_NONE}
    con_logcenterprint = {'name': 'con_logcenterprint', 'value':'1', 'flags':cvar.CVAR_NONE}

    cvar.Cvar_RegisterVariable(con_notifytime)
    cvar.Cvar_RegisterVariable(con_logcenterprint)

    con_initialized = True

def Con_Linefeed():
    global con_backscroll, con_x, con_current, con_text

    if con_backscroll:
        con_backscroll += 1
    con_backscroll = min(con_backscroll, con_totallines - ( gl_screen.glheight >> 3 ) - 1)

    con_x = 0
    con_current += 1

    con_text[con_current % con_totallines] = ' ' * con_linewidth


def Con_DrawNotify():
    gl_draw.GL_SetCanvas(screen.canvastype.CANVAS_CONSOLE)
    v = gl_vidsdl._vid.conheight

    text:str = ''

    for i in range( con_current - NUM_CON_TIMES + 1, con_current + 1):
        if i < 0:
            continue

        time = con_times[i % NUM_CON_TIMES]
        if time == 0:
            continue

        time = host.realtime - time
        if time > cvar.Cvar_GetCvar('con_notifytime').value:
            continue

        offset = (i % con_totallines) * con_linewidth

        text = con_text[offset : offset + con_linewidth]

        gl_screen.clearnotify = 0

        for x in range(con_linewidth):
            gl_draw.Draw_Character( ( x + 1 ) << 3, v, text[x])

        v += 8

        gl_screen.scr_tileclear_updates = 0

    if keys.key_dest == keys.keydest_t.key_message:
        gl_screen.clearnotify = 0

        if keys.chat_team:
            gl_draw.Draw_String(8, v, 'say_team:')
            x = 11
        else:
            gl_draw.Draw_String(8, v, 'say:')
            x = 6

        text = keys.Key_GetChatBuffer()
        i = keys.Key_GetChatMsgLen()

        if i > con_linewidth - x - 1:
            text += i - con_linewidth + x + 1

        for char in text:
            gl_draw.Draw_Character(x << 3, v, char)
            x += 1

        gl_draw.Draw_Character(x << 3, v, 10 + ( host.realtime * con_cursorspeed & 1))

        v += 8

        gl_screen.scr_tileclear_updates = 0

def Con_DrawInput() -> None:
    if keys.key_dest != keys.keydest_t.key_console and not con_forcedup:
        return

    edit_str = keys.key_lines[keys.edit_line]
    str_len = len(edit_str)

    max_visible = con_linewidth - 2
    if keys.key_linepos >= max_visible:
        ofs = 1 + keys.key_linepos - max_visible
    else:
        ofs = 0

    y_pos = gl_vidsdl._vid.conheight - 16

    gl_draw.Draw_Character(0, y_pos, 11)

    i = 0
    while (i + ofs) < str_len and i < max_visible:
        char_val = edit_str[i + ofs]
        char_code = ord(char_val) if isinstance(char_val, str) else char_val
        gl_draw.Draw_Character((i + 1) << 3, y_pos, char_code)
        i += 1

    if int((host.realtime - keys.key_blinktime) * con_cursorspeed) & 1:
        cursor_x = (keys.key_linepos - ofs + 1) << 3
        pic = gl_draw.pic_ins if keys.key_insert else gl_draw.pic_ovr
        gl_draw.Draw_Pic(cursor_x, y_pos, pic)

def Con_DrawConsole():
    raise Exception('differs from original source, needs to  take two arguments')
    global con_text, con_displaylines, con_totallines, con_input_buffer, con_backscroll

    if con_displaylines <= 0 or con_text is None:
        return

    # 1. Setup Scaling
    scr_width = gl_vidsdl._vid.width
    scr_height = gl_vidsdl._vid.height
    ui_scale = scr_width / 640.0
    line_height = 8 * ui_scale
    char_width = 8 * ui_scale

    # 2. SCISSOR TEST
    # OpenGL Scissor starts from BOTTOM-LEFT.
    # This prevents text from drawing below the moving console background.
    gl.glEnable(gl.GL_SCISSOR_TEST)
    gl.glScissor(0, int(scr_height - con_displaylines), int(scr_width), int(con_displaylines))

    # 3. Background (Slides down)
    gl_draw.Draw_Fill(0, 0, scr_width, con_displaylines, 200)

    # 4. Draw History (Stationary relative to top)
    # Calculate how many lines fit in the target height (400)
    max_vis_lines = int(400 // line_height) - 1

    for i in range(max_vis_lines):
        # Apply backscroll here for your PageUp/PageDown logic
        line_index = (con_totallines - max_vis_lines - con_backscroll + i)
        if line_index < 0: continue

        start = line_index * 80
        try:
            line_data = con_text[start:start+80].decode('ascii', 'replace')
        except: continue

        # FIXED Y: The text is always drawn from Y=0 downwards
        # It doesn't move when con_displaylines changes!
        text_y = i * line_height

        gl_draw.Draw_String(char_width, text_y, line_data, scale=ui_scale)

    # 5. Draw Prompt (Moves with the bottom edge)
    prompt_y = con_displaylines - line_height
    if prompt_y >= 0:
        full_input_line = "]" + con_input_buffer
        gl_draw.Draw_String(char_width, prompt_y, full_input_line, scale=ui_scale)

        cursor_x = char_width + (len(full_input_line)) * char_width
        if int(host.realtime * 2) % 2 == 0:
            gl_draw.Draw_Character(cursor_x, prompt_y, 11, scale=ui_scale)

    gl.glDisable(gl.GL_SCISSOR_TEST)

def Con_NotifyBox(text: str):
    Con_Printf(f'\n\n{Con_Quakebar(40)}')
    Con_Printf(text)
    Con_Printf('Press a key\n')
    Con_Printf(Con_Quakebar(40))

    in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_console

    keys.Key_BeginInputGrag()

    while True:
        t1 = sys_sdl_unix.Sys_DoubleTime()
        gl_screen.SCR_UpdateScreen()
        sys_sdl_unix.Sys_SendKeyEvents()
        lastkey, lastchar = keys.Key_GetGrabbedInput()
        sys_sdl_unix.Sys_Sleep(16)
        t2 = sys_sdl_unix.Sys_DoubleTime()
        host.realtime += t2 - t1

        if lastkey == -1 and lastchar == -1:
            break

    keys.Key_EndInputGrag()
    Con_Printf('\n')
    in_sdl.IN_Activate()
    keys.key_dest = keys.keydest_t.key_game
    host.realtime = 0


def Con_CheckResize() -> None:
    global con_displaylines

    # 1. Target height is half the screen height when open, 0 when closed
    # (Matches Quake default: vid.height >> 1 or scaled by scr_conscale)
    target = (gl_vidsdl._vid.height >> 1) if keys.key_dest == keys.keydest_t.key_console else 0

    # 2. Scale animation speed by frame delta time for frame-rate independence
    # Standard Quake CON_SPEED is around 300-500 pixels per second
    speed = CON_SPEED * host.host_frametime

    # 3. Animate console height toward target
    if con_displaylines < target:
        con_displaylines += speed
        if con_displaylines > target:
            con_displaylines = float(target)
    elif con_displaylines > target:
        con_displaylines -= speed
        if con_displaylines < target:
            con_displaylines = float(target)
