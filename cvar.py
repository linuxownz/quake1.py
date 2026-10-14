#cvar.py

import io

import _cmd
import console
import host

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

class cvar_t:
    def __init__(self, name, string, flags, value, default_string, callback, next):
        self.name: str = name
        self.string = string
        self.flags = flags
        self.value = value
        self.default_string = default_string
        self.callback = callback
        self.next = next

#HAVE TO CONVERT THIS TO A dictionary
#HAVE TO CONVERT THIS TO A dictionary
#HAVE TO CONVERT THIS TO A dictionary
__cvars: dict[cvar_t] = {}
#HAVE TO CONVERT THIS TO A dictionary
#HAVE TO CONVERT THIS TO A dictionary
#HAVE TO CONVERT THIS TO A dictionary

def Cvar_List_f():
    """
    Lists all cvars. If an argument is provided, only lists those
    starting with that string.
    """
    match = _cmd.Cmd_Argv(1)
    var = Cvar_FindVarAfter("", 0) # Start from the beginning

    count = 0
    while var:
        if not match or var.name.startswith(match):
            # Quake format: [A] cvar_name "value"
            # [A] denotes an ARCHIVE flag
            prefix = "A" if (var.flags & CVAR_ARCHIVE) else " "
            console.Con_Printf(f"{prefix} {var.name:20} \"{var.string}\"\n")
            count += 1
        var = Cvar_FindVarAfter(var.name, 0)

    console.Con_Printf(f"{count} cvars\n")

def Cvar_Toggle_f():
    match _cmd.Cmd_Argc():
        case _, 1:
            console.Con_Printf('toggle <cvar> : toggle cvar')
        case 2:
            if Cvar_VariableValue(_cmd.Cmd_Argv(1)):
                Cvar_Set(_cmd.Cmd_Argv(1), '0')
            else:
                Cvar_Set(_cmd.Cmd_Argv(1), '1')


def Cvar_Cycle_f():
    if _cmd.Cmd_Argc() < 3:
        console.Con_Printf('cycle <cvar> <unique value list> : cycle cvar through a list of values')
        return

    val1 = _cmd.Cmd_Argv(1)
    val2 = _cmd.Cmd_Argv(2)

    for i in range(2, _cmd.Cmd_Argc()):
        if float(_cmd.Cmd_Argv(i)) == 0:
            if _cmd.Cmd_Argv(i) == Cvar_VariableString(val1):
                break
        else:
            if _cmd.Cmd_Argv(i) == Cvar_VariableValue(val1):
                break

    if i == _cmd.Cmd_Argc():
        Cvar_Set(val1, val2)
    elif i + 1 == _cmd.Cmd_Argc():
        Cvar_Set(val1, val2)
    else:
        Cvar_Set(val1, _cmd.Cmd_Argv(i + 1))


def Cvar_Inc_f():
    match _cmd.Cmd_Argc():
        case _, 1:
            console.Con_Printf('inc <cvar> [amount] : increment cvar\n')
        case 2:
            Cvar_SetValue( _cmd.Cmd_Argv(1), Cvar_VariableValue(_cmd.Cmd_Argv(1))+1)
        case 3:
            Cvar_SetValue (_cmd.Cmd_Argv(1), Cvar_VariableValue(_cmd.Cmd_Argv(1)) + _cmd.Cmd_Argv(2))


def Cvar_Reset_f():
    match _cmd.Cmd_Argc():
        case _, 1:
            console.Con_Printf('reset <cvar> : reset cvar to default')
        case 2:
            Cvar_Reset(_cmd.Cmd_Argv(1))


def Cvar_ResetAll_f():
    for cvar in __cvars:
        Cvar_Reset(cvar.name)

def Cvar_ResetCfg_f():
    for cvar in __cvars:
        if cvar.flags & CVAR_ARCHIVE:
            Cvar_Reset(cvar.name)

def Cvar_Init():
    global _cmd
    import _cmd
    #import console
    #import host
    #import sys_sdl_unix

    _cmd.Cmd_AddCommand('cvarlist', Cvar_List_f)
    _cmd.Cmd_AddCommand('toggle', Cvar_Toggle_f)
    _cmd.Cmd_AddCommand('cycle', Cvar_Cycle_f)
    _cmd.Cmd_AddCommand('inc', Cvar_Inc_f)
    _cmd.Cmd_AddCommand('reset', Cvar_Reset_f)
    _cmd.Cmd_AddCommand('resetall', Cvar_ResetAll_f)
    _cmd.Cmd_AddCommand('resetcfg', Cvar_ResetCfg_f)

def Cvar_VariableValue(varname) -> float:
    var: cvar_t = Cvar_FindVar(varname)
    if var:
        return float(var.value)

def Cvar_VariableString(varname):
    var: cvar_t = Cvar_FindVar(varname)
    if not var:
        return '' #cvar_null_string
    return var.string

def Cvar_CompleteVariable(partial: str):
    if not partial:
        return None

    for cvar in __cvars:
        if cvar.name.startswith(partial):
            return cvar.name

    return None

def Cvar_Reset(name):
    cvar: cvar_t = Cvar_FindVar(name)

    if not cvar:
        console.Con_Printf(f'variable {name} not found')
    else:
        Cvar_SetQuick(cvar, cvar.default_string)

def Cvar_FindVar(name) -> cvar_t:
    if name in __cvars:
        return __cvars[name]
    return None

def Cvar_FindVarAfter(prev_name: str, with_flags: int) -> cvar_t:
    """
    Finds the next cvar_t in the list after prev_name that matches the flags.
    Matches the logic of the C version you provided.
    """
    found_prev = False

    # If prev_name is empty, we start from the very first cvar
    if not prev_name:
        found_prev = True

    for var in __cvars:
        if not found_prev:
            if var.name == prev_name:
                found_prev = True
            continue

        # Search for the next cvar matching the needed flags
        # (var->flags & with_flags) || !with_flags
        if not with_flags or (var.flags & with_flags):
            return var

    return None


def Cvar_LockVar(var_name):
    var: cvar_t = Cvar_FindVar(var_name)
    if var:
        var.flags |= CVAR_LOCKED

def Cvar_UnlockVar(var_name):
    var: cvar_t = Cvar_FindVar(var_name)
    if var:
        var.flags &= ~CVAR_LOCKED

def Cvar_UnlockAll():
    for cvar in __cvars:
        cvar.flags &= ~CVAR_LOCKED

def Cvar_RegisterVariable(variable):
    name   = variable['name']
    flags  = variable.get('flags', CVAR_NONE)
    value  = variable.get('value')
    initial_str = str(variable.get('value', '0'))
    string = variable.get('string')
    default_string = variable.get('default_string')
    callback = variable.get('callback')

    # reminder to implement
    if callback:
        raise NotImplementedError

    initial_val = 0.0
    try:
        initial_val = float(initial_str)
    except ValueError:
        pass

    if Cvar_FindVar(name):
        console.Con_Printf(f'Cvar_RegisterVariable: cant register variable {name}, already defined')
        return

    if _cmd.Cmd_Exists(name):
        console.Con_Printf(f'Cvar_RegisterVariable {name} is a command')
        return

    new_cvar = cvar_t(
        name=name,
        string=initial_str, # This must NOT be None
        flags=flags | CVAR_REGISTERED,
        value=initial_val,
        default_string=initial_str,
        callback=variable.get('callback'),
        next = None
    )

    __cvars[name] = new_cvar

def Cvar_GetCvar(name) -> cvar_t:
    """ convert __cvars to a hash """
    if name in __cvars:
        return __cvars[name]
    console.Con_Printf(f'failed to look up {name} in Cvar_GetCvar()')
    return None

def Cvar_SetCallback(Cvar:dict, callback):

    cvar = Cvar_FindVar(Cvar['name'])

    if cvar is None:
        sys_sdl_unix.Sys_Error(f'could not find cvar {Cvar['name']} to set callback')

    cvar.callback = callback

    if callback:
        cvar.flags |= CVAR_CALLBACK
    else:
        cvar.flags &= ~CVAR_CALLBACK


def Cvar_SetQuick(Cvar: cvar_t, value: str):

    if Cvar.string == value:
        return


    if Cvar.flags & (CVAR_ROM | CVAR_LOCKED):
        return
    if not (Cvar.flags & CVAR_REGISTERED):
        return

    # Quake converts to string first, then updates the float value
    Cvar.string = str(value)

    try:
        Cvar.value = float(Cvar.string)
    except ValueError:
        Cvar.value = 0.0

    Cvar.flags |= CVAR_CHANGED

    if not Cvar.default_string or not host.host_initialized:
        Cvar.default_string = Cvar.string

    if Cvar.callback:
        try:
            Cvar.callback(Cvar)
        except TypeError:
            Cvar.callback()

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

    if var is None:
        console.Con_Printf(f'Cvar_Set: variable {varname} not found!')
        return

    value = value.strip().strip('"')

    Cvar_SetQuick(var, value)

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


def Cvar_Command(args: list[str]) -> bool:
    """
    Checks if the first argument is a registered Cvar.
    If it is, it either prints the value or sets it.
    Returns True if handled, False if not a Cvar.
    """
    v = Cvar_FindVar(args[0])
    if not v:
        return False

    # If only the name was typed (e.g., "sensitivity")
    if len(args) == 1:
        console.Con_Printf(f'"{v.name}" is "{v.string}"\n')
        return True

    # If a value was provided (e.g., "sensitivity 5")
    # We use index 1 as the new value
    Cvar_Set(v.name, args[1])
    return True


def Cvar_WriteVariables(f: io.FileIO):
    for cvar in __cvars:
        if cvar.flags & CVAR_ARCHIVE:
            f.write(f'{cvar.name} "{cvar.string}"')

