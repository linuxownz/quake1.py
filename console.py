#console.py

import sys
from datetime import datetime
from enum import Enum

import cvar
import _cmd
import host
import keys
import cl_main
import client
import common
import gl_draw
import gl_vidsdl
import cvar


# class keydest_t(Enum):
#     key_game    = 0
#     key_console = 1
#     key_message = 2
#     key_menu    = 3

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
CON_SPEED = 12

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

def Con_Printf(text):
    global con_text
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


def Con_MessageMode_f():
    global key_dest

    if cl_main.cls.state != client.cactive_t.ca_connected or cl_main.cls.demoplayback:
        return

    keys.chat_team = False
    key_dest = keys.keydest_t.key_message

def Con_MessageMode2_f():
    global key_dest

    if cl_main.cls.state != client.cactive_t.ca_connected or cl_main.cls.demoplayback:
        return

    keys.chat_team = True
    key_dest = keys.keydest_t.key_message

def Con_Clear_f():
    global con_text
    if con_text is not None:
        con_text[:] = b' ' * (con_totallines * 80)

def Con_Dump_f():
    file = f'{common.com_gamedir}/condump.txt'
    try:
        with open(file, 'wt') as f:
            for line in con_text:
                f.write(line, '\n')
        Con_Printf(f'Dumped console text to {file}')
    except:
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

def Con_DrawConsole():
    global con_text, con_displaylines, con_totallines, con_input_buffer

    if con_displaylines <= 0 or con_text is None:
        return

    # 1. Background (Slides down from top)
    gl_draw.Draw_Fill(0, 0, 640, con_displaylines, 200)

    # 2. Draw History
    # We want the text to "stick" to the bottom of the sliding console
    for i in range(25):
        line_index = (con_totallines - 25 + i)
        start = line_index * 80
        try:
            line_data = con_text[start:start+80].decode('ascii', 'replace')
        except:
            continue

        # Calculate Y relative to the current bottom (con_displaylines)
        # Newest history line is 16px above the prompt
        text_y = (con_displaylines - 24) - ((24 - i) * 8)

        if text_y >= 0:
            gl_draw.Draw_String(8, text_y, line_data)


    # 3. Draw Prompt & Input Buffer
    prompt_y = con_displaylines - 8

    # print(f"Debug: Buffer is '{con_input_buffer}' at Y: {prompt_y}")

    if prompt_y >= 0:
        # Draw the prompt symbol ']' followed by your typed buffer
        full_input_line = "]" + con_input_buffer
        gl_draw.Draw_String(8, prompt_y, full_input_line)

        # Draw the blinking cursor at the end of the text
        # Logic: 8 pixels per character (prompt + buffer length)
        cursor_x = 8 + (len(full_input_line)) * 8

        # Simple blink based on system time
        if int(host.realtime * 2) % 2 == 0:
            gl_draw.Draw_Character(cursor_x, prompt_y, 11) # 11 is the Quake cursor


def Con_CheckResize():
    global con_displaylines, console_is_open

    target = 200 if console_is_open else 0

    if con_displaylines < target:
        con_displaylines += CON_SPEED
        if con_displaylines > target:
            con_displaylines = target
    elif con_displaylines > target:
        con_displaylines -= CON_SPEED
        if con_displaylines < target:
            con_displaylines = target