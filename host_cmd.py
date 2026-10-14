#host_cmd.py

import os

import _cmd
import cl_demo
import cl_main
import common
import console
import cvar
import gl_model
import gl_screen
import host
import host_cmd
import in_sdl
import keys
import menu
import net_main
import pr_edict
import pr_exec
import progs
import protocol
import quakedef
import server
import sv_main
import sv_user
import sys_sdl_unix
import world


class filelist_item_t:
    def __init__(self, name, path_id, next):
        self.name: str = name
        self.path_id = path_id
        self.next = next

modlist : filelist_item_t = None
extralevels: filelist_item_t = None
demolist : filelist_item_t = None

noclip_anglehack: bool = False

current_skill: int = 0


def _client_index(client) -> int:
    """C: host_client - svs.clients (pointer subtraction). Identity based."""
    for i, c in enumerate(sv_main.svs.clients):
        if c is client:
            return i
    return -1


def FileList_Add(name, _list: filelist_item_t, path_id) -> filelist_item_t:
    item = _list

    # 1. Check for duplicate entries
    while item:
        if name == item.name:
            return _list
        item = item.next

    # 2. Allocate new file list node
    new_item = filelist_item_t(name, path_id, None)

    # 3. Handle empty list or insertion at the head (alphabetical order)
    if _list is None or new_item.name < _list.name:
        new_item.next = _list
        return new_item

    # 4. Traverse to find alphabetical insertion position
    prev = _list
    cursor = _list.next

    while cursor and new_item.name > cursor.name:
        prev = cursor
        cursor = cursor.next

    new_item.next = prev.next
    prev.next = new_item

    return _list

def FileList_Clear(_list: filelist_item_t):
    blah: filelist_item_t
    while _list:
        blah = _list.next
        _list.next = None
        _list = blah

def ExtraMaps_Add(name, _list: filelist_item_t, path_id):
    global extralevels
    extralevels = FileList_Add(name, _list, path_id)

def ExtraMaps_Clear():
    global extralevels
    FileList_Clear(extralevels)
    extralevels = None


def ExtraMaps_NewGame():
    ExtraMaps_Clear()
    ExtraMaps_Init()

def ExtraMaps_List(mod_name: str):
    if mod_name:
        console.Con_Printf(f'maps in search path from directory {mod_name}')
        search: common.searchpath_t = common.com_searchpaths

        while search:
            if search.pack:
                continue
            else:
                dir_name = os.path.basename(search.filename)

                if dir_name.casefold() == mod_name.casefold():
                    path_id = search.path_id
                    break
            search = search.next

        if not path_id:
            console.Con_Printf(f'game {mod_name} not loaded')
            return

        level = extralevels
        i = 0
        while level:
            if path_id and path_id != level.path_id:
                continue
            i += 1
            level = level.next
        if i:
            console.Con_Printf(f'{i} maps found')
        else:
            console.Con_Printf('no maps found')




def Host_Maps_f():
    if _cmd.Cmd_Argc() > 1:
        ExtraMaps_List(_cmd.Cmd_Argv(1))
    else:
        ExtraMaps_List(None)

def Host_Maps_Mod_f():
    ExtraMaps_List(common.COM_SkipPath(common.com_gamedir))


def Modlist_Add(name: str):
    global modlist
    modlist = FileList_Add(name, modlist, 0)


def Host_Mapname_f():
    if sv_main.sv.active:
        console.Con_Printf(f'mapname is {sv_main.sv.name}')
        return

    if cl_main.cls.state == quakedef.cactive_t.ca_connected:
        console.Con_Printf(f'mapname is {cl_main.cl.mapname}')

    console.Con_Printf('no map loaded')


def Host_Randmap_f():
    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        return

    level: filelist_item_t = extralevels

    numlevels = 0
    while level:
        numlevels += 1
        level = level.next

    if numlevels == 0:
        console.Con_Printf('no maps')
        return

    import random
    randlevel = random.randrange(numlevels)

    level = extralevels
    i = 0
    while level:
        if i == randlevel:
            console.Con_Printf(f'Starting map {level.name}')
            _cmd.Cbuf_AddText(f'map {level.name}')
            return




def Host_Status_f():
    print_fn = console.Con_Printf
    seconds = 0; minutes = 0; hours = 0

    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        if not sv_main.sv.active:
            _cmd.Cmd_ForwardToServer()
            return
    else:
        print_fn = host.SV_ClientPrintf


    print_fn(f'host:     {cvar.Cvar_VariableString('hostname')}')
    print_fn(f'version: {1.0}')

    if net_main.tcpipAvailable:
        print_fn(f'tcp/ip:   {net_main.my_tcpip_address}')

    print_fn(f'map:    {sv_main.sv.name}')
    print_fn(f'players: {net_main.net_activeconnections} active ({sv_main.svs.maxclients} max) ')

    j = 1
    for client in sv_main.svs.clients:
        if not client.active:
            continue

        seconds = int(net_main.net_time - net_main.NET_QSocketGetTime(client.netconnection))
        minutes = seconds / 60

        if minutes:
            seconds -= ( minutes * 60)
            hours = minutes / 60
            if hours:
                minutes -= (hours * 60)
        else:
            hours = 0

        print_fn(f'{j} {client.name} {client.edict.v.frags} {hours}:{minutes}:{seconds}' )

        print_fn(f'{net_main.NET_QSocketGetAddressString(client.netconnection)}')

def Host_Quit_f():
    if keys.key_dest != keys.keydest_t.key_console and cl_main.cls.state != cl_main.cactive_t.ca_dedicated:
        menu.M_Menu_Quit_f()
        return

    cl_main.CL_Disconnect()
    host.Host_ShutdownServer(False)

    sys_sdl_unix.Sys_Quit()

def Host_God_f():
    if _cmd.cmd == _cmd.cmd_source_t.src_command:
        _cmd.Cmd_ForwardToServer()
        return

    if pr_edict.pr_global_struct.deathmatch:
        return

    match _cmd.Cmd_Arvc():
        case 1:
            host.host_client.edict.v.flags = int(host.host_client.edict.v.flags) ^ quakedef.FL_GODMODE
            if int(host.host_client.edict.v.flags) & quakedef.FL_GODMODE:
                host.SV_ClientPrintf('godmode ON\n')
            else:
                host.SV_ClientPrintf('godmode OFF')
        case 2:
            if _cmd.Cmd_Argv(1) == 1:
                host.host_client.edict.v.flags = host.host_client.edict.v.flags | quakedef.FL_GODMODE
                host.SV_ClientPrintf('godmode ON\n')
            else:
                host.host_client.edict.v.flags = host.host_client.edict.v.flags & ~quakedef.FL_GODMODE
                host.SV_ClientPrintf('godmode OFF\n')
        case _:
            console.Con_Printf('god [value] : toggle god mode 0=off, 1=on\n')

def Host_Notarget_f():

    if _cmd.cmd == _cmd.cmd_source_t.src_command:
        _cmd.Cmd_ForwardToServer()
        return

    if pr_edict.pr_global_struct.deathmatch:
        return

    match _cmd.Cmd_Arvc():
        case 1:
            host.host_client.edict.v.flags = int(host.host_client.edict.v.flags) ^ quakedef.FL_NOTARGET
            if int(host.host_client.edict.v.flags) & quakedef.FL_NOTARGET:
                host.SV_ClientPrintf('notarget ON\n')
            else:
                host.SV_ClientPrintf('notarget OFF')
        case 2:
            if _cmd.Cmd_Argv(1) == 1:
                host.host_client.edict.v.flags = host.host_client.edict.v.flags | quakedef.FL_NOTARGET
                host.SV_ClientPrintf('notarget ON\n')
            else:
                host.host_client.edict.v.flags = host.host_client.edict.v.flags & ~quakedef.FL_NOTARGET
                host.SV_ClientPrintf('notarget OFF\n')
        case _:
            console.Con_Printf('notarget [value] : toggle notarget mode 0=off, 1=on\n')

def Host_Fly_f():
    if _cmd.cmd == _cmd.cmd_source_t.src_command:
        _cmd.Cmd_ForwardToServer()
        return

    if pr_edict.pr_global_struct.deathmatch:
        return

    match (_cmd.Cmd_Argc()):
        case 1:
            if host.host_client.edict.v.movetype != quakedef.MOVETYPE_FLY:
                host.host_client.edict.v.movetype = quakedef.MOVETYPE_FLY
                host.SV_ClientPrintf('flymode ON\n')
            else:
                host.host_client.edict.v.movetype = quakedef.MOVETYPE_WALK
                host.SV_ClientPrintf('flymode OFF\n')
        case 2:
            if _cmd.Cmd_Argv(1):
                host.host_client.edict.v.movetype = quakedef.MOVETYPE_FLY
                host.SV_ClientPrintf('flymode ON\n')
            else:
                host.host_client.edict.v.movetype = quakedef.MOVETYPE_WALK
                host.SV_ClientPrintf('flymode OFF\n')
        case _:
            console.Con_Printf('fly [value] : toggle fly mode. values 0=off, 1=on\n')

def Host_Map_f():
    if _cmd.Cmd_Argc() < 2:
        if cl_main.cls.state == cl_main.cactive_t.ca_dedicated:
            if sv_main.sv.active:
                console.Con_Printf(f'Current map {sv_main.sv.name}')
            else:
                console.Con_Printf('server not active')
        elif cl_main.cls.state == cl_main.cactive_t.ca_connected:
            console.Con_Printf(f'Current map {cl_main.cl.levelname} {cl_main.cl.mapname}')
        else:
            console.Con_Printf('map <levelname>: start a new server')
        return

    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        return

    cl_main.cls.demonum = -1

    cl_main.CL_Disconnect()
    host.Host_ShutdownServer(False)

    if cl_main.cls.state != cl_main.cactive_t.ca_dedicated:
        in_sdl.IN_Activate()

    keys.key_dest = keys.keydest_t.key_game
    gl_screen.SCR_BeginLoadingPlaque()

    sv_main.svs.serverflags = 0
    name = _cmd.Cmd_Argv(1)

    name.strip('.bsp')

    sv_main.SV_SpawnServer(name)

    if not sv_main.sv.active:
        return

    if cl_main.cls.state != cl_main.cactive_t.ca_dedicated:
        for i in range (_cmd.Cmd_Argc()):
            cl_main.cls.spawnparms += _cmd.Cmd_Argv(i)
        _cmd.Cmd_ExecuteString ('connect local', _cmd.cmd_source_t.src_command)


def Host_Restart_f():

    if cl_main.cls.demoplayback or not sv_main.sv.active:
        return

    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        return

    sv_main.SV_SpawnServer(sv_main.sv.name)

    if not sv_main.sv.active:
        host.Host_Error(f'cannot restart map {sv_main.sv.name}')


def Host_Changelevel_f():
    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf('changelevel <levelname> : continue game on a new level\n')
        return

    if not sv_main.sv.active or cl_main.cls.demoplayback:
        console.Con_Printf('only the server may changelevel\n')
        return

    level = f'maps/{_cmd.Cmd_Argv(1)}.bsp'

    if not common.COM_FileExists(level, None):
        host.Host_Error(f'cannot find map {level}')

    if cl_main.cls.state != quakedef.cactive_t.ca_dedicated:
        in_sdl.IN_Activate()

    keys.key_dest = keys.keydest_t.key_game
    sv_main.SV_SaveSpawnparms()

    level = _cmd.Cmd_Argv(1)
    sv_main.SV_SpawnServer(level)

    if not sv_main.sv.active:
        host.Host_Error(f'cannot run map {level}')


def Host_Connect_f():
    cl_main.cls.demonum = -1

    if cl_main.cls.demoplayback:
        cl_demo.CL_StopPlayback()
        cl_main.CL_Disconnect()

    cl_main.CL_EstablishConnection(_cmd.Cmd_Argv(1))
    Host_Reconnect_f()

def Host_SavegameComment():
    comment = cl_main.cl.levelname + '\n'
    comment += f'kills: {cl_main.cl.stats[quakedef.STAT_MONSTERS]:03}/{cl_main.cl.stats[quakedef.STAT_TOTALMONSTERS]:03}\n'
    return comment


def Host_Reconnect_f():
    if cl_main.cls.demoplayback:
        return

    gl_screen.SCR_BeginLoadingPlaque()
    cl_demo.CL_ClearSignons()


def Host_Name_f():
    newName = ''
    cl_name = cvar.Cvar_GetCvar('_cl_name')

    if _cmd.Cmd_Argc() == 1:
        console.Con_Printf(f'name is {cl_name.string}')
        return

    if _cmd.Cmd_Argc() == 2:
        newName = _cmd.Cmd_Argv(1)
    else:
        newName = _cmd.Cmd_Args()

    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        if cl_name.string == newName:
            return

        cvar.Cvar_Set('_cl_name', newName)

        if cl_main.cls.state == cl_main.cactive_t.ca_connected:
            _cmd.Cmd_ForwardToServer()
        return

    if host.host_client.name and host.host_client.name != 'unconnected':  # noqa: SIM102
        if host.host_client.name != newName:
            console.Con_Printf(f'{host.host_client.name} renamed to {newName}')

    host.host_client.name = newName
    host.host_client.edict.v.netname = pr_edict.PR_SetEngineString(host.host_client.name)

    common.MSG_WriteByte(sv_main.sv.reliable_datagram, protocol.svc_updatename)
    common.MSG_WriteByte(sv_main.sv.reliable_datagram, _client_index(host.host_client))
    common.MSG_WriteString(sv_main.sv.reliable_datagram, host.host_client.name)


def Host_Say(teamonly: bool):
    fromServer = False
    save: server.client_t = None
    client: server.client_t = None

    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        if cl_main.cls.state != quakedef.cactive_t.ca_dedicated:
            _cmd.Cmd_ForwardToServer_f()
            return
        fromServer = True
        teamonly = False

    if _cmd.Cmd_Argc() < 2:
        return

    save = host.host_client
    p = _cmd.Cmd_Args()
    quoted = False

    if p.startswith('"'):
        p = p[1:]
        quoted = True

    if not fromServer:
        text = f'\001{save.name}: {p}'
    else:
        hostname = cvar.Cvar_GetCvar('hostname')
        text = f'\001<{hostname.string}> {p}'

    buffer_size = 1024
    if len(text) >= buffer_size - 1:
        text = text[: buffer_size - 2] + "\n"
    else:
        # 2. Strip trailing \r, \n, and conditional trailing quote
        while text:
            if text.endswith(("\r", "\n")):
                text = text[:-1]
            elif text.endswith('"') and quoted:
                quoted = False
                text = text[:-1]
            else:
                break

        text += "\n"

    for client in sv_main.svs.clients:
        if not client or not client.active or not client.spawned:
            continue
        if cvar.Cvar_GetCvar('teamplay').value and teamonly and client.edict.v.team != save.edict.v.team:
            continue
        host.host_client = client
        host.SV_ClientPrintf(text)

    host.host_client = save

    if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
        sys_sdl_unix.Sys_Printf(text[1:])




def Host_Noclip_f():
    global noclip_anglehack
    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        _cmd.Cmd_ForwardToServer()
        return

    if pr_edict.pr_global_struct.deathmatch:
        return

    match _cmd.Cmd_Argc():
        case 1:
            if host.host_client.edict.v.movetype != quakedef.MOVETYPE_NOCLIP:
                noclip_anglehack = True
                host.host_client.edict.v.movetype = quakedef.MOVETYPE_NOCLIP
                host.SV_ClientPrintf('noclip ON\n')

            else:
                noclip_anglehack = False
                host.host_client.edict.v.movetype = quakedef.MOVETYPE_WALK
                host.SV_ClientPrintf('noclip OFF\n')
        case 2:
            if _cmd.Cmd_Argv(1):
                noclip_anglehack = True
                host.host_client.edict.v.movetype = quakedef.MOVETYPE_NOCLIP
                host.SV_ClientPrintf('noclip ON\n')
            else:
                noclip_anglehack = False
                host.host_client.edict.v.movetyhpe = quakedef.MOVETYPE_WALK
                host.SV_ClientPrintf('noclip OFF\n')
        case _:
            console.Con_Printf('noclip [0/1]')

def Host_SetPos_f():
    global noclip_anglehack
    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        _cmd.Cmd_ForwardToServer_f()
        return

    if pr_edict.pr_global_struct.deathmatch:
        return

    if _cmd.Cmd_Argv() != 7 and _cmd.Cmd_Argv() != 4:
        v = host.host_client.edict.v

        host.SV_ClientPrintf("usage:\n")
        host.SV_ClientPrintf("   setpos <x> <y> <z>\n")
        host.SV_ClientPrintf("   setpos <x> <y> <z> <pitch> <yaw> <roll>\n")
        host.SV_ClientPrintf("current values:\n")
        host.SV_ClientPrintf(
            f"   {int(v.origin[0])} {int(v.origin[1])} {int(v.origin[2])} "
            f"{int(v.v_angle[0])} {int(v.v_angle[1])} {int(v.v_angle[2])}\n"
        )

    if host.host_client.edict.v.movetype != quakedef.MOVETYPE_NOCLIP:
        noclip_anglehack = True
        host.host_client.edict.v.movetype = quakedef.MOVETYPE_NOCLIP
        host.SV_ClientPrintf('noclip ON')

    host.host_client.edict.v.velocity[0] = 0
    host.host_client.edict.v.velocity[1] = 0
    host.host_client.edict.v.velocity[2] = 0

    host.host_client.edict.v.origin[0] = float(_cmd.Cmd_Argv(1))
    host.host_client.edict.v.origin[1] = float(_cmd.Cmd_Argv(2))
    host.host_client.edict.v.origin[2] = float(_cmd.Cmd_Argv(3))

    if _cmd.Cmd_Argv() == 7:
        host.host_client.edict.v.angles[0] = float(_cmd.Cmd_Argv(4))
        host.host_client.edict.v.angles[1] = float(_cmd.Cmd_Argv(5))
        host.host_client.edict.v.angles[2] = float(_cmd.Cmd_Argv(6))
        host.host_client.edict.v.fixangle = 1

    world.SV_LinkEdict(host.host_client.edict, False)


def Host_Say_f():
    Host_Say(False)

def Host_Say_Team_f():
    Host_Say(True)

def Host_Tell_f():
    quoted = False

    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        _cmd.Cmd_ForwardToServer()
        return

    if _cmd.Cmd_Argc() < 3:
        return

    p = _cmd.Cmd_Args()

    if p[0] == '"':
        p = p[1:]
        quoted = True

    text = f'{host.host_client.name}: {p}'
    if quoted:
        text = text.rstrip('"')
    text = text.rstrip() + '\n'

    save = host.host_client
    for client in sv_main.svs.clients:
        if not client.active or not client.spawned:
            continue
        if client.name != _cmd.Cmd_Argv(1):
            continue
        host.host_client = client
        host.SV_ClientPrintf(text)
        break
    host.host_client = save


def Host_Color_f():
    top = 0
    bottom = 0

    if _cmd.Cmd_Argc() == 1:
        cl_color = cvar.Cvar_GetCvar('_cl_color').value
        console.Con_Printf (f'"color" is {(int(cl_color)) >> 4} {(int(cl_color)) & 0x0f}')
        console.Con_Printf ("color <0-13> [0-13]\n");
        return;

    if _cmd.Cmd_Argc() == 2:
        top = bottom = int(_cmd.Cmd_Argv(1))
    else:
        top    = int(_cmd.Cmd_Argv(1))
        bottom = int(_cmd.Cmd_Argv(2))

    top &= 15
    top = min(top, 13)
    bottom &= 15
    bottom = min(bottom, 13)

    playercolor = top * 16 + bottom

    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        cvar.Cvar_SetValue('_cl_color', playercolor)
        if cl_main.cls.state == quakedef.cactive_t.ca_connected:
            _cmd.Cmd_ForwardToServer()
        return

    host.host_client.colors = playercolor
    host.host_client.edict.v.team = bottom + 1

    common.MSG_WriteByte(sv_main.sv.reliable_datagram, protocol.svc_updatecolors)
    client_index = _client_index(host.host_client) & 0xff
    common.MSG_WriteByte(sv_main.sv.reliable_datagram, client_index)
    common.MSG_WriteByte(sv_main.sv.reliable_datagram, host.host_client.colors)

def Host_Kill_f():
    if _cmd.cmd == _cmd.cmd_source_t.src_command:
        _cmd.Cmd_ForwardToServer()
        return

    if host.host_client.edict.v.health <= 0:
        host.SV_ClientPrintf('cant suicide -- already dead')
        return

    pr_edict.pr_global_struct.time = sv_main.sv.time
    pr_edict.pr_global_struct.self = pr_edict.EDICT_TO_PROG(host.host_client.edict)
    pr_edict.PR_ExecuteProgram(pr_edict.pr_global_struct.ClientKill)

# supposed to be defined in host_cmd.py
def Host_Pause_f():
    if cl_main.cls.demoplayback:
        cl_main.cls.demopaused = not cl_main.cls.demopaused
        cl_main.cl.paused = cl_main.cls.demopaused
        return

    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        _cmd.Cmd_ForwardToServer()
        return

    if not cvar.Cvar_GetCvar('pausable').value:
        host.SV_ClientPrintf('pause not allowed\n')
    else:
        sv_main.sv.paused ^= 1;

        if sv_main.sv.paused:
            host.SV_BroadcastPrintf(f'{pr_edict.PR_GetString(host.host_client.edict.v.netname)} paused the game')
        else:
            host.SV_BroadcastPrintf(f'{pr_edict.PR_GetString(host.host_client.edict.v.netname)} unpaused the game')

        common.MSG_WriteByte(sv_main.sv.reliable_datagram, protocol.svc_setpause)
        common.MSG_WriteByte(sv_main.sv.reliable_datagram, sv_main.sv.paused)

def Host_Spawn_f():
    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        console.Con_Printf('spawn is not valid from the console\n')
        return
    if host.host_client.spawned:
        console.Con_Printf('spawn not valid -- already spawned\n')
        return

    if sv_main.sv.loadgame:
        sv_main.sv.paused = False
    else:
        ent = host.host_client.edict
        ent.v.colormap = pr_edict.NUM_FOR_EDICT(ent)
        ent.v.team = ( host.host_client.colors & 15) + 1
        ent.v.netname = pr_edict.PR_SetEngineString(host.host_client.name)

        # Copy spawn parms out of host_client into pr_global_struct
        for i in range(server.NUM_SPAWN_PARMS):
            setattr(pr_edict.pr_global_struct, f"parm{i + 1}", host.host_client.spawn_parms[i])

        pr_edict.pr_global_struct.time = sv_main.sv.time
        pr_edict.pr_global_struct.self = pr_edict.EDICT_TO_PROG(host.host_client.edict)
        pr_exec.PR_ExecuteProgram(pr_edict.pr_global_struct.ClientConnect)

        if sys_sdl_unix.Sys_DoubleTime() - net_main.NET_QSocketGetTime(host.host_client.netconnection) <= sv_main.sv.time:
            sys_sdl_unix.Sys_Printf(f'{host.host_client.name} entered the game\n')

        pr_exec.PR_ExecuteProgram(pr_edict.pr_global_struct.PutClientInServer)

    common.SZ_Clear(host.host_client.message)

    common.MSG_WriteByte(host.host_client.message, protocol.svc_time)
    common.MSG_WriteFloat(host.host_client.message, sv_main.sv.time)

    for i in range(sv_main.svs.maxclients):
        client = sv_main.svs.clients[i]
        common.MSG_WriteByte (host.host_client.message, protocol.svc_updatename)
        common.MSG_WriteByte (host.host_client.message, i)
        common.MSG_WriteString (host.host_client.message, client.name)
        common.MSG_WriteByte (host.host_client.message, protocol.svc_updatefrags)
        common.MSG_WriteByte (host.host_client.message, i)
        common.MSG_WriteShort (host.host_client.message, client.old_frags)
        common.MSG_WriteByte (host.host_client.message, protocol.svc_updatecolors)
        common.MSG_WriteByte (host.host_client.message, i)
        common.MSG_WriteByte (host.host_client.message, client.colors)

    for i in range(quakedef.MAX_LIGHTSTYLES):
        common.MSG_WriteByte(host.host_client.message, protocol.svc_lightstyle)
        common.MSG_WriteByte(host.host_client.message, i)
        common.MSG_WriteString(host.host_client.message, sv_main.sv.lightstyles[i])

    common.MSG_WriteByte (host.host_client.message, protocol.svc_updatestat)
    common.MSG_WriteByte (host.host_client.message, quakedef.STAT_TOTALSECRETS)
    common.MSG_WriteLong (host.host_client.message, pr_edict.pr_global_struct.total_secrets)

    common.MSG_WriteByte (host.host_client.message, protocol.svc_updatestat)
    common.MSG_WriteByte (host.host_client.message, quakedef.STAT_TOTALMONSTERS)
    common.MSG_WriteLong (host.host_client.message, pr_edict.pr_global_struct.total_monsters)

    common.MSG_WriteByte (host.host_client.message, protocol.svc_updatestat)
    common.MSG_WriteByte (host.host_client.message, quakedef.STAT_SECRETS)
    common.MSG_WriteLong (host.host_client.message, pr_edict.pr_global_struct.found_secrets)

    common.MSG_WriteByte (host.host_client.message, protocol.svc_updatestat)
    common.MSG_WriteByte (host.host_client.message, quakedef.STAT_MONSTERS)
    common.MSG_WriteLong (host.host_client.message, pr_edict.pr_global_struct.killed_monsters)

    client_num = _client_index(host.host_client)
    ent = pr_edict.EDICT_NUM(1 + client_num)

    common.MSG_WriteByte(host.host_client.message, protocol.svc_setangle)

    for i in range(2):
        common.MSG_WriteAngle(host.host_client.message, ent.v.angles[i], sv_main.sv.protocolflags)

    common.MSG_WriteAngle(host.host_client.message, 0, sv_main.sv.protocolflags)

    sv_main.SV_WriteClientdataToMessage(host.host_client.edict, host.host_client.message)

    common.MSG_WriteByte(host.host_client.message, protocol.svc_signonnum)
    common.MSG_WriteByte(host.host_client.message, 3)
    host.host_client.sendsignon = server.sendsignon_e.PRESPAWN_FLUSH






def Host_Begin_f():
    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        console.Con_Printf('begin not valid from console\n')
        return

    host.host_client.spawned = True


def Host_PreSpawn_f():
    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        console.Con_Printf('prespawn not available from console\n')
        return

    if host.host_client.spawned:
        console.Con_Printf('prespawn not valid, already spawned\n')
        return

    host.host_client.sendsignon = server.sendsignon_e.PRESPAWN_SIGNONBUFS
    host.host_client.signonidx = 0


def Host_Kick_f():
    who = ''
    message = ''
    byNumber = False

    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        if not sv_main.sv.active:
            _cmd.Cmd_ForwardToServer()
            return

    elif pr_edict.pr_global_struct.deathmath:
        return

    save = host.host_client

    i = 0

    if _cmd.Cmd_Argc() > 2 and _cmd.Cmd_Argv(1) == '#':
        i = int(_cmd.Cmd_Argv(2)) - 1

        if i < 0 or i >= sv_main.svs.maxclients:
            return
        if not sv_main.svs.clients[i].active:
            return
        host.host_client = sv_main.svs.clients[i]
        byNumber = True
    else:
        for host_client in sv_main.svs.clients:
            if not host_client.active:
                continue
            if host_client.name == _cmd.Cmd_Argv(1):
                break

    if i < sv_main.svs.maxclients:
        if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
            if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
                who = 'Console'
            else:
                who = cvar.Cvar_GetCvar('_cl_name').string
        else:
            who = save.name

        if host.host_client is save:
            return

        if _cmd.Cmd_Argc() > 2:
            message = common.COM_Parse(_cmd.Cmd_Args())

            if byNumber:
                message = message[1:]
                message.lstrip()

                message = message[len(_cmd.Cmd_Argv(2)):]

                message.lstrip()

        if len(message):
            host.SV_ClientPrintf(f'kicked by {who} {message}')
        else:
            host.SV_ClientPrintf(f'kicked by {who}')

        host.SV_DropClient(False)

    host.host_client = save

def Host_Ping_f():
    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        _cmd.Cmd_ForwardToServer()
        return

    host.SV_ClientPrintf('client ping times:\n')

    total = 0.0
    for client in sv_main.svs.clients:
        if not client.active:
            continue

        for j in client.ping_times:
            total += client.ping_times

        total /= quakedef.NUM_PING_TIMES

        host.SV_ClientPrintf(f'{total*1000} {client.name}')

start = ''
def Host_Loadgame_f():
    if _cmd.cmd_source == _cmd.cmd_source_t.src_command:
        return

    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf('load <savename> : load a game\n')
        return

    if _cmd.Cmd_Argv(1).contains('..'):
        console.Con_Printf('load <savename> : relative pathnames are not allowed\n')
        return

    nomonsters:cvar.cvar_t = cvar.Cvar_GetCvar('nomonsters')
    if nomonsters.value:
        console.Con_Warning(f'{nomonsters.name} disabled automatically\n')
        cvar.Cvar_SetValueQuick(nomonsters, 0.0)

    cl_main.cls.demonum = -1

    name = f'{common.com_gamedir}/{_cmd.Cmd_Argv(1)}'
    common.COM_AddExtension(name, '.sav')

    # disabled in original source
    #SCR_BeginLoadingPlaque()

    console.Con_Printf(f'loading game from {name}\n')

    if start:
        start = None

    start, _ = common.COM_LoadMallocFile_TextMode_OSPath(name) # name, NULL

    if start is None:
        console.Con_Printf(f'Error: could not open savegame {name}\n')
        return

    data = start
    data, version = common.COM_ParseIntNewline(data) # data, version

    if version != quakedef.SAVEGAME_VERSION: # 5
        start = None
        host.Host_Error(f'savegame is version {version} not {quakedef.SAVEGAME_VERSION}\n')
        return

    data = common.COM_ParseIntNewline(data)

    spawn_parms: list[float] = [0.0 for _ in quakedef.NUM_SPAWN_PARMS]
    for i in range(quakedef.NUM_SPAWN_PARMS):
        data, spawn_parms[i] = common.COM_ParseFloatNewline(data) # data, &spawn_parms[i]

    global current_skill
    data, current_skill = common.COM_ParseFloatNewline(data) # data, &tfloat ( current_skill )
    cvar.Cvar_SetValue('skill', current_skill)

    data, token = common.COM_ParseStringNewline(data)
    mapname = token # TODO q_strlcpy ( mapname, com_token, sizeof mapname)
    data, time = common.COM_ParseFloatNewline(data)

    cl_main.CL_Disconnect_f()

    sv_main.SV_SpawnServer(mapname)

    if not sv_main.sv.active:
        start = None
        gl_screen.SCR_EndLoadingPlaque()
        console.Con_Printf(f'couldnt load map {mapname}\n')

    sv_main.sv.paused = True
    sv_main.sv.loadgame = True

    for i in range(quakedef.MAX_LIGHTSTYLES):
        data, token = common.COM_ParseStringNewline(data)
        sv_main.sv.lightstyles[i] = token

    entnum = -1

    while(data):
        data = common.COM_Parse(data)

        if common.com_token == '':
            break

        if common.com_token != '{':
            host.Host_Error('first token isnt a brace')

        if entnum == -1:
            data = pr_edict.ED_ParseGlobals(data)
        else:
            ent = pr_edict.EDICT_NUM(entnum)
            if entnum < sv_main.sv.num_edicts:
                ent.free = False
                ent.v = [] # Array(progs.entityfields * 4) # TODO may have to implement fixedsize array
            else:
                ent.baseline.scale = protocol.ENTSCALE_DEFAULT

            data, ent = pr_edict.ED_ParseEdict(data)

            if not ent.free:
                sv_main.SV_LinkEdict(ent, False)

        entnum += 1


    for i in range(sv_main.sv.num_edicts):
        pr_edict.ED_Free(pr_edict.EDICT_NUM(i))

    sv_main.sv.num_edicts = entnum
    sv_main.sv.time = time

    start = None

    for i in range(quakedef.NUM_SPAWN_PARMS):
        sv_main.svs.client.spawn_parms[i] = spawn_parms[i]

    if cl_main.cls.state != quakedef.cactive_t.ca_dedicated:
        cl_main.CL_EstablishConnection('local')
        Host_Reconnect_f()

    if cl_main.cls.state != quakedef.cactive_t.ca_dedicated:
        in_sdl.IN_Activate()


def Host_Savegame_f():
    name = ''
    comment = ''

    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        return

    if not sv_main.sv.active:
        console.Con_Printf('not playing a local game\n')
        return

    if sv_main.sv.nomonsters:
        console.Con_Printf('cant save when using nomonsters\n')
        return

    if cl_main.cl.intermission:
        console.Con_Printf('cant save in an intermission\n')
        return

    if sv_main.svs.maxclients != 1:
        console.Con_Printf('cant save multiplayer games\n')
        return

    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf('save <savename> : save a game\n')
        return

    if '..' in _cmd.Cmd_Argv(1):
        console.Con_Printf('relative pathname are not allowed\n')
        return

    for client in sv_main.svs.maxclients:
        if client.active and client.edict.v.health <= 0:
            console.Con_Printf('cant save game with dead player\n')
            return

    name = f'{common.com_gamedir}/{_cmd.Cmd_Argv(1)}'
    name += '.sav' #COM_AddExtension(name, '.sav')

    console.Con_Printf(f'saving game to {name}\n')

    try:
        with open(name, 'w') as file:
            file.write(f'{quakedef.SAVEGAME_VERSION}\n')
            comment += Host_SavegameComment()
            file.write(f'{comment}\n')

            file.writelines(f'{sv_main.svs.client.spawn_parms[i]}\n' for i in range(quakedef.NUM_SPAWN_PARMS))

            file.write(f'{current_skill}\n')
            file.write(f'{sv_main.sv.name}\n')
            file.write(f'{sv_main.sv.time}\n')

            for i in range(quakedef.MAX_LIGHTSTYLES):
                if sv_main.sv.lightstyles[i]:
                    file.write(f'{sv_main.sv.lightstyles[i]}\n')
                else:
                    file.write('m\n')

            pr_edict.ED_WriteGlobals(file)

            for i in range(sv_main.sv.num_edicts):
                pr_edict.ED_Write(file, pr_edict.EDICT_NUM(i))

            file.close()
            console.Con_Printf('done\n')

    except OSError as e:
        console.Con_Printf(f'couldnt open save file {e}')
        return




def Host_Give_f():
    if _cmd.cmd_source == _cmd.cmd_source.src_command:
        _cmd.Cmd_ForwardToServer()
        return

    if pr_edict.pr_global_struct.deathmatch:
        return

    t = _cmd.Cmd_Argv(1)
    v = int(_cmd.Cmd_Argv(2))

    match(t[0]):
        case x if 0 <= x <= 9:
            if common.hipnotic:
                if t[0] == '6':
                    if t[1] == 'a':
                        host.host_client.edict.v.items = host.host_client.edict.v.items | quakedef.HIT_PROXIMITY_GUN
                    else:
                        host.host_client.edict.v.items = host.host_client.edict.v.items | quakedef.IT_GRENADE_LAUNCHER
                elif t[0] == '9':
                    host.host_client.edict.v.items |= quakedef.HIT_LASER_CANNON
                elif t[0] == '0':
                    host.host_client.edict.v.items |= quakedef.HIT_MJOLNIR
                elif t[0] == '2':
                    host.host_client.edict.v.items = host.host_client.edict.v.items | ( quakedef.IT_SHOTGUN << (int(t[0]) - 2))

            else:
                if t[0] >= '2':
                    host.host_client.edict.v.items = host.host_client.edict.v.items | ( quakedef.IT_SHOTGUN << (int(t[0]) - 2))
        case 's':
            if common.rogue:
                val = pr_edict.GetEdictFieldValue(host.host_client.edict, 'ammo_shells1')
                if val:
                    val.float = v

            host.host_client.edict.v.ammo_shells1 = v
        case 'n':
            if common.rogue:
                val = pr_edict.GetEdictFieldValue(host.host_client.edict, 'ammo_nails1')
                if val:
                    val.float = v
                    if host.host_client.edict.v.weapon <= quakedef.IT_LIGHTNING:
                        host.host_client.edict.v.ammo_nails = v

            else:
                host.host_client.edict.v.ammo_nails = v

        case 'l':
            if common.rogue:
                val = pr_edict.GetEdictFieldValue(host.host_client.edict, 'ammo_lava_nails')
                if val:
                    val.float = v
                    if host.host_client.edict.v.weapon > quakedef.IT_LIGHTNING:
                        host.host_client.edict.v.ammo_nails = v
        case 'r':
            if common.rogue:
                val = pr_edict.GetEdictFieldValue(host.host_client.edict, 'ammo_rockets')
                if val:
                    val.float = v
                    if host.host_client.edict.v.weapon <= quakedef.IT_LIGHTNING:
                        host.host_client.edict.v.ammo_rockets = v
            else:
                host.host_client.edict.v.ammo_rockets = v
        case 'm':
            if common.rogue:
                val = pr_edict.GetEdictFieldValue(host.host_client.edict, 'ammo_multi_rockets')
                if val:
                    val.float = v
                    if host.host_client.edict.v.weapon > quakedef.IT_LIGHTNING:
                        host.host_client.edict.v.ammo_rockets = v
        case 'h':
            host.host_client.edict.v.health = v

        case 'c':
            if common.rogue:
                val = pr_edict.GetEdictFieldValue(host.host_client.edict, 'ammo_cells')
                if val:
                    val.float = v
                    if host.host_client.edict.v.weapon <= quakedef.IT_LIGHTNING:
                        host.host_client.edict.v.ammo_cells = v
            else:
                host.host_client.edict.v.ammo_cells = v

        case 'p':
            if common.rogue:
                val = pr_edict.GetEdictFieldValue(host.host_client.edict, 'ammo_plasma')
                if val:
                    val.float = v
                    if host.host_client.edict.v.weapon > quakedef.IT_LIGHTNING:
                        host.host_client.edict.v.ammo_cells = v

        case 'a':
            if v > 150:
                host.host_client.edict.v.armortype = 0.8
                host.host_client.edict.v.armorvalue = v
                host.host_client.edict.v.items = host.host_client.edict.v.items - int(host.host_client.edict.v.items & int(quakedef.IT_ARMOR1 | quakedef.IT_ARMOR2 | quakedef.IT_ARMOR3)) + quakedef.IT_ARMOR3
            if v > 100:
                host.host_client.edict.v.armortype = 0.6
                host.host_client.edict.v.armorvalue = v
                host.host_client.edict.v.items = host.host_client.edict.v.items - int(host.host_client.edict.v.items & int(quakedef.IT_ARMOR1 | quakedef.IT_ARMOR2 | quakedef.IT_ARMOR3)) + quakedef.IT_ARMOR2
            if v > 0:
                host.host_client.edict.v.armortype = 0.3
                host.host_client.edict.v.armorvalue = v
                host.host_client.edict.v.items = host.host_client.edict.v.items - int(host.host_client.edict.v.items & int(quakedef.IT_ARMOR1 | quakedef.IT_ARMOR2 | quakedef.IT_ARMOR3)) + quakedef.IT_ARMOR1


    match host.host_client.edict.v.weapon:
        case quakedef.IT_SHOTGUN | quakedef.IT_SUPER_SHOTGUN:
            host.host_client.edict.v.currentammo = host.host_client.edict.v.ammo_shells
        case quakedef.IT_NAILGUN | quakedef.IT_SUPER_NAILGUN | quakedef.RIT_LAVA_SUPER_NAILGUN:
            host.host_client.edict.v.currentammo = host.host_client.edict.v.ammo_nails
        case quakedef.IT_GRENADE_LAUNCHER | quakedef.IT_ROCKET_LAUNCHER | quakedef.RIT_MULTI_GRENADE | quakedef.RIT_MULTI_ROCKET:
            host.host_client.edict.v.currentammo = host.host_client.edict.v.ammo_rockets
        case quakedef.IT_LIGHTNING | quakedef.HIT_LASER_CANNON | quakedef.HIT_MJOLNIR:
            host.host_client.edict.v.currentammo = host.host_client.edict.v.ammo_cells
        case quakedef.RIT_LAVA_NAILGUN:
            if common.rogue:
                host.host_client.edict.v.currentammo = host.host_client.edict.v.ammo_nails

        case quakedef.RIT_PLASMA_GUN:
            if common.rogue:
                host.host_client.edict.v.currentammo = host.host_client.edict.v.ammo_cells
            if common.hipnotic:
                host.host_client.edict.v.currentammo = host.host_client.edict.v.ammo_rockets


def FindViewThing() -> progs.edict_t:
    for i in range(sv_main.sv.num_edicts):
        e: progs.edict_t = pr_edict.EDICT_NUM(i)
        if pr_edict.PR_GetString(e.v.classname) == 'viewthing':
            return e
    console.Con_Printf('No viewthing on map')
    return None


def Host_Resetdemos():
    cl_main.cls.demos = []
    cl_main.cls.demonum = 0


def Host_Startdemos_f():
    if cl_main.cls.state == cl_main.cactive_t.ca_dedicated:
        return

    c = _cmd.Cmd_Argc() - 1
    if c > quakedef.MAX_DEMOS:
        console.Con_Printf(f'max {quakedef.MAX_DEMOS} demos in demoloop')
        c = quakedef.MAX_DEMOS

    console.Con_Printf(f'{c} demos in loop')

    cl_main.cls.demos = [_cmd.Cmd_Argv(i) for i in range(1, c+1)]

    import cvar
    cl_startdemos = int(cvar.Cvar_GetCvar('cl_startdemos').value)
    if not sv_main.sv.active and cl_main.cls.demonum != -1 and not cl_main.cls.demoplayback:
        cl_main.cls.demonum = 0
        if not common.fitzmode and not cl_startdemos:
            cl_main.cls.demonum = -1
            _cmd.Cbuf_InsertText('menu_main\n')
            return
        cl_main.CL_NextDemo()
    else:
        cl_main.cls.demonum = -1

def Host_Demos_f():
    if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
        return
    if cl_main.cls.demonum == -1:
        cl_main.cls.demonum = 1
    cl_main.CL_Disconnect_f()
    cl_main.CL_NextDemo()

def Host_Stopdemo_f():
    if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
        return
    if not cl_main.cls.demoplayback:
        return
    cl_demo.CL_StopPlayback()
    cl_main.CL_Disconnect()

def Host_Viewmodel_f():
    e: progs.edict_t = FindViewThing()
    if not e:
        return

    m: quakedef.qmodel_t = gl_model.Mod_ForName(_cmd.Cmd_Argv(1))
    if not m:
        console.Con_Printf(f'Cant load {_cmd.Cmd_Argv(1)}')
        return

    e.v.frame = 0
    cl_main.cl.model_precache[int(e.v.modelindex)] = m

def Host_Viewframe_f():
    e:progs.edict_t = FindViewThing()
    if not e:
        return
    m: quakedef.qmodel_t = cl_main.cl.model_precache[int(e.v.modelindex)]

    f = int(_cmd.Cmd_Argv(1))
    if f >= m.numframes:
        f = m.numframes - 1

    e.v.frame = f

def PrintFrameName(m: quakedef.qmodel_t, frame: int):
    hdr: quakedef.aliashdr_t = gl_model.Mod_Extradata(m)
    if not hdr:
        return

    pframedesc: quakedef.maliasframedesc_t = hdr.frames[frame]
    console.Con_Printf(f'frame {frame}: {pframedesc.name}')


def Host_Viewnext_f():
    e: progs.edict_t = FindViewThing()
    if not e:
        return

    m: quakedef.qmodel_t = cl_main.cl.model_precache[int(e.v.modelindex)]

    e.v.frame = e.v.frame + 1
    if e.v.frame >= m.numframes:
        e.v.frame = m.numframes - 1

    PrintFrameName(m, e.v.frame)



def Host_Viewprev_f():
    e: progs.edict_t = FindViewThing()
    if not e:
        return

    m: quakedef.qmodel_t = cl_main.cl.model_precache[int(e.v.modelindex)]

    e.v.frame = e.v.frame - 1

    e.v.frame = max(e.v.frame, 0)

    PrintFrameName(m, e.v.frame)




def Host_InitCommands():
    _cmd.Cmd_AddCommand('maps', Host_Maps_f)
    _cmd.Cmd_AddCommand('maps_mod', Host_Maps_Mod_f)
    _cmd.Cmd_AddCommand('mods', Host_Mods_f)
    _cmd.Cmd_AddCommand('games', Host_Mods_f)
    _cmd.Cmd_AddCommand('mapname', Host_Mapname_f)
    _cmd.Cmd_AddCommand('randmap', Host_Randmap_f)

    _cmd.Cmd_AddCommand('status', Host_Status_f)
    _cmd.Cmd_AddCommand('quit', Host_Quit_f)
    _cmd.Cmd_AddCommand('god', Host_God_f)
    _cmd.Cmd_AddCommand('notarget', host_cmd.Host_Notarget_f)
    _cmd.Cmd_AddCommand('fly', Host_Fly_f)
    _cmd.Cmd_AddCommand('map', Host_Map_f)
    _cmd.Cmd_AddCommand('restart', Host_Restart_f)
    _cmd.Cmd_AddCommand('changelevel', Host_Changelevel_f)
    _cmd.Cmd_AddCommand('connect', Host_Connect_f)
    _cmd.Cmd_AddCommand('reconnect', Host_Reconnect_f)
    _cmd.Cmd_AddCommand('name', Host_Name_f)
    _cmd.Cmd_AddCommand('noclip', Host_Noclip_f)
    _cmd.Cmd_AddCommand('setpos', Host_SetPos_f)

    _cmd.Cmd_AddCommand('say', Host_Say_f)
    _cmd.Cmd_AddCommand('say_team', Host_Say_Team_f)
    _cmd.Cmd_AddCommand('tell', Host_Tell_f)
    _cmd.Cmd_AddCommand('color', Host_Color_f)
    _cmd.Cmd_AddCommand('kill', Host_Kill_f)
    _cmd.Cmd_AddCommand('pause', Host_Pause_f)
    _cmd.Cmd_AddCommand('spawn', Host_Spawn_f)
    _cmd.Cmd_AddCommand('begin', Host_Begin_f)
    _cmd.Cmd_AddCommand('prespawn', Host_PreSpawn_f)
    _cmd.Cmd_AddCommand('kick', Host_Kick_f)
    _cmd.Cmd_AddCommand('ping', Host_Ping_f)
    _cmd.Cmd_AddCommand('load', Host_Loadgame_f)
    _cmd.Cmd_AddCommand('save', Host_Savegame_f)
    _cmd.Cmd_AddCommand('give', Host_Give_f)

    _cmd.Cmd_AddCommand('startdemos', Host_Startdemos_f)
    _cmd.Cmd_AddCommand('demos', Host_Demos_f)
    _cmd.Cmd_AddCommand('stopdemo', Host_Stopdemo_f)

    _cmd.Cmd_AddCommand('viewmodel', Host_Viewmodel_f)
    _cmd.Cmd_AddCommand('viewframe', Host_Viewframe_f)
    _cmd.Cmd_AddCommand('viewnext', Host_Viewnext_f)
    _cmd.Cmd_AddCommand('viewprev', Host_Viewprev_f)


def ExtraMaps_Init():
    mapname = ''
    search = common.com_searchpaths
    while search:
        if search.filename:
            filestring = f'{search.filename}/maps/'
            try:
                dir_p = os.listdir(filestring)
            except:
                search = search.next
                continue

            if not dir_p:
                search = search.next
                continue

            for file in dir_p:
                if not file.endswith('.bsp'):
                    continue
                file = common.COM_StripExtension(file)
                ExtraMaps_Add(file, search.path_id)
        else: # pakfile
            if search.path_id != 1:
                for i in range(search.pack.numfiles):
                    if common.COM_FileGetExtension(search.pack.files[i].name) == 'bsp':
                        mapname = common.COM_StripExtension(search.pack.files[i].name)
                        ExtraMaps_Add(mapname, extralevels, search.path_id)

        search = search.next



def ModList_Init() -> None:
    """Scans the game base directory for valid mod folders and adds them to the mod list.

    C equivalent snippet from host_cmd.c / menu.c:
    void ModList_Init (void)
    """
    dir_string = common.com_basedir

    if not os.path.isdir(dir_string):
        return

    try:
        with os.scandir(dir_string) as entries:
            for entry in entries:
                # 1. Skip non-directory entries and hidden folders (. and .. handled automatically by scandir)
                if not entry.is_dir() or entry.name.startswith('.'):
                    continue

                # 2. Skip macOS application packages (.app)
                if common.COM_FileGetExtension(entry.name).casefold() == 'app':
                    continue

                # 3. Check if the directory is a valid Quake mod directory
                mod_path = entry.path
                if _IsValidModDir(mod_path):
                    Modlist_Add(entry.name)

    except (OSError, PermissionError):
        pass


def _IsValidModDir(mod_path: str) -> bool:
    """Validates whether a directory qualifies as a Quake mod directory

    by checking for .pak files or a maps/ subdirectory.
    """
    try:
        with os.scandir(mod_path) as sub_entries:
            for sub_entry in sub_entries:
                ext = common.COM_FileGetExtension(sub_entry.name).casefold()
                # Mod contains .pak files
                if ext == 'pak':
                    return True
                # Mod contains a maps subdirectory
                if sub_entry.is_dir() and sub_entry.name.casefold() == 'maps':
                    return True
    except (OSError, PermissionError):
        return False

    return False


def DemoList_Clear():
    FileList_Clear(demolist)

def DemoList_Rebuild():
    DemoList_Clear()
    DemoList_Init()


def DemoList_Init():
    demname = ''
    search = common.com_searchpaths
    while search:
        if search.filename:
            filestring = f'{search.filename}'
            try:
                dir_p = os.listdir(filestring)
            except:
                search = search.next
                continue

            if not dir_p:
                search = search.next
                continue

            for file in dir_p:
                if not file.endswith('.dem'):
                    continue

                file = common.COM_StripExtension(file)
                FileList_Add(demname, demolist, search.path_id)
        else: # pakfile
            if search.path_id != 1:
                for i in range(search.pack.numfiles):
                    if common.COM_FileGetExtension(search.pack.files[i].name) == 'dem':
                        demname = common.COM_StripExtension(search.pack.files[i].name)
                        FileList_Add(demname, demolist, search.path_id)

        search = search.next

def Host_Mods_f():
    mod: filelist_item_t = modlist

    i = 0
    while mod:
        console.Con_Printf(f'   {mod.name}')
        i += 1
    if i:
        console.Con_Printf(f'{i} mods found')
    else:
        console.Con_Printf('no mods found')


def Host_SyncExternalFS():
    pass