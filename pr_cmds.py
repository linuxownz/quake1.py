#pr_cmds.py

import math
import random
import struct

import _cmd
import common
import console
import cvar
import gl_model
import glquake
import host
import mathlib
import pr_edict
import pr_exec
import progs
import protocol
import quakedef
import server
import sv_main
import sv_move
import world


# ---------------------------------------------------------------------------
# VM global accessors.
#
# pr_edict.pr_globals is the single source of truth. Entity, string, field and
# function slots hold ints; float slots hold floats. These read the list
# directly, so they do not depend on how progs.py converts between the two.
# ---------------------------------------------------------------------------
_gofs_cache = {'progz': None, 'map': {}}


def _gofs(name: str) -> int:
    """Offset of a named system global (v_forward, trace_ent, parm1, ...) from progs.dat."""
    c = _gofs_cache
    if c['progz'] is not pr_edict.progz:
        c['progz'] = pr_edict.progz
        c['map'] = {}
    ofs = c['map'].get(name)
    if ofs is None:
        d = pr_edict.ED_FindGlobal(name)
        if d is None:
            host.Host_Error(f'pr_cmds: global "{name}" not found in progs.dat')
            return 0
        ofs = d.ofs
        c['map'][name] = ofs
    return ofs


def _G_INT(ofs: int) -> int:
    return int(pr_edict.pr_globals[ofs])


def _G_FLOAT(ofs: int) -> float:
    return float(pr_edict.pr_globals[ofs])


def _G_VECTOR(ofs: int) -> list[float]:
    g = pr_edict.pr_globals
    return [float(g[ofs]), float(g[ofs + 1]), float(g[ofs + 2])]


def _G_STRING(ofs: int) -> str:
    return pr_edict.PR_GetString(int(pr_edict.pr_globals[ofs]))


def _G_EDICTNUM(ofs: int) -> int:
    return int(pr_edict.pr_globals[ofs])


def _G_EDICT(ofs: int):
    n = int(pr_edict.pr_globals[ofs])
    edicts = sv_main.sv.edicts
    if n < 0 or n >= len(edicts):
        pr_exec.PR_RunError(f'Bad entity reference {n}')
        return edicts[0]
    return edicts[n]


def _set_vec(ofs: int, v) -> None:
    g = pr_edict.pr_globals
    g[ofs] = float(v[0])
    g[ofs + 1] = float(v[1])
    g[ofs + 2] = float(v[2])


def _GV(name: str) -> list[float]:
    return _G_VECTOR(_gofs(name))

STRINGTEMP_BUFFERS = 16
STRINGTEMP_LENGTH  = 1024

pr_string_tempindex = 0

pr_string_temp: list[bytearray] = [
    bytearray(STRINGTEMP_LENGTH) for _ in range(STRINGTEMP_BUFFERS)
]

MSG_BROADCAST = 0
MSG_ONE       = 1
MSG_ALL       = 2
MSG_INIT      = 3

checkpvs: bytearray = bytearray()
checkpvs_capacity = 0

c_invis: int = 0
c_notvis: int = 0
MAX_CHECK = 16

def PR_GetTempString() -> str:
    global pr_string_tempindex
    pr_string_tempindex += 1
    offset = ( STRINGTEMP_BUFFERS - 1) & pr_string_tempindex
    pr_string_temp[0] = '\0'
    return pr_string_temp[offset]


def RETURN_EDICT(e: progs.edict_t):
    # Entity references are int words in the VM (no float bit-casting)
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = pr_edict.EDICT_TO_PROG(e)


def PF_GetStringArg(idx: int, userdata=None) -> str:
    if userdata is not None:
        idx += int(userdata)

    if idx < 0 or idx >= pr_exec.pr_argc:
        return ''

    raw_str = _G_STRING(pr_edict.OFS_PARM0 + idx * 3)
    if not raw_str:
        return ''

    return common.LOC_GetString(raw_str)


def PF_VarString(first: int) -> str:
    out: bytearray = bytearray(1024)
    pos = 0

    if first >= pr_exec.pr_argc:
        return ''

    # Get format string from progs string table
    format_str = _G_STRING(pr_edict.OFS_PARM0 + first * 3)

    if False and common.LOC_HasPlaceholders(format_str):  # noqa: SIM223
        offset = first + 1
        return common.LOC_Format(format_str, PF_GetStringArg, offset, out, 1024)

    pos = 0
    for i in range(first, pr_exec.pr_argc):
        string = _G_STRING(pr_edict.OFS_PARM0 + i * 3)

        if not string:
            continue

        encoded = string.encode('latin-1', errors='replace')
        enc_len = len(encoded)

        if pos + enc_len >= 1023:
            space_left = 1023 - pos
            if space_left > 0:
                out[pos:pos + space_left] = encoded[:space_left]
                pos += space_left
            console.Con_Warning('PF_VarString: overflow (string truncated)\n')
            break

        out[pos:pos + enc_len] = encoded
        pos += enc_len

    if pos > 255:  # noqa: SIM102
        if not host.dev_overflows.varstring or host.dev_overflows.varstring + glquake.CONSOLE_RESPAM_TIME < host.realtime:
            console.Con_DPrintf(f'PF_VarString: {pos} characters exceeds standard limit of 255 (max = 1023).\n')
            host.dev_overflows.varstring = host.realtime

    return out[:pos].decode('latin-1', errors='replace')

def PF_error():
    s = PF_VarString(0)
    fname = pr_edict.PR_GetString(pr_exec.pr_xfunction.s_name)
    ed = _G_EDICT(pr_edict.OFS_SELF)

    console.Con_Printf(f'=======SERVER ERROR in {fname}\n{s}\n')
    pr_edict.ED_Print(ed)

    host.Host_Error('Program error')

def PF_objerror():
    s = PF_VarString(0)
    fname = pr_edict.PR_GetString(pr_exec.pr_xfunction.s_name)
    ed = _G_EDICT(pr_edict.OFS_SELF)

    print("\n=================== ENGINE STATE DUMP ===================")
    print(f"Function : {fname}")
    print(f"Error Msg: {s}")
    print(f"Server State: {sv_main.sv.state}")

    if ed:
        #print(f"\n--- Triggering Edict (#{ed.num}) ---")
        classname_ofs = getattr(ed.v, 'classname', 0)
        targetname_ofs = getattr(ed.v, 'targetname', 0)
        noise_ofs = getattr(ed.v, 'noise', 0)
        model_ofs = getattr(ed.v, 'model', 0)

        print(f"classname  : {pr_edict.PR_GetString(classname_ofs)} (raw: {classname_ofs})")
        print(f"targetname : {pr_edict.PR_GetString(targetname_ofs)} (raw: {targetname_ofs})")
        print(f"noise      : {pr_edict.PR_GetString(noise_ofs)} (raw: {noise_ofs})")
        print(f"model      : {pr_edict.PR_GetString(model_ofs)} (raw: {model_ofs})")
        print(f"spawnflags : {getattr(ed.v, 'spawnflags', 0)}")

    print("\n--- Precached Sounds Dump (Non-Empty Slots) ---")
    for idx, snd in enumerate(sv_main.sv.sound_precache):
        if snd:
            print(f"  [{idx:3d}] -> '{snd}'")

    print("\n--- Precached Models Dump (Non-Empty Slots) ---")
    for idx, mdl in enumerate(sv_main.sv.model_precache):
        if mdl:
            print(f"  [{idx:3d}] -> '{mdl}'")

    print("========================================================\n")

    console.Con_Printf(f'=======OBJECT ERROR in {fname}\n{s}\n')
    pr_edict.ED_Print(ed)
    pr_edict.ED_Free(ed)

    host.Host_Error('Program error')

def PF_makevectors():
    angles = _G_VECTOR(pr_edict.OFS_PARM0)

    forward = [0.0, 0.0, 0.0]
    right = [0.0, 0.0, 0.0]
    up = [0.0, 0.0, 0.0]

    mathlib.AngleVectors(angles, forward, right, up)

    # Offsets come from progs.dat, not hard-coded numbers
    _set_vec(_gofs('v_forward'), forward)
    _set_vec(_gofs('v_right'), right)
    _set_vec(_gofs('v_up'), up)


def PF_setorigin():
    """Builtin #2: setorigin(entity e, vector org)"""
    e = _G_EDICT(pr_edict.OFS_PARM0)
    org = _G_VECTOR(pr_edict.OFS_PARM1)

    mathlib.VectorCopy(org, e.v.origin)
    # SV_LinkEdict itself ignores the world edict, as in C
    world.SV_LinkEdict(e, False)


def SetMinMaxSize(e: progs.edict_t, minvec: list[float], maxvec: list[float], rotate: bool):
    bounds: list[list[float]] = [[0.,0.,0.], [0.,0.,0.]]
    xvector: list[float] = [0, 0]
    yvector: list[float] = [0, 0]
    base: quakedef.vec3_t = [0, 0, 0]
    transformed: quakedef.vec3_t = [0, 0, 0]
    rmin: quakedef.vec3_t = [0, 0, 0]
    rmax: quakedef.vec3_t = [0, 0, 0]

    for i in range(3):
        if minvec[i] > maxvec[i]:
            pr_exec.PR_RunError('backwards mins/maxs')

    rotate = False

    if not rotate:
        mathlib.VectorCopy(minvec, rmin)
        mathlib.VectorCopy(maxvec, rmax)
    else:
        angles = e.v.angles
        a = angles[1]/180 * math.pi

        xvector[0] = math.cos(a)
        xvector[1] = math.sin(a)
        yvector[0] = -math.sin(a)
        yvector[1] = math.cos(a)

        mathlib.VectorCopy(minvec, bounds[0])
        mathlib.VectorCopy(maxvec, bounds[1])

        rmin[0] = rmin[1] = rmin[2] = mathlib.FLT_MAX
        rmax[0] = rmax[1] = rmax[2] = -mathlib.FLT_MAX

        for i in range(2):
            base[0] = bounds[i][0]
            for j in range(2):
                base[1] = bounds[j][1]
                for k in range(2):
                    base[2] = bounds[k][2]

                    transformed[0] = xvector[0]*base[0] + yvector[0]*base[1]
                    transformed[1] = xvector[1]*base[0] + yvector[1]*base[1]
                    transformed[2] = base[2]

                    for l in range(3):
                        rmin[l] = min(rmin[l], transformed[l])
                        rmax[l] = max(rmax[l], transformed[l])
    mathlib.VectorCopy(rmin, e.v.mins)
    mathlib.VectorCopy(rmax, e.v.maxs)
    mathlib.VectorSubtract(maxvec, minvec, e.v.size)

    world.SV_LinkEdict(e, False)


def PF_setsize():
    e = _G_EDICT(pr_edict.OFS_PARM0)
    if e is None:
        pr_exec.PR_RunError('PF_setsize: NULL edict')
        return
    minvec = _G_VECTOR(pr_edict.OFS_PARM1)
    maxvec = _G_VECTOR(pr_edict.OFS_PARM2)
    SetMinMaxSize(e, minvec, maxvec, False)


def PF_setmodel():
    """Builtin #3: setmodel(entity e, string m)"""
    e = _G_EDICT(pr_edict.OFS_PARM0)
    m = _G_STRING(pr_edict.OFS_PARM1)

    # check to see if the model was properly precached (slot 0 is "")
    model_idx = -1
    if m == '':
        model_idx = 0
    else:
        for i, check in enumerate(sv_main.sv.model_precache):
            if check is not None and check == m:
                model_idx = i
                break

    if model_idx == -1:
        pr_exec.PR_RunError(f'no precache: {m}')
        return

    # model is a string (engine string index), modelindex is a float
    e.v.model = pr_edict.PR_SetEngineString(sv_main.sv.model_precache[model_idx])
    e.v.modelindex = float(model_idx)

    models = sv_main.sv.models
    mod = models[model_idx] if model_idx < len(models) else None
    if mod:
        SetMinMaxSize(e, mod.mins, mod.maxs, True)
    else:
        SetMinMaxSize(e, mathlib.vec3_origin, mathlib.vec3_origin, True)


def PF_bprint():
    s = PF_VarString(0)
    host.SV_BroadcastPrintf('%s', s)

def PF_sprint():

    entnum = _G_EDICTNUM(pr_edict.OFS_PARM0)
    s = PF_VarString(1)

    if entnum < 1 or entnum > sv_main.svs.maxclients:
        console.Con_Printf('tried to sprint to a non-client\n')
        return

    client = sv_main.svs.clients[entnum-1]

    common.MSG_WriteChar(client.message, protocol.svc_print )
    common.MSG_WriteString(client.message, s)

def PF_centerprint():
    entnum = _G_EDICTNUM(pr_edict.OFS_PARM0)
    s = PF_VarString(1)

    if entnum < 1 or entnum > sv_main.svs.maxclients:
        console.Con_Printf('tried to centerprint to a non-client\n')
        return

    client = sv_main.svs.clients[entnum-1]

    common.MSG_WriteChar(client.message, protocol.svc_centerprint )
    common.MSG_WriteString(client.message, s)

def PF_normalize():

    newvalue: quakedef.vec3_t = [0, 0, 0]

    value1 = _G_VECTOR(pr_edict.OFS_PARM0)

    new_temp = value1[0] * value1[0] + value1[1] * value1[1] + value1[2]*value1[2]
    new_temp = math.sqrt(new_temp)

    if new_temp == 0:
        newvalue[0] = newvalue[1] = newvalue[2] = 0
    else:
        new_temp = 1 / new_temp
        newvalue[0] = value1[0] * new_temp
        newvalue[1] = value1[1] * new_temp
        newvalue[2] = value1[2] * new_temp

    _set_vec(pr_edict.OFS_RETURN, newvalue)


def PF_vlen():
    v = _G_VECTOR(pr_edict.OFS_PARM0)
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = length

def PF_vectoyaw():
    v = _G_VECTOR(pr_edict.OFS_PARM0)

    if v[1] == 0 and v[0] == 0:
        yaw = 0
    else:
        yaw = float(int(math.atan2(v[1], v[0]) * 180.0 / math.pi))
        if yaw < 0:
            yaw += 360

    pr_edict.pr_globals[pr_edict.OFS_RETURN] = yaw


def PF_vectoangles():
    v = _G_VECTOR(pr_edict.OFS_PARM0)

    if v[1] == 0 and v[0] == 0:
        yaw = 0
        if v[2] > 0:
            pitch = 90
        else:
            pitch = 270
    else:
        yaw = float(int(math.atan2(v[1], v[0]) * 180.0 / math.pi))
        if yaw < 0:
            yaw += 360

        forward = math.sqrt(v[0] * v[0] + v[1] * v[1])
        pitch = float(int(math.atan2(v[2], forward) * 180.0 / math.pi))
        if pitch < 0:
            pitch += 360

    pr_edict.pr_globals[pr_edict.OFS_RETURN + 0] = pitch
    pr_edict.pr_globals[pr_edict.OFS_RETURN + 1] = yaw
    pr_edict.pr_globals[pr_edict.OFS_RETURN + 2] = 0


def PF_random():
    num = (random.randint(0, 0x8000) & 0x7fff) / 0x7fff
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = float(num)


def PF_particle():

    org = _G_VECTOR(pr_edict.OFS_PARM0)
    _dir = _G_VECTOR(pr_edict.OFS_PARM1)
    color = _G_FLOAT(pr_edict.OFS_PARM2)
    count = _G_FLOAT(pr_edict.OFS_PARM3)

    sv_main.SV_StartParticle(org, _dir, color, count)


def PF_ambientsound():
    large = False

    pos = _G_VECTOR(pr_edict.OFS_PARM0)

    # Read string cleanly via PR_GetString
    samp_offset = _G_INT(pr_edict.OFS_PARM1)
    samp = str(pr_edict.PR_GetString(samp_offset)).rstrip('\x00').strip()

    vol = _G_FLOAT(pr_edict.OFS_PARM2)
    attenuation = _G_FLOAT(pr_edict.OFS_PARM3)

    soundnum = -1
    for i, check in enumerate(sv_main.sv.sound_precache):
        if check and str(check).rstrip('\x00').strip() == samp:
            soundnum = i
            break

    if soundnum == -1:
        console.Con_Printf(f'no precache: {samp}\n')
        return

    if soundnum > 255:
        if sv_main.sv.protocol == protocol.PROTOCOL_NETQUAKE:
            return
        else:
            large = True

    sv_main.SV_ReserveSignonSpace(17)

    if large:
        common.MSG_WriteByte(sv_main.sv.signon, protocol.svc_spawnstaticsound2)
    else:
        common.MSG_WriteByte(sv_main.sv.signon, protocol.svc_spawnstaticsound)

    for i in range(3):
        common.MSG_WriteCoord(sv_main.sv.signon, pos[i], sv_main.sv.protocolflags)

    if large:
        common.MSG_WriteShort(sv_main.sv.signon, soundnum)
    else:
        common.MSG_WriteByte(sv_main.sv.signon, soundnum)

    common.MSG_WriteByte(sv_main.sv.signon, int(vol * 255))
    common.MSG_WriteByte(sv_main.sv.signon, int(attenuation * 64))

def PF_sound():
    entity = _G_EDICT(pr_edict.OFS_PARM0)
    channel = _G_FLOAT(pr_edict.OFS_PARM1)

    sample_offset = _G_INT(pr_edict.OFS_PARM2)
    sample = str(pr_edict.PR_GetString(sample_offset)).rstrip('\x00').strip()

    volume = _G_FLOAT(pr_edict.OFS_PARM3) * 255
    attenuation = _G_FLOAT(pr_edict.OFS_PARM4)

    match_found = False
    for check in sv_main.sv.sound_precache:
        if check and str(check).rstrip('\x00').strip() == sample:
            match_found = True
            break

    if not match_found:
        console.Con_Printf(f'no precache: {sample}\n')
        return

    sv_main.SV_StartSound(entity, channel, sample, volume, attenuation)


def PF_break():
    console.Con_Printf('break statement')
    breakpoint()  # noqa: T100

def PF_traceline():
    v1 = _G_VECTOR(pr_edict.OFS_PARM0)
    v2 = _G_VECTOR(pr_edict.OFS_PARM1)
    nomonsters = int(_G_FLOAT(pr_edict.OFS_PARM2))   # a float, not a vector
    ent = _G_EDICT(pr_edict.OFS_PARM3)

    if cvar.Cvar_VariableValue('developer'):
        if any(math.isnan(x) for x in v1 + v2):
            console.Con_Warning('NAN in traceline\n')

    if any(math.isnan(x) for x in v1):
        v1 = [0.0, 0.0, 0.0]
    if any(math.isnan(x) for x in v2):
        v2 = [0.0, 0.0, 0.0]

    trace = world.SV_Move(v1, mathlib.vec3_origin, mathlib.vec3_origin, v2, nomonsters, ent)

    g = pr_edict.pr_globals
    g[_gofs('trace_allsolid')] = float(trace.allsolid)
    g[_gofs('trace_startsolid')] = float(trace.startsolid)
    g[_gofs('trace_fraction')] = float(trace.fraction)
    g[_gofs('trace_inwater')] = float(trace.inwater)
    g[_gofs('trace_inopen')] = float(trace.inopen)
    _set_vec(_gofs('trace_endpos'), trace.endpos)
    _set_vec(_gofs('trace_plane_normal'), trace.plane.normal)
    g[_gofs('trace_plane_dist')] = float(trace.plane.dist)
    # a miss reports the world edict (edict 0)
    g[_gofs('trace_ent')] = pr_edict.EDICT_TO_PROG(trace.ent) if trace.ent is not None else 0


def PF_newcheckclient(check: int) -> int:
    """Helper for checkclient: Iterates through connected client slots (1 to maxclients)

    in a round-robin search to find the next active target, generating its PVS array.
    """
    global checkpvs, checkpvs_capacity

    # 1. Clamp start index within client slot range [1, maxclients]
    check = max(1, min(check, sv_main.svs.maxclients))

    if check == sv_main.svs.maxclients:
        i = 1
    else:
        i = check + 1

    # 2. Round-robin search for next valid, targetable client (C: for (;;i++))
    ent = None
    while True:
        if i == sv_main.svs.maxclients + 1:
            i = 1

        ent = pr_edict.EDICT_NUM(i)

        if i == check:
            break  # didn't find anything else

        if ent.free or ent.v.health <= 0 or (int(ent.v.flags) & server.FL_NOTARGET):
            i += 1
            continue

        break  # found a valid target client (return i, not i + 1)

    # 3. Calculate eye position and obtain Leaf/PVS data
    org: quakedef.vec3_t = [0.0, 0.0, 0.0]
    mathlib.VectorAdd(ent.v.origin, ent.v.view_ofs, org)

    leaf = gl_model.Mod_PointInLeaf(org, sv_main.sv.worldmodel)
    pvs = gl_model.Mod_LeafPVS(leaf, sv_main.sv.worldmodel)

    # 4. Resize checkpvs byte buffer matching C realloc
    pvsbytes = (sv_main.sv.worldmodel.numleafs + 7) >> 3

    if checkpvs is None or pvsbytes > checkpvs_capacity:
        checkpvs_capacity = pvsbytes
        checkpvs = bytearray(pvsbytes)

    # Copy raw PVS bytes into checkpvs buffer
    checkpvs[:len(pvs)] = pvs

    return i

def PF_checkclient():
    global c_notvis, c_invis
    view = [0.0, 0.0, 0.0]

    if sv_main.sv.time - sv_main.sv.lastchecktime >= 0.1:
        sv_main.sv.lastcheck = PF_newcheckclient(sv_main.sv.lastcheck)
        sv_main.sv.lastchecktime = sv_main.sv.time

    ent = pr_edict.EDICT_NUM(sv_main.sv.lastcheck)
    if ent.free or ent.v.health <= 0:
        RETURN_EDICT(sv_main.sv.edicts[0])
        return

    _self = _G_EDICT(pr_edict.OFS_SELF)
    mathlib.VectorAdd(_self.v.origin, _self.v.view_ofs, view)
    leaf = gl_model.Mod_PointInLeaf(view, sv_main.sv.worldmodel)
    l = world._leaf_index(leaf) - 1   # C: (leaf - worldmodel->leafs) - 1

    if l < 0 or not (checkpvs[l >> 3] & (1 << (l & 7))):
        c_notvis += 1
        RETURN_EDICT(sv_main.sv.edicts[0])
        return

    c_invis += 1
    RETURN_EDICT(ent)


def PF_stuffcmd():
    entnum = _G_EDICTNUM(pr_edict.OFS_PARM0)

    if entnum < 1 or entnum > sv_main.svs.maxclients:
        pr_exec.PR_RunError('Parm 0 not a client')
    string = _G_STRING(pr_edict.OFS_PARM1)

    old = host.host_client
    host.host_client = sv_main.svs.clients[entnum -1]
    host.Host_ClientCommands('%s', string)
    host.host_client = old

def PF_localcmd():
    string = _G_STRING(pr_edict.OFS_PARM0)
    _cmd.Cbuf_AddText(string)

def PF_cvar():
    string = _G_STRING(pr_edict.OFS_PARM0)
    # returns the cvar's float VALUE (it used to store the name string)
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = float(cvar.Cvar_VariableValue(string))


def PF_cvar_set():
    var = _G_STRING(pr_edict.OFS_PARM0)
    val = _G_STRING(pr_edict.OFS_PARM1)

    cvar.Cvar_Set(var, val)

def PF_findradius():
    """Builtin #22: findradius(vector org, float rad) -> entity

    Searches active non-SOLID_NOT entities whose origin + mid-point bounds fall
    within 'rad' distance of 'org', linking them into a chain via e.v.chain.
    Returns the head entity of the linked list.
    """
    org = _G_VECTOR(pr_edict.OFS_PARM0)
    rad = _G_FLOAT(pr_edict.OFS_PARM1)
    rad_sq = rad * rad

    # Head of the chain starts at worldspawn (edict 0)
    chain = pr_edict.EDICT_NUM(0)

    # Loop through active edicts, skipping worldspawn at index 0
    for i in range(1, sv_main.sv.num_edicts):
        ent = pr_edict.EDICT_NUM(i)

        if ent.free:
            continue
        if int(ent.v.solid) == server.SOLID_NOT:
            continue

        # Check squared distance along X, Y, and Z axes early-out
        # Midpoint center = origin + (mins + maxs) * 0.5
        d0 = org[0] - (ent.v.origin[0] + (ent.v.mins[0] + ent.v.maxs[0]) * 0.5)
        lensq = d0 * d0
        if lensq > rad_sq:
            continue

        d1 = org[1] - (ent.v.origin[1] + (ent.v.mins[1] + ent.v.maxs[1]) * 0.5)
        lensq += d1 * d1
        if lensq > rad_sq:
            continue

        d2 = org[2] - (ent.v.origin[2] + (ent.v.mins[2] + ent.v.maxs[2]) * 0.5)
        lensq += d2 * d2
        if lensq > rad_sq:
            continue

        # Link ent into the chain: ent.v.chain points to previous chain head index
        ent.v.chain = pr_edict.EDICT_TO_PROG(chain)
        chain = ent

    # Return head edict index to QuakeC (OFS_RETURN)
    RETURN_EDICT(chain)


def PF_dprint():
    console.Con_DPrintf(PF_VarString(0))

def PF_ftos():
    """Builtin #28: ftos(float v) -> string

    Converts a float to a string representation, matching C Quake sprintf behavior:
    - If v has no fractional part, formats as an integer ("%d").
    - Otherwise, formats with 5 characters total and 1 decimal place ("%5.1f").
    """
    v = _G_FLOAT(pr_edict.OFS_PARM0)

    # C Quake float-to-int equality check
    if v == int(v):
        s = f"{int(v)}"
    else:
        # %5.1f equivalent: right-aligned in 5 spaces with 1 decimal place
        s = f"{v:5.1f}"

    # Allocate engine string buffer offset and store in OFS_RETURN
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = pr_edict.PR_SetEngineString(s)

def PF_fabs():
    v = _G_FLOAT(pr_edict.OFS_PARM0)
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = math.fabs(v)

def PF_vtos():
    v = _G_VECTOR(pr_edict.OFS_PARM0)
    s = f"'{v[0]:5.1f} {v[1]:5.1f} {v[2]:5.1f}'"
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = pr_edict.PR_SetEngineString(s)


def PF_Spawn():
    """Builtin #14: spawn() -> entity"""
    RETURN_EDICT(pr_edict.ED_Alloc())


def PF_Remove():
    ed = _G_EDICT(pr_edict.OFS_PARM0)
    if ed is sv_main.sv.edicts[0]:
        console.Con_DPrintf('Tried to remove the world entity\n')
        return
    pr_edict.ED_Free(ed)


def PF_Find():
    """Builtin #18: find(entity start, .string field, string match) -> entity"""
    e = _G_EDICTNUM(pr_edict.OFS_PARM0)
    f = _G_INT(pr_edict.OFS_PARM1)          # field offset
    s = _G_STRING(pr_edict.OFS_PARM2)

    if not s:
        pr_exec.PR_RunError('PF_Find: bad search string')
        return

    for i in range(e + 1, sv_main.sv.num_edicts):
        ed = pr_edict.EDICT_NUM(i)          # was EDICT_NUM(e): always the same edict
        if ed.free:
            continue

        t = pr_edict.PR_GetString(int(pr_exec.GetEdictFieldValue(ed.v, f)))
        if not t:
            continue

        if t == s:
            RETURN_EDICT(ed)
            return

    RETURN_EDICT(sv_main.sv.edicts[0])


def PR_CheckEmptyString(s: str):
    if s[0] < ' ':
        pr_exec.PR_RunError('Bad string')

def PF_precache_file():
    # dummy for the qcc compiler: returns its argument unchanged
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = pr_edict.pr_globals[pr_edict.OFS_PARM0]


import traceback

def PF_precache_sound():
    if sv_main.sv.state != server.server_state_t.ss_loading:
        pr_exec.PR_RunError('PF_Precache_*: Precache can only be done in spawn functions')
        return

    s = _G_STRING(pr_edict.OFS_PARM0)
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = pr_edict.pr_globals[pr_edict.OFS_PARM0]

    if not s:
        pr_exec.PR_RunError('PF_precache_sound: NULL pointer')
        return

    sp = sv_main.sv.sound_precache
    if not sp:
        sp.append('')
    elif not sp[0]:
        sp[0] = ''

    for i in range(1, quakedef.MAX_SOUNDS):
        if i >= len(sp):
            sp.append(s)
            return
        if not sp[i]:
            sp[i] = s
            return
        if sp[i] == s:
            return

    pr_exec.PR_RunError('PF_precache_sound: overflow')


def PF_precache_model():
    if sv_main.sv.state != server.server_state_t.ss_loading:
        pr_exec.PR_RunError('PF_Precache_*: Precache can only be done in spawn functions')
        return

    s = _G_STRING(pr_edict.OFS_PARM0)
    # like C, returns its argument (the string), not the model index
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = pr_edict.pr_globals[pr_edict.OFS_PARM0]

    if not s:
        pr_exec.PR_RunError('PF_precache_model: NULL pointer')
        return

    mp = sv_main.sv.model_precache
    if not mp:
        mp.append('')
    elif not mp[0]:
        mp[0] = ''

    max_models = getattr(quakedef, 'MAX_MODELS', 2048)
    idx = -1
    for i in range(1, max_models):
        if i >= len(mp):
            mp.append(s)
            idx = i
            break
        if not mp[i]:
            mp[i] = s
            idx = i
            break
        if mp[i] == s:
            return  # already precached

    if idx == -1:
        pr_exec.PR_RunError('PF_precache_model: overflow')
        return

    models = sv_main.sv.models
    while len(models) <= idx:
        models.append(None)
    models[idx] = gl_model.Mod_ForName(s, True)


def PF_coredump():
    pr_edict.ED_PrintEdicts_f()


def PF_traceon():
    pr_exec.pr_trace = True

def PF_traceoff():
    pr_exec.pr_trace = False

def PF_eprint():
    pr_edict.ED_PrintNum(_G_EDICTNUM(pr_edict.OFS_PARM0))

def PF_walkmove():
    move: quakedef.vec3_t = [0, 0, 0]

    ent = _G_EDICT(pr_edict.OFS_SELF)
    yaw = _G_FLOAT(pr_edict.OFS_PARM0)
    dist = _G_FLOAT(pr_edict.OFS_PARM1)

    if not (int(ent.v.flags) & (server.FL_ONGROUND|server.FL_FLY|server.FL_SWIM)):
        pr_edict.pr_globals[pr_edict.OFS_RETURN] = 0.0
        return

    yaw = yaw * math.pi * 2 / 360

    move[0] = math.cos(yaw) * dist
    move[1] = math.sin(yaw) * dist
    move[2] = 0

    oldf = pr_exec.pr_xfunction
    oldself = pr_edict.pr_globals[pr_edict.OFS_SELF]

    pr_edict.pr_globals[pr_edict.OFS_RETURN] = float(bool(sv_move.SV_movestep(ent, move, True)))

    pr_exec.pr_xfunction = oldf
    pr_edict.pr_globals[pr_edict.OFS_SELF] = oldself


def PF_droptofloor():
    """Builtin #34: droptofloor() -> float (1.0 on success, 0.0 if stuck or in mid-air)"""
    end = [0.0, 0.0, 0.0]
    ent = _G_EDICT(pr_edict.OFS_SELF)

    mathlib.VectorCopy(ent.v.origin, end)
    end[2] -= 256.0

    # SV_Move lives in world.py; the C code passes false (MOVE_NORMAL)
    trace = world.SV_Move(ent.v.origin, ent.v.mins, ent.v.maxs, end, world.MOVE_NORMAL, ent)

    if trace.fraction == 1.0 or trace.allsolid:
        pr_edict.pr_globals[pr_edict.OFS_RETURN] = 0.0
    else:
        mathlib.VectorCopy(trace.endpos, ent.v.origin)
        world.SV_LinkEdict(ent, False)
        ent.v.flags = float(int(ent.v.flags) | server.FL_ONGROUND)
        ent.v.groundentity = pr_edict.EDICT_TO_PROG(trace.ent)
        pr_edict.pr_globals[pr_edict.OFS_RETURN] = 1.0


def PF_lightstyle():
    style = _G_FLOAT(pr_edict.OFS_PARM0)
    val   = _G_STRING(pr_edict.OFS_PARM1)

    if style < 0 or style >= quakedef.MAX_LIGHTSTYLES:
        console.Con_DPrintf(f'PF_lightstyle: invalid style {style}\n')
        return

    sv_main.sv.lightstyles[int(style)] = val

    if sv_main.sv.state != server.server_state_t.ss_active:
        return

    for j in range(sv_main.svs.maxclients):
        client = sv_main.svs.clients[j]

        if client.active or client.spawn_parms:
            common.MSG_WriteChar(client.message, protocol.svc_lightstyle)
            common.MSG_WriteChar(client.message, int(style))
            common.MSG_WriteString(client.message, val)


def PF_rint():

    f = _G_FLOAT(pr_edict.OFS_PARM0)

    if f > 0.0:
        val = float(int(f + 0.5))
    else:
        val = float(int(f - 0.5))

    pr_edict.pr_globals[pr_edict.OFS_RETURN] = val


def PF_floor():

    f = _G_FLOAT(pr_edict.OFS_PARM0)
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = float(math.floor(f))


def PF_ceil():

    f = _G_FLOAT(pr_edict.OFS_PARM0)
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = float(math.ceil(f))


def PF_checkbottom():
    ent = _G_EDICT(pr_edict.OFS_PARM0)
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = float(bool(sv_move.SV_CheckBottom(ent)))

def PF_pointcontents():
    v = _G_VECTOR(pr_edict.OFS_PARM0)
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = float(world.SV_PointContents(v))

def PF_nextent():
    i = _G_EDICTNUM(pr_edict.OFS_PARM0)

    while True:
        i += 1
        if i == sv_main.sv.num_edicts:
            RETURN_EDICT(sv_main.sv.edicts[0])
            return

        ent = pr_edict.EDICT_NUM(i)
        if not ent.free:
            RETURN_EDICT(ent)
            return


def PF_aim():
    """Builtin #44: aim(entity ent, float speed) -> vector"""
    start = [0.0, 0.0, 0.0]
    _dir = [0.0, 0.0, 0.0]
    end = [0.0, 0.0, 0.0]

    ent = _G_EDICT(pr_edict.OFS_PARM0)
    # speed (PARM1) is unused, as in the C code

    v_forward = _GV('v_forward')

    mathlib.VectorCopy(ent.v.origin, start)
    start[2] += 20.0

    # try sending a trace straight ahead
    _dir = list(v_forward)
    mathlib.VectorMA(start, 2048.0, _dir, end)
    tr = world.SV_Move(start, mathlib.vec3_origin, mathlib.vec3_origin, end, world.MOVE_NORMAL, ent)

    teamplay = cvar.Cvar_VariableValue('teamplay')
    if tr.ent is not None and int(tr.ent.v.takedamage) == server.DAMAGE_AIM:
        if not teamplay or ent.v.team <= 0 or ent.v.team != tr.ent.v.team:
            _set_vec(pr_edict.OFS_RETURN, v_forward)
            return

    # try all possible entities
    bestdir = list(_dir)
    bestdist = cvar.Cvar_VariableValue('sv_aim')
    bestent = None

    for i in range(1, sv_main.sv.num_edicts):
        check = pr_edict.EDICT_NUM(i)

        if int(check.v.takedamage) != server.DAMAGE_AIM:
            continue
        if check is ent:
            continue
        if teamplay and ent.v.team > 0 and ent.v.team == check.v.team:
            continue  # don't aim at teammate

        for j in range(3):
            end[j] = check.v.origin[j] + 0.5 * (check.v.mins[j] + check.v.maxs[j])

        mathlib.VectorSubtract(end, start, _dir)
        mathlib.VectorNormalize(_dir)

        dist = mathlib.DotProduct(_dir, v_forward)
        if dist < bestdist:
            continue  # too far to turn

        tr = world.SV_Move(start, mathlib.vec3_origin, mathlib.vec3_origin, end, world.MOVE_NORMAL, ent)
        if tr.ent is check:
            bestdist = dist
            bestent = check

    if bestent is not None:
        mathlib.VectorSubtract(bestent.v.origin, ent.v.origin, _dir)
        dist = mathlib.DotProduct(_dir, v_forward)
        mathlib.VectorScale(v_forward, dist, end)
        end[2] = _dir[2]
        mathlib.VectorNormalize(end)
        _set_vec(pr_edict.OFS_RETURN, end)
    else:
        _set_vec(pr_edict.OFS_RETURN, bestdir)


def PF_changeyaw():
    ent = _G_EDICT(pr_edict.OFS_SELF)
    current = mathlib.anglemod(ent.v.angles[1])
    ideal = ent.v.ideal_yaw
    speed = ent.v.yaw_speed

    if current == ideal:
        return

    move = ideal - current

    if ideal > current:
        if move >= 180:
            move = move - 360
    else:
        if move <= -180:
            move += 360

    if move > 0:
        move = min(move, speed)
    else:
        move = max(move, -speed)

    ent.v.angles[1] = mathlib.anglemod(current + move)


def WriteDest() -> common.sizebuf_s:
    dest = int(_G_FLOAT(pr_edict.OFS_PARM0))

    if dest ==  MSG_BROADCAST:
        return sv_main.sv.datagram

    elif dest ==  MSG_ONE:
        ent = _G_EDICT(_gofs('msg_entity'))
        entnum = pr_edict.NUM_FOR_EDICT(ent)

        if entnum < 1 or entnum > sv_main.svs.maxclients:
            pr_exec.PR_RunError('WriteDest: not a client')

        return sv_main.svs.clients[entnum-1].message

    elif dest == MSG_ALL:
        return sv_main.sv.reliable_datagram

    elif dest == MSG_INIT:
        return sv_main.sv.signon

    else:
        pr_exec.PR_RunError('WriteDest: bad destination')

    return None

def PF_WriteByte():
    """Builtin #52: WriteByte(float msg_dest, float val)"""
    val = int(_G_FLOAT(pr_edict.OFS_PARM1)) & 0xFF
    common.MSG_WriteByte(WriteDest(), val)


def PF_WriteChar():
    """Builtin #53: WriteChar(float msg_dest, float val)"""
    val = int(_G_FLOAT(pr_edict.OFS_PARM1)) & 0xFF
    common.MSG_WriteChar(WriteDest(), val)


def PF_WriteShort():
    """Builtin #54: WriteShort(float msg_dest, float val)"""
    val = int(_G_FLOAT(pr_edict.OFS_PARM1)) & 0xFFFF
    common.MSG_WriteShort(WriteDest(), val)


def PF_WriteLong():
    """Builtin #55: WriteLong(float msg_dest, float val)"""
    val = int(_G_FLOAT(pr_edict.OFS_PARM1))
    common.MSG_WriteLong(WriteDest(), val)


def PF_WriteAngle():
    """Builtin #56: WriteAngle(float msg_dest, float val)"""
    val = _G_FLOAT(pr_edict.OFS_PARM1)
    common.MSG_WriteAngle(WriteDest(), val, sv_main.sv.protocolflags)


def PF_WriteCoord():
    """Builtin #57: WriteCoord(float msg_dest, float val)"""
    val = _G_FLOAT(pr_edict.OFS_PARM1)
    common.MSG_WriteCoord(WriteDest(), val, sv_main.sv.protocolflags)


def PF_WriteString():
    """Builtin #58: WriteString(float msg_dest, string s)"""
    raw_str = _G_STRING(pr_edict.OFS_PARM1)
    localized_str = common.LOC_GetString(raw_str)
    common.MSG_WriteString(WriteDest(), localized_str)


def PF_WriteEntity():
    """Builtin #59: WriteEntity(float msg_dest, entity e)"""
    entnum = _G_EDICTNUM(pr_edict.OFS_PARM1)
    common.MSG_WriteShort(WriteDest(), entnum)



def PF_makestatic():
    bits = 0

    ent = _G_EDICT(pr_edict.OFS_PARM0)

    if ent.alpha == protocol.ENTALPHA_ZERO:
        pr_edict.ED_Free(ent)
        return

    # In strict Quake parity, ent.v.model is always a string offset (int)
    model_str = pr_edict.PR_GetString(ent.v.model)
    model_idx = sv_main.SV_ModelIndex(model_str)
    frame_val = int(ent.v.frame)

    if sv_main.sv.protocol == protocol.PROTOCOL_NETQUAKE:
        if (model_idx & 0xFF00) or (frame_val & 0xFF00):
            pr_edict.ED_Free(ent)
            return
    else:
        if model_idx & 0xFF00:
            bits |= protocol.B_LARGEMODEL
        if frame_val & 0xFF00:
            bits |= protocol.B_LARGEFRAME
        if ent.alpha != protocol.ENTALPHA_DEFAULT:
            bits |= protocol.B_ALPHA

        if sv_main.sv.protocol == protocol.PROTOCOL_RMQ:
            val: progs.eval_t = pr_edict.GetEdictFieldValue(ent, 'scale')
            if val:
                ent.scale = protocol.ENTSCALE_ENCODE(val._float)
            else:
                ent.scale = protocol.ENTSCALE_DEFAULT

            if ent.scale != protocol.ENTSCALE_DEFAULT:
                bits |= protocol.B_SCALE

    sv_main.SV_ReserveSignonSpace(34)

    if bits:
        common.MSG_WriteByte(sv_main.sv.signon, protocol.svc_spawnstatic2)
        common.MSG_WriteByte(sv_main.sv.signon, bits)
    else:
        common.MSG_WriteByte(sv_main.sv.signon, protocol.svc_spawnstatic)

    if bits & protocol.B_LARGEMODEL:
        common.MSG_WriteShort(sv_main.sv.signon, model_idx)
    else:
        common.MSG_WriteByte(sv_main.sv.signon, model_idx)

    if bits & protocol.B_LARGEFRAME:
        common.MSG_WriteShort(sv_main.sv.signon, frame_val)
    else:
        common.MSG_WriteByte(sv_main.sv.signon, frame_val)

    common.MSG_WriteByte(sv_main.sv.signon, int(ent.v.colormap))
    common.MSG_WriteByte(sv_main.sv.signon, int(ent.v.skin))

    for i in range(3):
        common.MSG_WriteCoord(sv_main.sv.signon, ent.v.origin[i], sv_main.sv.protocolflags)
        common.MSG_WriteAngle(sv_main.sv.signon, ent.v.angles[i], sv_main.sv.protocolflags)

    if bits & protocol.B_ALPHA:
        common.MSG_WriteByte(sv_main.sv.signon, int(ent.alpha))

    if bits & protocol.B_SCALE:
        common.MSG_WriteByte(sv_main.sv.signon, int(ent.scale))

    pr_edict.ED_Free(ent)









def PF_setspawnparms():
    """Builtin #3: setspawnparms(entity client)

    Copies persistent client spawn parameters (health, items, ammo across level transitions)
    from client structure back into global parm1..parm16 variables.
    """
    ent = _G_EDICT(pr_edict.OFS_PARM0)
    i = pr_edict.NUM_FOR_EDICT(ent)

    if i < 1 or i > sv_main.svs.maxclients:
        pr_exec.PR_RunError('Entity is not a client')

    client = sv_main.svs.clients[i - 1]

    # Explicit attribute assignment
    for j in range(16):
        pr_edict.pr_globals[_gofs(f'parm{j + 1}')] = float(client.spawn_parms[j])


def PF_changelevel():
    if sv_main.svs.changelevel_issued:
        return
    sv_main.svs.changelevel_issued = True

    s = _G_STRING(pr_edict.OFS_PARM0)
    _cmd.Cbuf_AddText(f'changelevel {s}\n')



def PF_finalefinished():
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = 0

def PF_CheckPlayerEXFlags():
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = 0

def PF_walkpathtogoal():
    pr_edict.pr_globals[pr_edict.OFS_RETURN] = 0

def PF_localsound():
    entnum = _G_EDICTNUM(pr_edict.OFS_PARM0)
    sample = _G_STRING(pr_edict.OFS_PARM1)

    if entnum < 1 or entnum > sv_main.svs.maxclients:
        console.Con_Printf('tried to localsound a non client\n')
        return

    sv_main.SV_LocalSound(sv_main.svs.clients[entnum-1], sample)

def PF_Fixme():
    pr_exec.PR_RunError('unimplemented builtin')

pr_builtin = [
    PF_Fixme,
    PF_makevectors,
    PF_setorigin,
    PF_setmodel,
    PF_setsize,
    PF_Fixme,
    PF_break,
    PF_random,
    PF_sound,
    PF_normalize,
    PF_error,
    PF_objerror,
    PF_vlen,
    PF_vectoyaw,
    PF_Spawn,
    PF_Remove,
    PF_traceline,
    PF_checkclient,
    PF_Find,
    PF_precache_sound,
    PF_precache_model,
    PF_stuffcmd,
    PF_findradius,
    PF_bprint,
    PF_sprint,
    PF_dprint,
    PF_ftos,
    PF_vtos,
    PF_coredump,
    PF_traceon,
    PF_traceoff,
    PF_eprint,
    PF_walkmove,
    PF_Fixme,
    PF_droptofloor,
    PF_lightstyle,
    PF_rint,
    PF_floor,
    PF_ceil,
    PF_Fixme,
    PF_checkbottom,
    PF_pointcontents,
    PF_Fixme,
    PF_fabs,
    PF_aim,
    PF_cvar,
    PF_localcmd,
    PF_nextent,
    PF_particle,
    PF_changeyaw,
    PF_Fixme,
    PF_vectoangles,

    PF_WriteByte,
    PF_WriteChar,
    PF_WriteShort,
    PF_WriteLong,
    PF_WriteCoord,
    PF_WriteAngle,
    PF_WriteString,
    PF_WriteEntity,

    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,

    sv_move.SV_MoveToGoal,
    PF_precache_file,
    PF_makestatic,

    PF_changelevel,
    PF_Fixme,

    PF_cvar_set,
    PF_centerprint,

    PF_ambientsound,

    PF_precache_model,
    PF_precache_sound,
    PF_precache_file,

    PF_setspawnparms,

    PF_finalefinished,
    PF_localsound,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,
    PF_Fixme,

    PF_CheckPlayerEXFlags,
    PF_walkpathtogoal,

    PF_Fixme,
]

pr_numbuiltins = len(pr_builtin)