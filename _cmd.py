#cmd.py 
from __future__ import annotations
from enum import Enum

cmd_text = ''

cmd_functions : List[cmd_function] = []

class cmd_function:
    def __init__(self, name, function):
        self.name = name
        self.function = function

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