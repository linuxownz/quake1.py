#cmd.py
from __future__ import annotations

import shlex
from enum import Enum

import common
import console
import _cmd

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

cmd_text = ''

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
    cmd_text = ''

def Cmd_AddCommand(cmd_name, function):
    cmd_functions.append(cmd_function(cmd_name, function))

def Cmd_List_f():
    for cmd_func in cmd_functions:
        print(cmd_func.name)

def Cmd_Unalias_f():
    pass

def Cmd_Unaliasall_f():
    pass

def Cmd_StuffCmds_f():
    pass


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
        console.Con_Printf('%s ' % Cmd_Argv(i))
    #console.Con_Printf('\n')

def Cmd_Alias_f():
    pass

def Cmd_ForwardToServer_f():
    pass

def Cmd_Wait_f():
    pass

def Cmd_Apropos_f():
    pass

def Cmd_Exists(name):
    for cmd in cmd_functions:
        if cmd.name == name:
            return True
    return False

def Cmd_Init():
    Cmd_AddCommand('cmdlist', Cmd_List_f)
    Cmd_AddCommand('unalias', Cmd_Unalias_f)
    Cmd_AddCommand('unaliasall', Cmd_Unaliasall_f)
    Cmd_AddCommand('stuffcmds', Cmd_StuffCmds_f)
    Cmd_AddCommand('exec', Cmd_Exec_f)
    Cmd_AddCommand('echo', Cmd_Echo_f)
    Cmd_AddCommand('alias', Cmd_Alias_f)
    Cmd_AddCommand('cmd', Cmd_ForwardToServer_f)
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

def Cbuf_InsertText(text: str):
    global cmd_text
    # We prepend the new text to the front of the buffer.
    # This ensures 'exec' commands are processed before subsequent commands.
    if not text.endswith('\n'):
        text += '\n'
    cmd_text = text + cmd_text

def Cbuf_AddText(text: str):
    """
    Adds a command string to the end of the command buffer.
    """
    global cmd_text

    # Ensure we are adding a string
    if isinstance(text, bytes):
        text = text.decode('ascii', 'replace')

    # Python strings use += to append
    cmd_text += text

def Cbuf_Execute():
    global cmd_text
    if not cmd_text:
        return

    execute_stack = cmd_text
    cmd_text = ""

    for line in execute_stack.split('\n'):
        line = line.strip()
        if not line or line.startswith('//'):
            continue

        if '//' in line:
            line = line.split('//')[0].strip()

        try:
            # posix=False prevents shlex from eating backslashes as escape chars
            # This allows bind "\" "+mlook" to parse correctly
            lexer = shlex.shlex(line, posix=False)
            lexer.whitespace_split = True
            lexer.commenters = ""

            tokens = list(lexer)

            # Re-process tokens to handle semicolons and strip quotes manually
            current_cmd_tokens = []
            for token in tokens:
                # Manually strip quotes since posix=False leaves them on
                clean_token = token.strip('"')

                if clean_token == ';':
                    if current_cmd_tokens:
                        Cmd_ExecuteString(" ".join(current_cmd_tokens))
                        current_cmd_tokens = []
                else:
                    current_cmd_tokens.append(clean_token)

            if current_cmd_tokens:
                thecmd = " ".join(current_cmd_tokens)
                Cmd_ExecuteString(thecmd, cmd_source_t.src_command)

        except ValueError as e:
            console.Con_Printf(f"Config parse error on line [{line}]: {e}\n")


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
    if cmd_name.startswith('+') or cmd_name.startswith('-'):
        return

    console.Con_Printf(f"Unknown command: {cmd_name}\n")