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

MAX_ALIAS_NAME = 32
CMDLINE_LENGTH = 256
MAX_ARGS       = 80

cmd_argc = 0
cmd_argv : list[str] = []
cmd_null_string = ''
cmd_args = ''

class cmdalias_t:
    def __init__(self, name, value, next):
        self.name = name
        self.value = value
        self.next = next

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
    cmd_text.__init__()

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
    # Assuming cmdline is a Cvar object with a .string attribute
    cmdline_str = cvar.Cvar_GetCvar('cmdline').string
    cmds = []
    plus = False

    for i, char in enumerate(cmdline_str):
        if char == '+':
            plus = True
            if len(cmds) > 0:
                # Replace trailing space with ';' and add a space back
                cmds[-1] = ';'
                cmds.append(' ')
        elif char == '-' and (i == 0 or cmdline_str[i - 1] == ' '):
            # Non-+ flag encountered; stop accumulating
            plus = False
        elif plus:
            cmds.append(char)

    # Join character array and push into the front of the command buffer
    cmds_str = "".join(cmds)
    Cbuf_InsertText(cmds_str)



def Cmd_Exec_f():
    # We expect one argument: the filename
    if Cmd_Argc() != 2:
        console.Con_Printf("exec <filename> : execute a script file\n")
        return

    filename = Cmd_Argv(1)

    # Load from the Virtual File System in common.py
    # This will check id1/, then pak0.pak, etc.
    data = common.COM_LoadFile(filename)

    if data is None:
        console.Con_Printf(f"couldn't execute {filename}\n")
        return

    console.Con_Printf(f"executing {filename}\n")

    # Ensure the data is a string before inserting
    try:
        if isinstance(data, bytes):
            text = data.decode('utf-8')
        else:
            text = str(data)

        Cbuf_InsertText(text)
    except Exception as e:
        console.Con_Printf(f"Error executing {filename}: {e}\n")


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

    # Clear previous args (replacing Z_Free loop & reset)
    cmd_argv.clear()
    cmd_argc = 0
    cmd_args = None

    idx = 0
    length = len(text)

    while True:
        # Skip leading whitespace up to a newline
        while idx < length and text[idx] <= ' ' and text[idx] != '\n':
            idx += 1

        if idx < length and text[idx] == '\n':
            # Stop tokenizing at newline (end of current command)
            break

        if idx >= length:
            return

        # Set raw arguments pointer tail starting at cmd_argv[1]
        if cmd_argc == 1:
            cmd_args = text[idx:]

        # Extract token using engine string tokenizer
        token, next_idx = common.COM_Parse(text, idx)
        if token is None:
            return

        idx = next_idx

        # Append token up to MAX_ARGS ceiling
        if cmd_argc < MAX_ARGS:
            cmd_argv.append(token)
            cmd_argc += 1

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

    # Process commands while the buffer has data
    while cmd_text.cursize > 0:
        # Convert buffer slice to string for scanning (assuming ASCII/UTF-8 encoding)
        text_str = cmd_text.data[:cmd_text.cursize].decode('ascii', errors='ignore')

        quotes = 0
        split_idx = len(text_str)

        # Scan for newline or unquoted semicolon
        for i, char in enumerate(text_str):
            if char == '"':
                quotes += 1
            if not (quotes & 1) and char == ';':
                split_idx = i
                break
            if char == '\n':
                split_idx = i
                break

        # Extract command line (truncate to 1023 chars max to mirror C buffer ceiling)
        line = text_str[:min(split_idx, 1023)]

        # Shift remaining buffer forward (C's memmove equivalent)
        if split_idx == cmd_text.cursize:
            cmd_text.cursize = 0
            cmd_text.data.clear()
        else:
            consume_bytes = split_idx + 1  # Include the separator character
            cmd_text.data = cmd_text.data[consume_bytes:]
            cmd_text.cursize -= consume_bytes

        # Execute single command
        Cmd_ExecuteString(line, src_command)

        # Handle frame delay flag ('wait' command)
        if cmd_wait:
            cmd_wait = False
            break

def Cmd_ExecuteString(text: str, src: _cmd.cmd_source_t):
    import cvar
    global cmd_argv, cmd_argc
    global cmd_source

    cmd_source = src

    try:
        # posix=False treats backslashes as literal characters
        lexer = shlex.shlex(text, posix=False)
        lexer.whitespace_split = True
        lexer.commenters = ""
        # Manually strip quotes from the resulting tokens
        cmd_argv = [token.strip('"') for token in lexer]
    except Exception:
        cmd_argv = text.split()

    cmd_argc = len(cmd_argv)

    if not cmd_argv:
        assert(cmd_argc == 0)
        return

    cmd_argc = len(cmd_argv)
    cmd_name = cmd_argv[0].lower()

    # 1. Check registered commands (like 'echo', 'exec', etc)
    for cmd_func in cmd_functions:
        if cmd_name == cmd_func.name:
            cmd_func.function()
            return

    # 2. Check CVars (like 'sensitivity')
    if cvar.Cvar_Command(cmd_argv):
        return

    # 3. SILENCE THE IMPULSE COMMANDS
    # If it starts with + or -, it's handled by the move system,
    # not the command system. We just return so it doesn't log an error.
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
