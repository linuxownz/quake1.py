#cmd.py 
from __future__ import annotations
from enum import Enum

MAX_ALIAS_NAME = 32
CMDLINE_LENGTH = 256
MAX_ARGS       = 80

cmd_argc = 0
cmd_argv : list[str] = []
cmd_null_string = ''
cmd_args = ''

class cmdalias_t():
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

cmd_source = cmd_source_t.src_client

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
    pass

def Cmd_Echo_f():
    pass

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

def Cmd_Argc():
    return cmd_argc

def Cmd_Argv(arg) -> str:
    if arg < 0 or arg > cmd_argc:
        return ''
    return cmd_argv[arg]