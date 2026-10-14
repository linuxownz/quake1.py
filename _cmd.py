#cmd.py
from __future__ import annotations

import shlex
from enum import Enum

import _cmd
import cl_main
import common
import console
import cvar
import protocol
import quakedef
import sys_sdl_unix
import zone

MAX_ALIAS_NAME = 32
CMDLINE_LENGTH = 256
MAX_ARGS       = 80

cmd_argc = 0
cmd_argv : list[str] = []
cmd_null_string = ''
cmd_args = ''

class cmdalias_t:
    def __init__(self, name = '', value = 0, _next = None):
        self.name  = name
        self.value = value
        self.next  = _next

cmd_alias : cmdalias_t = None

cmd_wait = False

cmd_text: common.sizebuf_s = common.sizebuf_s()

cmd_functions : list[cmd_function] = []

class cmd_function:
    def __init__(self, name, function): #, next):
        self.name = name
        self.function = function
        # self.next = next # why did I add this?

class cmd_source_t(Enum):
    src_client = 0
    src_command = 1

cmd_source: cmd_source_t = None

def Cbuf_Init():
    global cmd_text
    cmd_text = common.sizebuf_s()
    cmd_text.allowoverflow = False
    cmd_text.cursize = 0
    cmd_text.data = bytearray()
    cmd_text.maxsize = 1 << 18
    cmd_text.overflowed = False

def Cmd_AddCommand(cmd_name, function):
    cmd_functions.append(cmd_function(cmd_name, function))

def Cmd_List_f():
    for cmd_func in cmd_functions:
        print(cmd_func.name)


def Cmd_TintSubstring(in_str: str, substr: str) -> str:
    if not substr or not in_str:
        return in_str

    out_bytes = bytearray(in_str.encode('ascii', errors='ignore'))
    substr_lower = substr.lower()
    in_lower = in_str.lower()

    sub_len = len(substr)
    start_idx = 0

    # Search for occurrences case-insensitively
    while True:
        idx = in_lower.find(substr_lower, start_idx)
        if idx == -1:
            break

        # Set high bit (0x80) for printable ASCII characters
        for i in range(idx, idx + sub_len):
            char_code = out_bytes[i]
            if 32 <= char_code < 127:
                out_bytes[i] |= 0x80

        start_idx = idx + sub_len

    return out_bytes.decode('latin-1')


def Cmd_Apropos_f() -> None:
    hits: int = 0
    substr: str = Cmd_Argv(1)

    if not substr:
        console.Con_Printf(f'{Cmd_Argv(0)} <substring> : search through commands and cvars for the given substring\n')
        return

    # 1. Search through registered engine commands
    for cmd in cmd_functions:
        if substr.lower() in cmd.name.lower():
            hits += 1
            highlighted = Cmd_TintSubstring(cmd.name, substr)
            console.Con_Printf(f'    {highlighted}\n')

    # 2. Search through cvar linked list
    var = cvar.Cvar_FindVarAfter('', 0)
    while var is not None:
        if substr.lower() in var.name.lower():
            hits += 1
            highlighted = Cmd_TintSubstring(var.name, substr)
            console.Con_Printf(f'    {highlighted} is "{var.string}"\n')
        var = var.next

    if hits == 0:
        console.Con_Printf('no cvar or commands contain that substring\n')



def Cmd_Unalias_f():
    global cmd_alias

    a: cmdalias_t = None
    prev: cmdalias_t = None

    argc = Cmd_Argc()

    if argc == 0 or argc == 1:
        console.Con_Printf('unalias <name> : delete alias')
    elif argc == 2:
        prev = None
        a = cmd_alias

        while a is not None:
            if Cmd_Argv(1) ==  a.name:
                if prev is not None:
                    prev.next = a.next
                else:
                    cmd_alias = a.next

                a.value = ''
                return

            prev = a
            a = a.next



def Cmd_Unaliasall_f():
    global cmd_alias
    cmd_alias = None





def Cmd_StuffCmds_f() -> None:
    cvar_obj = cvar.Cvar_GetCvar('cmdline')
    if not cvar_obj or not cvar_obj.string:
        return

    cmdline_str = cvar_obj.string
    cmds = []
    plus = False

    for i, char in enumerate(cmdline_str):
        if char == '+':
            plus = True
            if len(cmds) > 0:
                cmds[-1] = ';'
                cmds.append(' ')
        elif char == '-' and (i == 0 or cmdline_str[i - 1] == ' '):
            plus = False
        elif plus:
            cmds.append(char)

    cmds_str = "".join(cmds)
    if cmds_str.strip():
        Cbuf_InsertText(cmds_str)


default_cfg = """
unbindall

bind ALT +strafe
bind , +moveleft
bind a +moveleft
bind . +moveright
bind d +moveright
bind DEL +lookdown
bind PGDN +lookup
bind END centerview
bind e +moveup
bind c +movedown
bind SHIFT +speed
bind CTRL +attack
bind UPARROW +forward
bind w +forward
bind DOWNARROW +back
bind s +back
bind LEFTARROW +left
bind RIGHTARROW +right
bind SPACE +jump
bind TAB +showscores
bind 1 "impulse 1"
bind 2 "impulse 2"
bind 3 "impulse 3"
bind 4 "impulse 4"
bind 5 "impulse 5"
bind 6 "impulse 6"
bind 7 "impulse 7"
bind 8 "impulse 8"

bind 0 "impulse 0"

bind / "impulse 10"
bind MWHEELDOWN "impulse 10"
bind MWHEELUP "impulse 12"

alias zoom_in "sensitivity 2;fov 90;wait;fov 70;wait;fov 50;wait;fov 30;wait;fov 10;wait;fov 5;bind F11 zoom_out"
alias zoom_out "sensitivity 4;fov 5;wait;fov 10;wait;fov 30;wait;fov 50;wait;fov 70;wait;fov 90;bind F11 zoom_in; sensitivity 3"
bind F11 zoom_in

bind F1 "help"
bind F2 "menu_save"
bind F3 "menu_load"
bind F4 "menu_options"
bind F5 "menu_multiplayer"
bind F6 "echo Quicksaving...; wait; save quick"
bind F9 "echo Quickloading...; wait; load quick"
bind F10 "quit"
bind F12 "screenshot"

bind \\ +mlook

bind PAUSE "pause"
bind ESCAPE "togglemenu"
bind ~ "toggleconsole"
bind ` "toggleconsole"

bind t "messagemode"

bind + "sizeup"
bind = "sizeup"
bind - "sizedown"

bind INS +klook

bind MOUSE1 +attack
bind MOUSE2 +jump

bind LSHOULDER "impulse 12"
bind RSHOULDER "impulse 10"
bind LTRIGGER +jump
bind RTRIGGER +attack

gamma 1.0
volume 0.7
sensitivity 3

viewsize 110
scr_conscale 1.6
scr_menuscale 1.6
scr_sbarscale 1.6

+mlook
"""

def Cmd_Exec_f():
    # We expect one argument: the filename
    if Cmd_Argc() != 2:
        console.Con_Printf("exec <filename> : execute a script file\n")
        return

    filename = Cmd_Argv(1)

    mark = zone.Hunk_LowMark()
    data = common.COM_LoadHunkFile(filename, False)

    if data is None:
        if filename == 'default.cfg':
            data = default_cfg
        else:
            console.Con_Printf(f"couldn't execute {filename}\n")
        return

    console.Con_Printf(f"executing {filename}\n")

    # Ensure the data is a string before inserting
    try:
        if isinstance(data, bytes):
            text = data.decode('utf-8')
        elif isinstance(data, memoryview):
            text = data.tobytes().decode('utf-8')
        else:
            text = data.decode('latin-1')

        Cbuf_InsertText(text)
    except Exception as e:
        console.Con_Printf(f"Error executing {filename}: {e}\n")

    if data == default_cfg:
        zone.Hunk_FreeToLowMark(mark)


def Cmd_Echo_f():
    for i in range (1, Cmd_Argc()):
        console.Con_Printf(f'{Cmd_Argv(i)} ')
    #console.Con_Printf('\n')

def Cmd_Alias_f() -> None:
    global cmd_alias

    a: cmdalias_t | None = None
    i: int = 0

    match Cmd_Argc():
        case 1:
            a = cmd_alias
            while a is not None:
                console.Con_Printf(f'   {a.name}: {a.value}')
                a = a.next
                i += 1

            if i:
                console.Con_Printf(f'{i} alias command(s)\n')
            else:
                console.Con_Printf('no alias commands found\n')

        case 2:
            a = cmd_alias
            while a is not None:
                if Cmd_Argv(1) == a.name:
                    console.Con_Printf(f'   {a.name}: {a.value}')
                    return
                a = a.next

        case _:
            s: str = Cmd_Argv(1)

            # 1. Search for existing alias
            a = cmd_alias
            while a is not None:
                if s == a.name:
                    break
                a = a.next

            # 2. Instantiate new alias if not found
            if a is None:
                a = cmdalias_t()
                a.next = cmd_alias
                cmd_alias = a
                a.name = s

            # 3. Concatenate arguments with spaces
            cmd_parts = []
            c = Cmd_Argc()
            for i in range(2, c):
                cmd_parts.append(Cmd_Argv(i))

            a.value = " ".join(cmd_parts) + "\n"


def Cmd_ForwardToServer() -> None:
    # 1. Ensure client is connected to a server
    if cl_main.cls.state != quakedef.cactive_t.ca_connected:
        console.Con_Printf(f'Can\'t "{Cmd_Argv(0)}", not connected\n')
        return

    # 2. Don't forward commands during demo playback
    if cl_main.cls.demoplayback:
        return

    # 3. Write client-to-server command packet opcode
    common.MSG_WriteByte(cl_main.cls.message, protocol.clc_stringcmd)

    # 4. Handle "cmd" alias prefix forwarding vs direct command forwarding
    if Cmd_Argv(0).lower() == 'cmd':
        common.SZ_Print(cl_main.cls.message, Cmd_Args())
    else:
        # If calling a server command directly (e.g. "kill" or "god")
        common.SZ_Print(cl_main.cls.message, Cmd_Argv(0))
        if Cmd_Argc() > 1:
            common.SZ_Print(cl_main.cls.message, ' ')
            common.SZ_Print(cl_main.cls.message, Cmd_Args())

    # 5. Append trailing newline character required by Quake server string parser
    common.SZ_Print(cl_main.cls.message, '\n')




def Cmd_Wait_f():
    global cmd_wait
    cmd_wait = True

def Cmd_Apropos_f():
    pass

def Cmd_Exists(name):
    for cmd in cmd_functions:
        if cmd.name == name:
            return True
    return False

def Cmd_CompleteCommand(partial: str) -> str:
    for cmd in cmd_functions:
        if partial in cmd.name:
            return cmd.name

    return None

def Cmd_Init():
    Cmd_AddCommand('cmdlist', Cmd_List_f)
    Cmd_AddCommand('unalias', Cmd_Unalias_f)
    Cmd_AddCommand('unaliasall', Cmd_Unaliasall_f)
    Cmd_AddCommand('stuffcmds', Cmd_StuffCmds_f)
    Cmd_AddCommand('exec', Cmd_Exec_f)
    Cmd_AddCommand('echo', Cmd_Echo_f)
    Cmd_AddCommand('alias', Cmd_Alias_f)
    Cmd_AddCommand('cmd', Cmd_ForwardToServer)
    Cmd_AddCommand('wait', Cmd_Wait_f)
    Cmd_AddCommand('apropos', Cmd_Apropos_f)
    Cmd_AddCommand('find', Cmd_Apropos_f)

    Cmd_List_f()

def Cmd_Argc() -> int:
    return cmd_argc

def Cmd_Argv(arg) -> str:
    # Use >= to ensure we don't go out of bounds of the list
    if arg < 0 or arg >= cmd_argc:
        return ''
    return cmd_argv[arg]


def Cmd_Args() -> str:
    """Returns the entire command line string excluding the command name."""
    if cmd_argc <= 1:
        return ""

    # This finds the first space after the command name and returns everything after it
    # This preserves multiple spaces and quotes better than joining a split list
    return " ".join(cmd_argv[1:])


def Cmd_TokenizeString(text: str) -> None:
    global cmd_argc, cmd_argv, cmd_args

    cmd_argv.clear()
    cmd_argc = 0
    cmd_args = ""

    if not text:
        return

    remaining = text
    while remaining:
        # COM_Parse updates common.com_token and returns the remaining data string
        remaining = common.COM_Parse(remaining)

        # Read the parsed word out of common.com_token
        token = common.com_token
        if token and cmd_argc < MAX_ARGS:
            cmd_argv.append(token)
            cmd_argc += 1

    # Populate cmd_args (everything after the command name)
    if cmd_argc > 1:
        cmd_args = " ".join(cmd_argv[1:])

def Cbuf_InsertText(text: str):
    # Save remaining unexecuted buffer data
    temp = cmd_text.data[:cmd_text.cursize]

    # Clear the buffer
    cmd_text.data.clear()
    cmd_text.cursize = 0

    # Insert new text + newline
    Cbuf_AddText(text)
    Cbuf_AddText("\n")

    # Append the old data back
    if temp:
        cmd_text.data.extend(temp)
        cmd_text.cursize += len(temp)

def Cbuf_AddText(text: str):
    length = len(text)

    # Check for buffer overflow
    if cmd_text.cursize + length >= cmd_text.maxsize:
        print("Cbuf_AddText: overflow")
        return

    # SZ_Write equivalent: append bytes/text to the dynamic buffer
    cmd_text.data += text.encode('ascii')  # or cmd_text.data.extend(text.encode())
    cmd_text.cursize += length

def Cbuf_Execute():
    global cmd_wait

    while cmd_text.cursize > 0:
        # Decode current byte array to string
        text_str = cmd_text.data[:cmd_text.cursize].decode('latin-1', errors='ignore')

        quotes = 0
        split_idx = len(text_str)

        # Scan for newline or unquoted semicolon
        for i, char in enumerate(text_str):
            if char == '"':
                quotes += 1
            elif not (quotes & 1) and char == ';':  # noqa: SIM114
                split_idx = i
                break
            elif char == '\r' or char == '\n':
                split_idx = i
                break

        # Extract the command slice
        raw_line = text_str[:split_idx]

        # Calculate bytes to consume including the trailing delimiter (\r, \n, or ;)
        consume_bytes = split_idx
        if split_idx < len(text_str):
            consume_bytes += 1
            # Handle \r\n pair in one pass if present
            if text_str[split_idx] == '\r' and split_idx + 1 < len(text_str) and text_str[split_idx + 1] == '\n':
                consume_bytes += 1

        # Shift remaining buffer forward
        cmd_text.data = cmd_text.data[consume_bytes:]
        cmd_text.cursize -= consume_bytes

        # Strip whitespace/newlines and skip empty lines or line comments
        line = raw_line.strip()
        if not line or line.startswith('//'):
            continue

        if line == '/':
            pass
            #breakpoint()

        print(f'executing {line}')

        # Execute single command
        Cmd_ExecuteString(line, cmd_source_t.src_command)

        # Handle frame delay flag ('wait' command)
        if cmd_wait:
            cmd_wait = False
            break

def Cmd_ExecuteString(text: str, src: cmd_source_t):
    global cmd_argv, cmd_argc, cmd_source

    cmd_source = src

    # Tokenize the whole line into cmd_argv
    Cmd_TokenizeString(text)

    if cmd_argc == 0:
        return

    # ONLY look at the first token (the command name)
    cmd_name = cmd_argv[0].lower()

    if cmd_name.startswith('//'):
        return

    # 1. Check registered functions
    for cmd_func in cmd_functions:
        if cmd_name == cmd_func.name:
            cmd_func.function()  # Call handler (e.g. Cmd_Exec_f or Host_Map_f)
            return               # STOP! Do not process remaining tokens as commands!

    # 2. Check CVars
    if cvar.Cvar_Command(cmd_argv):
        return

    # 3. Check Aliases
    a = cmd_alias
    while a is not None:
        if cmd_name == a.name.lower():
            Cbuf_InsertText(a.value)
            return
        a = a.next

    # 4. Movement keys
    if cmd_name.startswith(('+', '-')):
        return

    console.Con_Printf(f"Unknown command: {cmd_name}\n")


def Cmd_CheckParm(parm: str):
    if not parm:
        sys_sdl_unix.Sys_Error('Cmd_CheckParm: null input')

    for i in range(Cmd_Argc()):
        if parm.lower() == Cmd_Argv(1):
            return i
    return 0
