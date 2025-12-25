#host_cmd.py

import os

import cl_main
import client
import console
import common
import sv_main
import menu
import _cmd
import net_main
import host
import quakedef
import host_cmd
import keys
import sys_sdl_unix

class filelist_item_t:
    def __init__(self, name, path_id, next: filelist_item_t):
        self.name = name
        self.path_id = path_id
        self.next = next

modlist : filelist_item_t = None
extralevels: filelist_item_t = None
demolist : filelist_item_t = None


def FileList_Add(name, _list: filelist_item_t, path_id):
    item = _list

    while item:
        if name == item.name:
            return
        item = item.next

    item = filelist_item_t(name, path_id, None)

    if _list is None:
        _list = item
    else:
        _list.next = item

def ExtraMaps_Add(name, _list: filelist_item_t, path_id):
    FileList_Add(name, _list, path_id)

def Host_Maps_f():
    if _cmd.Cmd_Argc() > 1:
        ExtraMaps_List(Cmd_Argv(1))
    else:
        ExtraMaps_List(None)

def Host_Maps_Mod_f():
    ExtraMaps_List(common.COM_SkipPath(common.com_gamedir))

def Host_Mods_f():
    mod = modlist
    count = 0
    while True:
        if not mod:
            break
        count += 1
        console.Con_Printf(f'   {mod.name}')
        mod = mod.next

    console.Con_Printf(f'{count} mods found')

def Host_Mapname_f():
    if sv_main.sv.active:
        console.Con_Printf(f'mapname is {sv_main.sv.name}')
        return

    if cl_main.cls.state == ca_connected:
        console.Con_Printf(f'mapname is {cl_main.cl.mapname}')

    console.Con_Printf('no map loaded')


def Host_Randmap_f():
    raise NotImplementedError

    if _cmd.cmd_source != src_command:
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

    if tcpipAvailable:
        print_fn(f'tcp/ip:   {net_main.my_tcpip_address}')

    print_fn(f'map:    {sv.name}')
    print_fn(f'players: {net_activeconnections} active ({svs.maxclients} max) ')

    j = 1
    for client in svs.clients:
        if not client.active:
            continue

        seconds = int(net_time - NET_QSocketGetTime(client.netconnection))
        minutes = seconds / 60

        if minutes:
            seconds -= ( minutes * 60)
            hours = minutes / 60
            if hours:
                minutes -= (hours * 60)
        else:
            hours = 0

        print_fn(f'{j} {client.name} {client.edict.v.frags} {hours}:{minutes}:{seconds}' )

        print_fn(f'{NET_QSocketGetAddressString(client.netconnection)}')

def Host_Quit_f():
    if keys.key_dest != keys.keydest_t.key_console and client.cls.state != client.cactive_t.ca_dedicated:
        menu.M_Menu_Quit_f()
        return

    cl_main.CL_Disconnect()
    #host.Host_ShutdownServer(False)

    sys_sdl_unix.Sys_Quit()

def Host_God_f():
    if _cmd.cmd == src_command:
        Cmd_ForwardToServer()
        return

    if pr_global_struct.deathmatch:
        return

    match Cmd_Arvc():
        case 1:
            sv_player.v.flags = int(sv_player.v.flags) ^ FL_GODMODE
            if int(sv_player.v.flags) & FL_GODMODE:
                SV_ClientPrintf('godmode ON\n')
            else:
                SV_ClientPrintf('godmode OFF')
        case 2:
            if Cmd_Argv(1) == 1:
                sv_player.v.flags = sv_player.v.flags | FL_GODMODE
                SV_ClientPrintf('godmode ON\n')
            else:
                sv_player.v.flags = sv_player.v.flags & ~FL_GODMODE
                SV_ClientPrintf('godmode OFF\n')
        case _:
            console.Con_Printf('god [value] : toggle god mode 0=off, 1=on\n')

def Host_Notarget_f():

    if _cmd.cmd == src_command:
        Cmd_ForwardToServer()
        return

    if pr_global_struct.deathmatch:
        return

    match Cmd_Arvc():
        case 1:
            sv_player.v.flags = int(sv_player.v.flags) ^ FL_NOTARGET
            if int(sv_player.v.flags) & FL_NOTARGET:
                SV_ClientPrintf('notarget ON\n')
            else:
                SV_ClientPrintf('notarget OFF')
        case 2:
            if Cmd_Argv(1) == 1:
                sv_player.v.flags = sv_player.v.flags | FL_NOTARGET
                SV_ClientPrintf('notarget ON\n')
            else:
                sv_player.v.flags = sv_player.v.flags & ~FL_NOTARGET
                SV_ClientPrintf('notarget OFF\n')
        case _:
            console.Con_Printf('notarget [value] : toggle notarget mode 0=off, 1=on\n')

def Host_Fly_f():
    if _cmd.cmd == src_command:
        Cmd_ForwardToServer()
        return

    if pr_global_struct.deathmatch:
        return

    match (Cmd_Argc):
        case 1:
            if sv_player.v.movetype != MOVETYPE_FLY:
                sv_player.v.movetype = MOVETYPE_FLY
                SV_ClientPrintf('flymode ON\n')
            else:
                sv_player.v.movetype = MOVETYPE_WALK
                SV_ClientPrintf('flymode OFF\n')
        case 2:
            if Cmd_Argv(1):
                sv_player.v.movetype = MOVETYPE_FLY
                SV_ClientPrintf('flymode ON\n')
            else:
                sv_player.v.movetype = MOVETYPE_WALK
                SV_ClientPrintf('flymode OFF\n')
        case _:
            console.Con_Printf('fly [value] : toggle fly mode. values 0=off, 1=on\n')

def Host_Map_f():
    if Cmd_Argc() < 2:
        if cls.state == ca_dedicated:
            if sv.active:
                console.Con_Printf(f'Current map {sv.name}')
            else:
                console.Con_Printf('server not active')
        elif cls.state == ca_connected:
            console.Con_Printf(f'Current map {cl.levelname} {cl.mapname}')
        else:
            console.Con_Printf('map <levelname>: start a new server')
        return

    if _cmd.cmd != src_command:
        return

    cls.demonum = -1

    CL_Disconnect()
    Host_ShutdownServer(False)

    if cls.state != ca_dedicated:
        IN_Activate()

    key_dest = key_game
    SCR_BeginLoadingPlaque()

    svs.serverflags = 0
    name = Cmd_Argv(1)

    name.strip('.bsp')

    SV_SpawnServer(name)

    if not sv_active:
        return

    if cls.state != ca_dedicated:
        for i in range (Cmd_Argc()):
            cls.spawnparms += Cmd_Argv(i)
        Cmd_ExecuteString ('connect local', src_command)


def Host_Restart_f():

    if cls.demoplayback or not sv.active:
        return

    if _cmd.cmd_source != src_command:
        return

    SV_SpawnServer(sv.name)

    if not sv.active:
        Host_Error(f'cannot restart map {sv.name}')


def Host_Changelevel_f():
    if Cmd_Argc() != 2:
        console.Con_Printf('changelevel <levelname> : continue game on a new level\n')
        return

    if not sv.active or cls.demoplayback:
        console.Con_Printf('only the server may changelevel\n')
        return

    level = f'maps/{Cmd_Argv(1)}.bsp'

    if not COM_FileExists(level, None):
        Host_Error(f'cannot find map {level}')

    if cls.state != ca_dedicated:
        IN_Activate()

    key_dest = key_game
    SV_SaveSpawnparms()

    level = Cmd_Argv(1)
    SV_SpawnServer(level)

    if not sv.active:
        Host_Error(f'cannot run map {level}')


def Host_Connect_f():
    cls.demonum = -1

    if cls.demoplayback:
        CL_StopPlayback()
        CL_Disconnect()

    CL_EstablishConnection(Cmd_Argv(1))
    Host_Reconnect_f()

def Host_Reconnect_f():
    if cls.demoplayback:
        return

    SCR_BeginLoadingPlaque()
    CL_ClearSignons()


def Host_Name_f():
    newName = ''
    if Cmd_Argc() == 1:
        console.Con_Printf(f'name is {cl_name.string}')
        return

    if Cmd_Argc() == 2:
        newName = Cmd_Argv(1)
    else:
        newName = Cmd_Args()

    if _cmd.cmd_source == src_command:
        if cl_name.string == newName:
            return

        Cvar_Set('_cl_name', newName)

        if cls.state == ca_connected:
            Cmd_ForwardToServer()
        return

    if host_client.name and host_client.name == 'unconnected':
        if host_client.name != newName:
            console.Con_Printf(f'{host_client.name} renamed to {newName}')

    host_client.name = newName
    host_client.edict.v.netname = PR_SetEngineString(host_client.name)

    MSG_WriteByte(sv.reliable_datagram, svc_updatename)
    MSG_WriteByte(sv.reliable_datagram, host_client - svs.clients) # TODO how to do this???
    MSG_WriteString(sv.reliable_datagram, host_client.name)

def Host_Noclip_f():
    if _cmd.cmd_source == src_command:
        Cmd_ForwardToServer()
        return

    if pr_global_struct.deathmatch:
        return

    match Cmd_Argc():
        case 1:
            if sv_player.v.movetype != MOVETYPE_NOCLIP:
                noclip_anglehack = True
                sv_player.v.movetype = MOVETYPE_NOCLIP
                SV_ClientPrintf('noclip ON\n')

            else:
                noclip_anglehack = False
                sv_player.v.movetype = MOVETYPE_WALK
                SV_ClientPrintf('noclip OFF\n')
        case 2:
            if Cmd_Argv(1):
                noclip_anglehack = True
                sv_player.v.movetype = MOVETYPE_NOCLIP
                SV_ClientPrintf('noclip ON\n')
            else:
                noclip_anglehack = False
                sv_player.v.movetyhpe = MOVETYPE_WALK
                SV_ClientPrintf('noclip OFF\n')
        case _:
            console.Con_Printf('noclip [0/1]')

def Host_SetPos_f():
    raise NotImplementedError

def Host_Say_f():
    Host_Say(False)

def Host_Say_Team_f():
    Host_Say(True)

def Host_Tell_f():
    if _cmd.cmd_source == src_command:
        Cmd_ForwardToServer()
        return

    if Cmd_Argc() < 3:
        return

    text = Cmd_Args()
    text = text.replace('"', '').replace('\n', '').replace('\r', '')

    text = f'{host_client.name}: {text}'

    save = host_client

    for client in svs.clients:
        if not client.active or not client.spawned:
            continue
        if client.name != Cmd_Argv(1):
            continue

        host_client = client
        SV_ClientPrintf(text)
        break

    host_client = save

def Host_Color_f():
    raise NotImplementedError
    pass

def Host_Kill_f():
    if _cmd.cmd_source == src_command:
        Cmd_ForwardToServer()
        return

    if sv_player.v.health <= 0:
        SV_ClientPrintf('cant suicide -- already dead\n')
        return

    pr_global_struct.time = sv_time
    pr_global_struct.self = EDICT_TO_PROG(sv_player)
    PR_ExecuteProgram(pr_global_struct.ClientKill)

def Host_Pause_f():
    if cls.demoplayback:
        cls.demopaused = not cls.demopaused
        cl.paused = cls.demopaused
        return

    if _cmd.cmd_source == src_command:
        Cmd_ForwardToServer()
        return

    if not pausable.value:
        SV_ClientPrintf('Pause not allowed\n')
    else:
        sv.paused ^= 1

        if sv.paused:
            SV_BroadcastPrintf(f'{PR_GetString(sv_player.v.netname)} paused the game\n')
        else:
            SV_BroadcastPrintf(f'{PR_GetString(sv_player.v.netname)} unpaused the game\n')

        MSG_WriteByte(sv.reliable_datagram, svc_setpause)
        MSG_WriteByte(sv.reliable_datagram, sv.paused)

def Host_Spawn_f():
    raise NotImplementedError

    ent: edict_t = None
    if _cmd.cmd_source == src_command:
        console.Con_Printf('spawn not valid from console\n')
        return

    if host_client.spawned:
        console.Con_Printf('spawn not valid, already spawned\n')

    if sv.loadgame:
        sv.paused = False
    else:
        ent = host_client.edict
        # left off here for this function

def Host_Begin_f():
    if _cmd.cmd_source == src_command:
        console.Con_Printf('begin not valid from console\n')
        return

    host_client.spawned = True


def Host_PreSpawn_f():
    if _cmd.cmd_source == src_command:
        console.Con_Printf('prespawn not available from console\n')
        return

    if host_client.spawned:
        console.Con_Printf('prespawn not valid, already spawned\n')
        return

    host_client.sendsignon = PRESPAWN_SIGNONBUFS
    host_client.signonidx = 0


def Host_Kick_f():
    who = ''
    byNumber = False
    if _cmd.cmd_source == src_command:
        if not sv.active:
            Cmd_ForwardToServer()
            return

    elif pr_global_struct.deathmath:
        return

    save = host_client

    i = 0

    if Cmd_Argc() > 2 and Cmd_Argv(1) == '#':
        i = int(Cmd_Argv(2)) - 1

        if i < 0 or i >= svs.maxclients:
            return
        if not svs.clients[i].active:
            return
        host_client = svs.clients[i]
        byNumber = True
    else:
        for host_client in svs.clients:
            if not host_client.active:
                continue
            if host_client.name == Cmd_Argv(1):
                break

    if i < svs.maxclients:
        if _cmd.cmd_source == src_command:
            if cls.state == ca_dedicated:
                who = 'Console'
            else:
                who = cl_name.string
        else:
            who = save.name

        if host_client is save: # if id(host_client) == id(save) ????
            return

        if Cmd_Argc() > 2:
            message = COM_Parse(Cmd_())

            if byNumber:
                message = message[1:]
                message.lstrip()

                message = message[len(Cmd_Argv(2)):]

                message.lstrip()

        if len(message):
            SV_ClientPrintf(f'kicked by {who} {message}')
        else:
            SV_ClientPrintf(f'kicked by {who}')

        SV_DropClient(False)

    host_client = save

def Host_Ping_f():
    if _cmd.cmd_source == src_command:
        Cmd_ForwardToServer()
        return

    SV_ClientPrintf('client ping times:\n')

    for client in svs.clients:
        if not client.active:
            continue

        for j in client.ping_times:
            total += client.ping_times

        total /= NUM_PING_TIMES

        SV_ClientPrintf(f'{total*1000} {client.name}')

def Host_Loadgame_f():
    if _cmd.cmd_source == src_command:
        return

    if Cmd_Argc() != 2:
        console.Con_Printf('load <savename> : load a game\n')
        return

    if Cmd_Argv(1).contains('..'):
        console.Con_Printf('load <savename> : relative pathnames are not allowed\n')
        return

    if nomonsters.value:
        console.Con_Warning(f'{nomonsters.name} disabled automatically\n')
        cvar.Cvar_SetValueQuick(nomonsters, 0.0)

    cls.demonum = -1

    name = f'{com_gamedir}/{Cmd_Argv(1)}'
    COM_AddExtension(name, '.sav')

    # disabled in original source
    #SCR_BeginLoadingPlaque()

    console.Con_Printf(f'loading game from {name}\n')

    if start:
        start = None

    start, _ = COM_LoadMallocFile_TextMode_OSPath(name) # name, NULL

    if start is None:
        console.Con_Printf(f'Error: could not open savegame {name}\n')
        return

    data = start
    data, version = COM_ParseIntNewline(data) # data, version

    if version != SAVEGAME_VERSION: # 5
        start = None
        Host_Error(f'savegame is version {version} not {SAVEGAME_VERSION}\n')
        return

    data = COM_ParseIntNewline(data)

    for i in range(NUM_SPAWN_PARMS):
        data, spawn_parms[i] = COM_ParseFloatNewline(data) # data, &spawn_parms[i]

    data, current_skill = COM_ParseFloatNewline(data) # data, &tfloat ( current_skill )
    Cvar_SetValue('skill', current_skill)

    data = COM_ParseStringNewline(data)
    mapname = com_token # TODO q_strlcpy ( mapname, com_token, sizeof mapname)
    data, time = COM_ParseFloatNewline(data)

    CL_Disconnect_f()

    SV_SpawnServer(mapname)

    if not sv.active:
        start = None
        SCR_EndLoadingPlaque()
        console.Con_Printf(f'couldnt load map {mapname}\n')

    sv.paused = True
    sv.loadgame = True

    for i in range(MAX_LIGHTSTYLES):
        data = COM_ParseStringNewline(data)
        com_token = 'lightstyles'
        sv.lightstyles[i] = com_token

    entnum = -1

    while(data):
        data = COM_Parse(data)

        if com_token == '':
            break

        if com_token != '{':
            Host_Error('first token isnt a brace')

        if entnum == -1:
            data = ED_ParseGlobals(data)
        else:
            ent = EDICT_NUM(entnum)
            if entnum < sv.num_edicts:
                ent.free = False
                ent.v = [] # Array(progs.entityfields * 4) # TODO may have to implement fixedsize array
            else:
                ent.baseline.scale = ENTSCALE_DEFAULT

            data, ent = ED_ParseEdict(data)

            if not ent.free:
                SV_LinkEdict(ent, False)

        entnum += 1


    for i in range(sv.num_edicts):
        ED_Free(EDICT_NUM(i))

    sv.num_edicts = entnum
    sv.time = time

    start = None

    for i in range(NUM_SPAWN_PARMS):
        svs.client.spawn_parms[i] = spawn_parms[i]

    if cls.state != ca_dedicated:
        CL_EstablishConnection('local')
        Host_Reconnect_f()

    if cls.state != ca_dedicated:
        IN_Activate()


def Host_Savegame_f():
    name = ''
    comment = ''

    if _cmd.cmd_source != src_command:
        return

    if not sv.active:
        console.Con_Printf('not playing a local game\n')
        return

    if sv.nomonsters:
        console.Con_Printf('cant save when using nomonsters\n')
        return

    if cl.intermission:
        console.Con_Printf('cant save in an intermission\n')
        return

    if svs.maxclients != 1:
        console.Con_Printf('cant save multiplayer games\n')
        return

    if Cmd_Argc() != 2:
        console.Con_Printf('save <savename> : save a game\n')
        return

    if '..' in Cmd_Argv(1):
        console.Con_Printf('relative pathname are not allowed\n')
        return

    for client in svs.maxclients:
        if client.active and client.edict.v.health <= 0:
            console.Con_Printf('cant save game with dead player\n')
            return

    name = f'{com_gamedir}/{Cmd_Argv(1)}'
    name += '.sav' #COM_AddExtension(name, '.sav')

    console.Con_Printf(f'saving game to {name}\n')

    try:
        file = open(name, 'w')
    except:
        console.Con_Printf('couldnt open save file')
        return

    file.write(f'{SAVEGAME}\n')
    Host_SavegameComment(comment)
    file.write(f'{comment}\n')

    for i in range(NUM_SPAWN_PARMS):
        file.write(f'{svs.client.spawn_parms[i]}\n')

    file.write(f'{current_skill}\n')
    file.write(f'{sv.name}\n')
    file.write(f'{sv.time}\n')

    for i in range(MAX_LIGHTSTYLES):
        if sv.lightstyles[i]:
            file.write(f'{sv.lightstyles[i]}\n')
        else:
            file.write('m\n')

    ED_WriteGlobals(file)

    for i in range(sv.num_edicts):
        ED_Write(file, EDICT_NUM(i))

    file.close()
    console.Con_Printf('done\n')


def Host_Give_f():
    if _cmd.cmd_source == _cmd.cmd_source.src_command:
        Cmd_ForwardToServer()
        return

    if pr_global_struct.deathmatch:
        return

    t = Cmd_Argv(1)
    v = int(Cmd_Argv(2))

    match(t[0]):
        case x if 0 <= x <= 9:
            if hipnotic:
                if t[0] == '6':
                    if t[1] == 'a':
                        sv_player.v.items = sv_player.v.items | quakedef.HIT_PROXIMITY_GUN
                    else:
                        sv_player.v.items = sv_player.v.items | quakedef.IT_GRENADE_LAUNCHER
                elif t[0] == '9':
                    sv_player.v.items |= quakedef.HIT_LASER_CANNON
                elif t[0] == '0':
                    sv_player.v.items |= quakedef.HIT_MJOLNIR
                elif t[0] == '2':
                    sv_player.v.items = sv_player.v.items | ( quakedef.IT_SHOTGUN << (int(t[0]) - 2))

            else:
                if t[0] >= '2':
                    sv_player.v.items = sv_player.v.items | ( quakedef.IT_SHOTGUN << (int(t[0]) - 2))
        case 's':
            if rogue:
                val = GetEdictFieldValue(sv_player, 'ammo_shells1')
                if val:
                    val.float = v

            sv_player.v.ammo_shells1 = v
        case 'n':
            if rogue:
                val = GetEdictFieldValue(sv_player, 'ammo_nails1')
                if val:
                    val.float = v
                    if sv_player.v.weapon <= quakedef.IT_LIGHTNING:
                        sv_player.v.ammo_nails = v

            else:
                sv_player.v.ammo_nails = v

        case 'l':
            if rogue:
                val = GetEdictFieldValue(sv_player, 'ammo_lava_nails')
                if val:
                    val.float = v
                    if sv_player.v.weapon > quakedef.IT_LIGHTNING:
                        sv_player.v.ammo_nails = v
        case 'r':
            if rogue:
                val = GetEdictFieldValue(sv_player, 'ammo_rockets')
                if val:
                    val.float = v
                    if sv_player.v.weapon <= quakedef.IT_LIGHTNING:
                        sv_player.v.ammo_rockets = v
            else:
                sv_player.v.ammo_rockets = v
        case 'm':
            if rogue:
                val = GetEdictFieldValue(sv_player, 'ammo_multi_rockets')
                if val:
                    val.float = v
                    if sv_player.v.weapon > quakedef.IT_LIGHTNING:
                        sv_player.v.ammo_rockets = v
        case 'h':
            sv_player.v.health = v

        case 'c':
            if rogue:
                val = GetEdictFieldValue(sv_player, 'ammo_cells')
                if val:
                    val.float = v
                    if sv_player.v.weapon <= quakedef.IT_LIGHTNING:
                        sv_player.v.ammo_cells = v
            else:
                sv_player.v.ammo_cells = v

        case 'p':
            if rogue:
                val = GetEdictFieldValue(sv_player, 'ammo_plasma')
                if val:
                    val.float = v
                    if sv_player.v.weapon > quakedef.IT_LIGHTNING:
                        sv_player.v.ammo_cells = v

        case 'a':
            if v > 150:
                sv_player.v.armortype = 0.8
                sv_player.v.armorvalue = v
                sv_player.v.items = sv_player.v.items - int(sv_player.v.items & int(quakedef.IT_ARMOR1 | quakedef.IT_ARMOR2 | quakedef.IT_ARMOR3)) + quakedef.IT_ARMOR3
            if v > 100:
                sv_player.v.armortype = 0.6
                sv_player.v.armorvalue = v
                sv_player.v.items = sv_player.v.items - int(sv_player.v.items & int(quakedef.IT_ARMOR1 | quakedef.IT_ARMOR2 | quakedef.IT_ARMOR3)) + quakedef.IT_ARMOR2
            if v > 0:
                sv_player.v.armortype = 0.3
                sv_player.v.armorvalue = v
                sv_player.v.items = sv_player.v.items - int(sv_player.v.items & int(quakedef.IT_ARMOR1 | quakedef.IT_ARMOR2 | quakedef.IT_ARMOR3)) + quakedef.IT_ARMOR1


    match sv_player.v.weapon:
        case quakedef.IT_SHOTGUN | quakedef.IT_SUPER_SHOTGUN:
            sv_player.v.currentammo = sv_player.v.ammo_shells
        case quakedef.IT_NAILGUN | quakedef.IT_SUPER_NAILGUN | quakedef.RIT_LAVA_SUPER_NAILGUN:
            sv_player.v.currentammo = sv_player.v.ammo_nails
        case quakedef.IT_GRENADE_LAUNCHER | quakedef.IT_ROCKET_LAUNCHER | quakedef.RIT_MULTI_GRENADE | quakedef.RIT_MULTI_ROCKET:
            sv_player.v.currentammo = sv_player.v.ammo_rockets
        case quakedef.IT_LIGHTNING | quakedef.HIT_LASER_CANNON | quakedef.HIT_MJOLNIR:
            sv_player.v.currentammo = sv_player.v.ammo_cells
        case quakedef.RIT_LAVA_NAILGUN:
            if rogue:
                sv_player.v.currentammo = sv_player.v.ammo_nails

        case quakedef.RIT_PLASMA_GUN:
            if rogue:
                sv_player.v.currentammo = sv_player.v.ammo_cells
            if hipnotic:
                sv_player.v.currentammo = sv_player.v.ammo_rockets

def Host_Startdemos_f():
    if cl_main.cls.state == cl_main.cactive_t.ca_dedicated:
        return

    c = _cmd.Cmd_Argc() - 1
    if c > client.MAX_DEMOS:
        console.Con_Printf(f'max {client.MAX_DEMOS} demos in demoloop')
        c = client.MAX_DEMOS

    console.Con_Printf(f'{c} demos in loop')

    for i in range(1, c+1):
        cl_main.cls.demos.insert(i-1,_cmd.Cmd_Argv(i))

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
    if cls.state == ca_dedicated:
        return
    if cls.demonum == -1:
        cls.demonum = 1
    CL_Disconnect_f()
    CL_NextDemo()

def Host_Stopdemo_f():
    if cls.state == ca_dedicated:
        return
    if not cls.demoplayback:
        return
    CL_StopPlayback()
    CL_Disconnect()

def Host_Viewmodel_f():
    raise NotImplementedError

def Host_Viewframe_f():
    raise NotImplementedError

def Host_Viewnext_f():
    raise NotImplementedError

def Host_Viewprev_f():
    raise NotImplementedError

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


def ModList_Init():
    ''' not sure what this does '''
    return
    raise NotImplementedError

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

