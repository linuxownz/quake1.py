#snd_dma.py

import random
import struct

import _cmd
import bspfile
import cl_main
import common
import console
import cvar
import gl_model
import host
import mathlib
import q_sound
import quakedef
import snd_codec
import snd_mem
import snd_mix
import snd_sdl
import sys_sdl_unix
import zone

ambient_sfx : list[q_sound.sfx_t] = []
snd_channels : list[q_sound.channel_t] = [ q_sound.channel_t() for _ in range (q_sound.MAX_CHANNELS)]
total_channels = 0

snd_blocked = 0
snd_initialized = False

sn  : q_sound.dma_t = q_sound.dma_t()
shm : q_sound.dma_t = None

listener_origin  = [0, 0, 0]
listener_forward = [0, 0, 0]
listener_right   = [0, 0, 0]
listener_up      = [0, 0, 0]

sound_nominal_clip_dist = 1000.0

soundtime = 0
paintedtime = 0

s_rawend = 0
s_rawsamples : list[q_sound.portable_samplepair_t] = [ q_sound.portable_samplepair_t() for _ in range(q_sound.MAX_RAW_SAMPLES)]

MAX_SFX = 1024

known_sfx : list[q_sound.sfx_t] = []
num_sfx = 0

sound_started = False
SND_FILTERQUALITY_DEFAULT = '1'
S_Play_hash = 345

def S_ClearBuffer():
    global s_rawend
    if not sound_started:
        return
    snd_sdl.SNDDMA_LockBuffer()

    if not shm.buffer:
        snd_sdl.SNDDMA_UnlockBuffer()
        return

    s_rawend = 0

    if shm.samplebits == 8 and not shm.signed8:
        clear = 0x80
    else:
        clear = 0

    buffer_bytes = (shm.samples * shm.samplebits) // 8
    shm.buffer[:buffer_bytes] = bytes([clear]) * buffer_bytes

    snd_sdl.SNDDMA_Submit()

def S_Play():
    global S_Play_hash
    i = 1

    while i < _cmd.Cmd_Argc():
        name = _cmd.Cmd_Argv(i)

        if not name.endswith('.wav'):
            name += '.wav'
        sfx = S_PrecacheSound(name)

        S_Play_hash += 1
        S_StartSound(S_Play_hash, 0, sfx, listener_origin, 1.0, 1.0)
        i += 1


S_PlayVol_hash = 543
def S_PlayVol():
    global S_PlayVol_hash
    i = 1
    while i < _cmd.Cmd_Argc():
        name = _cmd.Cmd_Argv(i)
        if name.count('.') == 0:
            name += '.wav'

        sfx = S_PrecacheSound(name)
        vol = float(_cmd.Cmd_Argv(i+1))
        S_PlayVol_hash += 1
        S_StartSound(S_PlayVol_hash, 0, sfx, listener_origin, vol, 1.0)
        i += 2

def S_StopAllSoundsC():
    S_StopAllSounds(True)


def S_SoundInfo_f():
    if not sound_started or shm is None:
        console.Con_Printf('sound system not started')
        return

    console.Con_Printf("%d bit, %s, %d Hz\n" % (shm.samplebits, 'stereo' if shm.channels == 2 else "mono", shm.speed))
    console.Con_Printf("%5d samples\n" % shm.samples)
    console.Con_Printf("%5d samplepos\n" % shm.samplepos)
    console.Con_Printf("%5d submission_chunk\n" % shm.submission_chunk)
    console.Con_Printf("%5d total_channels\n" % total_channels)
    console.Con_Printf("dma buffer %s\n" % ('allocated' if shm.buffer else 'none'))

def SND_Callback_sfxvolume(var):
    Snd_InitScaletable()

def SND_Callback_snd_filterquality(var):
    snd_filterquality = int(cvar.Cvar_GetCvar('snd_filterquality').value)
    if snd_filterquality < 1 or snd_filterquality > 5:
        console.Con_Printf('snd_filterquality must be between 1 and 5\n')
        cvar.Cvar_SetQuickByName('snd_filterquality', SND_FILTERQUALITY_DEFAULT)

def S_FindName(name):
    global num_sfx
    if not name:
        sys_sdl_unix.Sys_Error('S_FindName : name is Null')

    for i in range(num_sfx):
        if known_sfx[i].name == name:
            return known_sfx[i]

    if num_sfx == MAX_SFX:
        sys_sdl_unix.Sys_Error('S_FindName: out of sfx_t')

    sfx = known_sfx[num_sfx]
    sfx.name = name
    num_sfx += 1

    return sfx

def S_PrecacheSound(name):
    nosound  = int(cvar.Cvar_GetCvar('nosound').value)
    precache = int(cvar.Cvar_GetCvar('precache').value)

    if not sound_started or nosound:
        return None

    sfx = S_FindName(name)

    if precache:
        snd_mem.S_LoadSound(sfx)

    return sfx

def Snd_InitScaletable():
    sfxvolume = float(cvar.Cvar_GetCvar('volume').value)

    table = getattr(snd_mix, 'snd_scaletable', None)
    if table is None or len(table) < 32:
        table = snd_mix.snd_scaletable = [[0] * 256 for _ in range(32)]

    for i in range(32):
        scale = i * 8 * 256 * sfxvolume
        for j in range(256):
            table[i][j] = int((j if j < 128 else j - 256) * scale)

def S_Startup():
    global sound_started, shm

    if not snd_initialized:
        return

    sound_started = snd_sdl.SNDDMA_Init(sn)
    if sound_started and shm is None:
        shm = sn   # C: shm = &sn inside SNDDMA_Init

    if not sound_started:
        console.Con_Printf('failed to init sound')
    else:
        console.Con_Printf("Audio: %d bit, %s, %d Hz\n" % ( shm.samplebits, 'stereo' if shm.channels == 2 else "mono", shm.speed))  # noqa: UP031

def S_Init():
    global known_sfx
    global num_sfx
    global snd_initialized
    global ambient_sfx

    import cvar

    ambient_sfx = [q_sound.sfx_t() for _ in range(quakedef.NUM_AMBIENTS)]

    if snd_initialized:
        console.Con_Printf('sound already initialized')

    bgmvolume         = {'name': "bgmvolume",         'value': "1",     'flags' : cvar.CVAR_ARCHIVE};
    sfxvolume         = {'name': "volume",            'value': "0.7",   'flags' : cvar.CVAR_ARCHIVE};
    precache          = {'name': "precache",          'value': "1",     'flags' : cvar.CVAR_NONE};
    loadas8bit        = {'name': "loadas8bit",        'value': "0",     'flags' : cvar.CVAR_NONE};
    sndspeed          = {'name': "sndspeed",          'value': "11025", 'flags' : cvar.CVAR_NONE};
    snd_mixspeed      = {'name': "snd_mixspeed",      'value': "44100", 'flags' : cvar.CVAR_NONE};

    snd_filterquality = {'name':"snd_filterquality",  'value':SND_FILTERQUALITY_DEFAULT, 'flags': cvar.CVAR_NONE};

    nosound           = {'name': "nosound",           'value': "0",     'flags' : cvar.CVAR_NONE}; # TODO should be 0 for sound
    ambient_level     = {'name': "ambient_level",     'value': "0.3",   'flags' : cvar.CVAR_NONE};
    ambient_fade      = {'name': "ambient_fade",      'value': "100",   'flags' : cvar.CVAR_NONE};
    snd_noextraupdate = {'name': "snd_noextraupdate", 'value': "0",     'flags' : cvar.CVAR_NONE};
    snd_show          = {'name': "snd_show",          'value': "0",     'flags' : cvar.CVAR_NONE};
    _snd_mixahead     = {'name': "_snd_mixahead",     'value': "0.1",   'flags' : cvar.CVAR_ARCHIVE};


    cvar.Cvar_RegisterVariable(nosound)
    cvar.Cvar_RegisterVariable(sfxvolume)
    cvar.Cvar_RegisterVariable(precache)
    cvar.Cvar_RegisterVariable(loadas8bit)
    cvar.Cvar_RegisterVariable(bgmvolume)
    cvar.Cvar_RegisterVariable(ambient_level)
    cvar.Cvar_RegisterVariable(ambient_fade)
    cvar.Cvar_RegisterVariable(snd_noextraupdate)
    cvar.Cvar_RegisterVariable(snd_show)
    cvar.Cvar_RegisterVariable(_snd_mixahead)
    cvar.Cvar_RegisterVariable(sndspeed)
    cvar.Cvar_RegisterVariable(snd_mixspeed)
    cvar.Cvar_RegisterVariable(snd_filterquality)

    import common
    if common.safemode or common.COM_CheckParm('-nosound'):
        return

    console.Con_Printf('\nSound Initialization\n')

    import _cmd
    _cmd.Cmd_AddCommand("play",      S_Play)
    _cmd.Cmd_AddCommand("playvol",   S_PlayVol)
    _cmd.Cmd_AddCommand("stopsound", S_StopAllSoundsC)
    _cmd.Cmd_AddCommand("soundlist", S_SoundList)
    _cmd.Cmd_AddCommand("soundinfo", S_SoundInfo_f)

    i = common.COM_CheckParm('-sndspeed')
    if i and i < common.com_argc - 1:
        cvar.Cvar_SetQuickByName('sndspeed', common.com_argv[i + 1])

    i = common.COM_CheckParm('-mixspeed')
    if i and i < common.com_argc - 1:
        cvar.Cvar_SetQuickByName('snd_mixspeed', common.com_argv[i + 1])

    cvar.Cvar_SetCallback(sfxvolume,         SND_Callback_sfxvolume);
    cvar.Cvar_SetCallback(snd_filterquality, SND_Callback_snd_filterquality);

    Snd_InitScaletable()

    known_sfx = [q_sound.sfx_t() for _ in range(MAX_SFX)]
    num_sfx = 0

    snd_initialized = True

    S_Startup()
    if sound_started == 0:
        return

    ambient_sfx[quakedef.AMBIENT_WATER] = S_PrecacheSound('ambience/water1.wav')
    ambient_sfx[quakedef.AMBIENT_SKY]   = S_PrecacheSound('ambience/wind2.wav')

    snd_codec.S_CodecInit()

    S_StopAllSounds(True)


def S_Shutdown():
    global sound_started, snd_blocked, shm

    if not sound_started:
        return

    sound_started = 0
    snd_blocked = 0

    snd_codec.S_CodecShutdown()

    snd_sdl.SNDDMA_Shutdown()
    shm = None

def S_TouchSound(name):
    if not sound_started:
        return

    S_FindName(name)   # C also touches the cache LRU; sfx.cache is held directly now

def SND_PickChannel(entnum: int, entchannel: int) -> q_sound.channel_t:
    first_to_die = -1
    life_left = 0x7fffffff

    for ch_idx in range(quakedef.NUM_AMBIENTS, quakedef.NUM_AMBIENTS + q_sound.MAX_DYNAMIC_CHANNELS):
        if entchannel != 0 and snd_channels[ch_idx].entnum == entnum and ( snd_channels[ch_idx].entchannel == entchannel or entchannel == -1):
            first_to_die = ch_idx
            break
        if snd_channels[ch_idx].entnum == cl_main.cl.viewentity and entnum != cl_main.cl.viewentity and snd_channels[ch_idx].sfx:
            continue
        if snd_channels[ch_idx].end - paintedtime < life_left:
            life_left = snd_channels[ch_idx].end - paintedtime
            first_to_die = ch_idx

    if first_to_die == -1:
        return None

    if snd_channels[first_to_die].sfx:
        snd_channels[first_to_die].sfx = None

    return snd_channels[first_to_die]

def SND_Spatialize(ch: q_sound.channel_t):
    if ch.entnum == cl_main.cl.viewentity:
        ch.leftvol = ch.master_vol
        ch.rightvol = ch.master_vol
        return

    source_vec: quakedef.vec3_t = [0, 0, 0]
    rscale = 0.0
    lscale = 0.0
    scale  = 0.0

    mathlib.VectorSubtract(ch.origin, listener_origin, source_vec)
    dist = mathlib.VectorNormalize(source_vec) * ch.dist_mult
    dot = mathlib.DotProduct(listener_right, source_vec)

    if shm.channels == 1:
        rscale = 1.0
        lscale = 1.0
    else:
        rscale = 1.0 + dot
        lscale = 1.0 - dot

    scale = ( 1.0 - dist ) * rscale
    ch.rightvol = int(ch.master_vol * scale)
    ch.rightvol = max(ch.rightvol, 0)

    scale = (1.0 - dist) * lscale
    ch.leftvol = int(ch.master_vol * scale)
    ch.leftvol = max(ch.leftvol, 0)

def S_StartSound( entnum: int, entchannel: int, sfx: q_sound.sfx_t, origin: quakedef.vec3_t, fvol: float, attenuation: float):
    if not sound_started:
        return

    if not sfx:
        return

    if cvar.Cvar_GetCvar('nosound').value:
        return

    target_chan: q_sound.channel_t = SND_PickChannel(entnum, entchannel)
    if not target_chan:
        return

    target_chan.clear()   # C: memset(target_chan, 0, sizeof(*target_chan))
    mathlib.VectorCopy(origin, target_chan.origin)
    target_chan.dist_mult = attenuation / sound_nominal_clip_dist
    target_chan.master_vol = int(fvol * 255)
    target_chan.entnum = entnum
    target_chan.entchannel = entchannel

    SND_Spatialize(target_chan)

    if not target_chan.leftvol and not target_chan.rightvol:
        return

    sc: q_sound.sfxcache_t = snd_mem.S_LoadSound(sfx)
    if not sc:
        target_chan.sfx = None
        return

    target_chan.sfx = sfx
    target_chan.pos = 0
    target_chan.end = paintedtime + sc.length

    for ch_idx in range(quakedef.NUM_AMBIENTS, quakedef.NUM_AMBIENTS + q_sound.MAX_DYNAMIC_CHANNELS):
        check = snd_channels[ch_idx]
        if check is target_chan:
            continue

        if check.sfx == sfx and not check.pos:
            skip = int(0.1 * shm.speed)
            skip = min(skip, sc.length)
            if skip > 0:
                skip = random.randint(0, 32767) % skip
            target_chan.pos += skip
            target_chan.end -= skip
            break

def S_StopSound(entnum, entchannel):
    for i in range(q_sound.MAX_DYNAMIC_CHANNELS):
        if snd_channels[i].entnum == entnum and snd_channels[i].entchannel == entchannel:
            snd_channels[i].end = 0
            snd_channels[i].sfx = None
            return


def S_StopAllSounds(clear: bool):
    global total_channels
    if not sound_started:
        return

    total_channels = q_sound.MAX_DYNAMIC_CHANNELS + quakedef.NUM_AMBIENTS

    for i in range(q_sound.MAX_CHANNELS):
        if snd_channels[i].sfx:
            snd_channels[i].clear()

    if clear:
        S_ClearBuffer()


def S_StaticSound(sfx: q_sound.sfx_t, origin: quakedef.vec3_t, vol: float, attenuation:float):
    global total_channels

    if not sfx:
        return

    if total_channels >= q_sound.MAX_CHANNELS:
        console.Con_Printf('total_channels == MAX_CHANNELS')
        return

    ss:q_sound.channel_t = snd_channels[total_channels]
    total_channels += 1

    sc:q_sound.sfxcache_t = snd_mem.S_LoadSound(sfx)
    if not sc:
        return

    if sc.loopstart == -1:
        console.Con_Printf(f'Sound {sfx.name} not looped')
        return

    ss.sfx = sfx
    mathlib.VectorCopy(origin, ss.origin)
    ss.master_vol = int(vol)
    ss.dist_mult =  (attenuation / 64) / sound_nominal_clip_dist
    ss.end = paintedtime + sc.length

    SND_Spatialize(ss)

def S_UpdateAmbientSounds():

    if cl_main.cls.state != quakedef.cactive_t.ca_connected:
        return

    if not cl_main.cl.worldmodel:
        return

    l:quakedef.mleaf_t = gl_model.Mod_PointInLeaf(listener_origin, cl_main.cl.worldmodel)

    ambient_level = cvar.Cvar_GetCvar('ambient_level').value
    ambient_fade = cvar.Cvar_GetCvar('ambient_fade').value

    if not l or not ambient_level:
        for ambient_channel in range(quakedef.NUM_AMBIENTS):
            snd_channels[ambient_channel].sfx = None
        return

    for ambient_channel in range(quakedef.NUM_AMBIENTS):
        chan = snd_channels[ambient_channel]
        chan.sfx = ambient_sfx[ambient_channel]

        vol = int( ambient_level * l.ambient_sound_level[ambient_channel])
        if vol < 8:
            vol = 0


        if chan.master_vol < vol:
            chan.master_vol += int(host.host_frametime * ambient_fade)
            chan.master_vol = min(chan.master_vol, vol)
        elif chan.master_vol > vol:
            chan.master_vol -= int(host.host_frametime * ambient_fade)
            chan.master_vol = max(chan.master_vol, vol)

        chan.leftvol = chan.rightvol = chan.master_vol


def S_RawSamples( samples: int, rate: int, width: int, channels: int, data: bytes, volume: float) -> None:

    global s_rawend

    if not sound_started:
        return

    s_rawend = max(s_rawend, paintedtime)

    scale: float = rate / shm.speed
    intVolume: int = int(256 * volume)

    i: int = 0
    while True:
        # C: src = (int)(i * scale);
        src: int = int(i * scale)
        if src >= samples:
            break

        dst: int = s_rawend & (q_sound.MAX_RAW_SAMPLES - 1)
        s_rawend += 1

        if channels == 2:
            if width == 2:
                # 16-bit Stereo PCM
                byte_offset = src * 4  # (src * 2 channels) * 2 bytes/sample
                left_sample, right_sample = struct.unpack_from(
                    "<hh", data, byte_offset
                )
                s_rawsamples[dst].left = left_sample * intVolume
                s_rawsamples[dst].right = right_sample * intVolume
            else:
                # 8-bit Stereo PCM (unsigned 0..255)
                byte_offset = src * 2
                b_left, b_right = data[byte_offset], data[byte_offset + 1]
                s_rawsamples[dst].left = ((b_left - 128) << 8) * intVolume
                s_rawsamples[dst].right = ((b_right - 128) << 8) * intVolume
        else:
            if width == 2:
                # 16-bit Mono PCM
                byte_offset = src * 2
                mono_sample = struct.unpack_from("<h", data, byte_offset)[0]
                sample_val = mono_sample * intVolume
                s_rawsamples[dst].left = sample_val
                s_rawsamples[dst].right = sample_val
            else:
                # 8-bit Mono PCM (unsigned 0..255)
                b_mono = data[src]
                sample_val = ((b_mono - 128) << 8) * intVolume
                s_rawsamples[dst].left = sample_val
                s_rawsamples[dst].right = sample_val

        i += 1

def S_Update(
    origin: quakedef.vec3_t,
    forward: quakedef.vec3_t,
    right: quakedef.vec3_t,
    up: quakedef.vec3_t,
) -> None:
    """C equivalent (snd_dma.c):

    void S_Update(vec3_t origin, vec3_t forward, vec3_t right, vec3_t up)
    """
    if not sound_started or snd_blocked > 0:
        return

    # Update global listener transform vectors
    mathlib.VectorCopy(origin, listener_origin)
    mathlib.VectorCopy(forward, listener_forward)
    mathlib.VectorCopy(right, listener_right)
    mathlib.VectorCopy(up, listener_up)

    S_UpdateAmbientSounds()

    combine: q_sound.channel_t | None = None
    static_start = q_sound.MAX_DYNAMIC_CHANNELS + quakedef.NUM_AMBIENTS

    for i in range(quakedef.NUM_AMBIENTS, total_channels):
        ch = snd_channels[i]
        if not ch.sfx:
            continue

        SND_Spatialize(ch)

        if not ch.leftvol and not ch.rightvol:
            continue

        # Static entity channels combining logic (e.g., doors, platforms)
        if i >= static_start:
            if combine and combine.sfx == ch.sfx:
                combine.leftvol += ch.leftvol
                combine.rightvol += ch.rightvol
                ch.leftvol = 0
                ch.rightvol = 0
                continue

            j = static_start
            while j < i:
                combine = snd_channels[j]
                if combine.sfx == ch.sfx:
                    break
                j += 1

            if j == i:
                combine = None
            else:
                if combine != ch:
                    combine.leftvol += ch.leftvol
                    combine.rightvol += ch.rightvol
                    ch.leftvol = 0
                    ch.rightvol = 0
                continue

    # Debug channel display (snd_show cvar)
    if cvar.Cvar_GetCvar('snd_show').value:
        total = 0
        for i in range(total_channels):
            ch = snd_channels[i]
            if ch.sfx and (ch.leftvol or ch.rightvol):
                console.Con_Printf(
                    f"{ch.leftvol:3d} {ch.rightvol:3d} {ch.sfx.name}\n"
                )
                total += 1
        console.Con_Printf(f"----({total})-----\n")

    S_Update_()


oldsamplepos = 0
buffers = 0
def GetSoundTime():
    global buffers, oldsamplepos, paintedtime, soundtime
    fullsamples = shm.samples // shm.channels

    samplepos = snd_sdl.SNDDMA_GetDMAPos()

    if samplepos < oldsamplepos:
        buffers += 1

        if paintedtime > 0x40000000:
            buffers = 0
            paintedtime = fullsamples
            S_StopAllSounds(True)

    oldsamplepos = samplepos
    soundtime = buffers * fullsamples + samplepos//shm.channels

def S_ExtraUpdate():
    if cvar.Cvar_GetCvar('snd_noextraupdate').value:
        return
    S_Update_()

def S_Update_() -> None:
    """C equivalent (snd_dma.c): static void S_Update_(void)"""
    global paintedtime

    if not sound_started or snd_blocked > 0:
        return

    snd_sdl.SNDDMA_LockBuffer()

    if not shm.buffer:
        snd_sdl.SNDDMA_UnlockBuffer()
        return

    GetSoundTime()

    paintedtime = max(paintedtime, soundtime)

    # Calculate target end time for mixing buffer
    mixahead_samples = int(cvar.Cvar_GetCvar("_snd_mixahead").value * shm.speed)
    endtime = soundtime + mixahead_samples

    # Total sample frames in hardware ring buffer
    samps = shm.samples >> (shm.channels - 1)

    # Clamp mixahead to prevent buffer overrun beyond hardware buffer length
    if endtime - soundtime > samps:
        endtime = soundtime + samps

    snd_mix.S_PaintChannels(endtime)

    snd_sdl.SNDDMA_Submit()
#    snd_sdl.SNDDMA_UnlockBuffer()



def S_BlockSound():
    global snd_blocked

    if sound_started and snd_blocked == 0:
        snd_blocked = 1
        S_ClearBuffer()
        if shm:
            snd_sdl.SNDDMA_BlockSound()


def S_UnblockSound():
    global snd_blocked

    if not sound_started or not snd_blocked:
        return

    if snd_blocked == 1:
        snd_blocked = 0
        snd_sdl.SNDDMA_UnblockSound()
        S_ClearBuffer()


def S_SoundList():
    total = 0

    for sfx in known_sfx[:num_sfx]:
        sc:q_sound.sfxcache_t = sfx.cache
        if not sc:
            continue

        size = sc.length * sc.width * ( sc.stereo + 1)
        total += size

        if sc.loopstart >= 0:
            console.Con_Printf('L')
        else:
            console.Con_Printf(' ')
        console.Con_Printf(f'({sc.width*8:2d}b) {size:6d} : {sfx.name}\n')

    console.Con_Printf(f'{num_sfx} sounds, {total} bytes\n')

def S_LocalSound(name: str):

    if cvar.Cvar_GetCvar('nosound').value:
        return
    if not sound_started:
        return

    sfx = S_PrecacheSound(name)
    if not sfx:
        console.Con_Printf(f'S_LocalSound:L cant cache {name}\n')
        return

    S_StartSound(cl_main.cl.viewentity, -1, sfx, mathlib.vec3_origin, 1, 1)

def S_ClearPrecache():
    pass

def S_BeginPrecaching():
    pass

def S_EndPrecaching():
    pass