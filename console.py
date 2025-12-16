#console.py 

import sys
from datetime import datetime
from enum import Enum

import cvar
import _cmd
import keys
import cl_main
import client
import common

class keydest_t(Enum):
    key_game    = 0
    key_console = 1
    key_message = 2
    key_menu    = 3

log_file = None

key_dest : keydest_t = keydest_t.key_console

con_linewidth = 38
con_cursorspeed = 4

con_buffersize = 0
con_forcedup = False

con_totallines = 0
con_backscroll = 0
con_current    = 0
con_x          = 0
con_text       = ''

con_lastcenterstring = ''

con_times : List[float] = []
con_vislines = 0
con_debuglog = False
con_initialized = False


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

def Con_Printf(msg):
    global con_debuglog

    print(msg)
    if con_debuglog:
        Con_DebugLog(msg) 

def Con_Warning(msg):
    print('Warning: ', msg)

def Con_DPrintf(msg):
    print(msg)

def Con_ToggleConsole_f():
    global key_dest
    global con_backscroll
    global con_times

    if key_dest == keys.keydest_t.key_console:
        keys.key_lines[keys.edit_line] = ''
        keys.key_linepos = 1
        con_backscroll = 0
        keys.history_line = keys.edit_line

        if cl_main.cls.state == client.cactive_t.ca_connected:
            IN_Activate()
            key_dest == keys.key_dest.key_game
        else:
            M_Menu_Main_f()
    else:
        IN_Deactivate(vid.modestate == vid.modestate_t.MS_WINDOWED)
        key_dest = keys.keydest_t.key_console
    
    SCR_EndLoadingPlaque()
    con_times = []

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
    global con_backscroll
    if con_text:
        con_text = ' ' * con_buffersize
    con_backscroll = 0

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

    con_linewidth = 38
    con_backscroll = 0
    con_totallines = 1000
    con_current = con_totallines - 1

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
