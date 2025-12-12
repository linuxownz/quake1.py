#cvar.py 

import _cmd

__cvars: List[cvar_t] = []

CVAR_NONE       = 0
CVAR_ARCHIVE    = 1 << 0
CVAR_NOTIFY     = 1 << 1
CVAR_SERVERINFO = 1 << 2 
CVAR_USERINFO   = 1 << 3
CVAR_CHANGED    = 1 << 4
CVAR_ROM        = 1 << 6
CVAR_LOCKED     = 1 << 8
CVAR_REGISTERED = 1 << 10
CVAR_CALLBACK   = 1 << 16

class cvar_t():
    def __init__(self, name, string, flags, value, default_string, callback):
        self.name = name
        self.string = string
        self.flags = flags
        self.value = value
        self.default_string = default_string
        self.callback = callback


def Cvar_List_f():
    for cvar in __cvars:
        print(cvar.name, cvar.string, cvar.flags, cvar.value, cvar.default_string)


def Cvar_Toggle_f():
    pass

def Cvar_Cycle_f():
    pass

def Cvar_Inc_f():
    pass

def Cvar_Reset_f():
    pass

def Cvar_ResetAll_f():
    pass

def Cvar_ResetCfg_f():
    pass

def Cvar_Init():
    _cmd.Cmd_AddCommand('cvar_list', Cvar_List_f)
    _cmd.Cmd_AddCommand('toggle', Cvar_Toggle_f)
    _cmd.Cmd_AddCommand('cycle', Cvar_Cycle_f)
    _cmd.Cmd_AddCommand('inc', Cvar_Inc_f)
    _cmd.Cmd_AddCommand('reset', Cvar_Reset_f)
    _cmd.Cmd_AddCommand('resetall', Cvar_ResetAll_f)
    _cmd.Cmd_AddCommand('resetcfg', Cvar_ResetCfg_f)


def Cvar_FindVar(name) -> cvar_t:
    for var in __cvars:
        if var.name == name:
            return var
    return None

def Cvar_RegisterVariable(variable):
    name   = variable['name']
    flags  = variable['flags']
    value  = variable['value']
    string = variable.get('string')
    default_string = variable.get('default_string')
    callback = variable.get('callback')

    # reminder to implement
    if callback:
        raise NotImplementedError
    
    if Cvar_FindVar(name):
        Con_Printf(f'Cvar_RegisterVariable: cant register variable {name}, already defined')
        return

    if _cmd.Cmd_Exists(name):
        Con_Printf(f'Cvar_RegisterVariable {name} is a command')
        return

    flags |= CVAR_REGISTERED
    
    __cvars.append(cvar_t(name, string, flags, value, default_string, callback))
    
def Cvar_SetCallback(Cvar:dict, callback):

    cvar = Cvar_FindVar(Cvar['name'])

    if cvar is None:
        Sys_Error(f'could not find cvar {Cvar['name']} to set callback')

    cvar.callback = callback

    if callback:
        cvar.flags |= CVAR_CALLBACK
    else:
        cvar.flags &= ~CVAR_CALLBACK


def Cvar_SetQuick(Cvar : cvar_t, value):

    flags = Cvar.flags

    if flags & ( CVAR_ROM | CVAR_LOCKED):
        return
    if not ( flags & CVAR_REGISTERED ):
        return

    if Cvar.string == None:
        Cvar.string = value
    else:
        if Cvar.string == value:
            return # no change

        Cvar.flags |= CVAR_CHANGED
        Cvar.string = value

    Cvar.value = value

    if not Cvar.default_string:
        Cvar.default_string = Cvar.string
    elif not host.host_initialized:
        Cvar.default_string = Cvar.string

    if Cvar.callback:
        Cvar.callback(Cvar)

def Cvar_SetQuickByName(name, value):
    var = Cvar_FindVar(name)
    Cvar_SetQuick(var, value)

def Cvar_SetValueQuick(cvarname, value):
    var = Cvar_FindVar(cvarname)
    # try and convert to int
    try:
        value = int(value)
    except ValueError:
        try:
            value = float(value)
        except ValueError:
            pass

    value = str(value)

    Cvar_SetQuick(var, value)
    

def Cvar_Set(varname, value):
    var = Cvar_FindVar(varname)

    if var == '':
        console.Con_Printf(f'Cvar_Set: variable {varname} not found!')
        return

    Cvar_SetQuick(varname, value)

def Cvar_SetValue(varname, value:float):
    value = str(value)

    Cvar_Set(varname, value)
    
def Cvar_SetROM(varname, value:str):
    var = Cvar_FindVar(varname)
    if var is not None:
        var.flags &= ~CVAR_ROM
        Cvar_SetQuick(var, value)
        var.flags |= CVAR_ROM

def Cvar_SetValueROM(varname, value:float):
    var = Cvar_FindVar(varname)
    if var is not None:
        var.flags &= ~CVAR_ROM
        Cvar_SetValueQuick(var, value)
        var.flags |= CVAR_ROM

   















    
    
    
    