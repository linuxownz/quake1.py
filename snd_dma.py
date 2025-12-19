#snd_dma.py 

import sdl2.sdlmixer

import _cmd
import cvar
import common
import bspfile
import console
import q_sound
import snd_mix
import snd_sdl

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

ambient_sfx : list[q_sound.sfx_t] = [q_sound.sfx_t() for _ in range(bspfile.NUM_AMBIENTS)]

sound_started = False

SND_FILTERQUALITY_DEFAULT = '1'


def SNDDMA_LockBuffer():
    SDL_LockAudio()

def S_ClearBuffer():
    if not sound_started:
        return

    SNDDMA_LockBuffer()
    

def S_StopAllSounds(clear):
    if not sound_started:
        return

    total_channels = MAX_DYNAMIC_CHANNELS + NUM_AMBIENTS

    if clear:
        S_ClearBuffer()




S_Play_hash = 345
def S_Play():
    global S_Play_hash
    i = 1

    while i < common.Cmd_Argc():
        name = common.Cmd_Argv(i)

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
        S_StartSound(S_PlayVol_hash, sfx, listener_origin, vol, 1.0)
        i += 2

def S_StopAllSoundsC():
    S_StopAllSounds(True)

def S_SoundList():
    total = 0

    raise NotImplementedError

    i = 0
    for sfx in known_sfx:
        sc = 1 # ????

def S_SoundInfo_f():
    if not sound_started or shm is None:
        console.Con_Printf('sound system not started')
        return

    console.Con_Printf("%d bit, %s, %d Hz\n" % shm.samplebits, 'stereo' if shm.channels == 2 else "mono", shm.speed)
    console.Con_Printf("%5d samples\n" % shm.samples);
    console.Con_Printf("%5d samplepos\n" % shm.samplepos);
    console.Con_Printf("%5d submission_chunk\n" % shm.submission_chunk);
    console.Con_Printf("%5d total_channels\n" % total_channels);
    console.Con_Printf("%p dma buffer\n" % shm.buffer);

def SND_Callback_sfxvolume(var):
    SND_InitScaleTable()

def SND_Callback_snd_filterquality(var):
    snd_filterquality = int(cvar.Cvar_GetCvar('snd_filterquality').value)
    if snd_filterquality < 1 or snd_filterquality > 5:
        console.Con_Printf('snd_filterquality must be between 1 and 5\n')
        cvar.Cvar_SetQuickByName('snd_filterquality', SND_FILTERQUALITY_DEFAULT)

def S_FindName(name):
    global num_sfx
    if not name:
        Sys_Error('S_FindName : name is Null')
    
    i = 0
    for i in range(num_sfx):
        if known_sfx[i].name == name:
            return known_sfx[i]

    print (i)

    if num_sfx == MAX_SFX:
        Sys_Error('S_FindName: out of sfx_t')

    sfx = known_sfx[i]
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
        S_LoadSound(sfx)

    return sfx

def Snd_InitScaletable():
    sfxvolume = float(cvar.Cvar_GetCvar('volume').value)

    for i in range(32):
        scale = i * 8 * 256 * sfxvolume
        for j in range(256):
            snd_mix.snd_scaletable[i][j] = (j if j < 128 else j - 256) * scale

def S_Startup():
    global sound_started

    if not snd_initialized:
        return

    sound_started = snd_sdl.SNDDMA_Init(sn)

    if not sound_started:
        console.Con_Printf('failed to init sound')
    else:
        console.Con_Printf("Audio: %d bit, %s, %d Hz\n" % ( shm.samplebits, 'stereo' if shm.channels == 2 else "mono", shm.speed))
    
def S_Init():
    global known_sfx
    global num_sfx
    global snd_initialized

    import cvar

    if snd_initialized:
        console.Con_Printf('sound already initialized')

    bgmvolume         = {'name': "bgmvolume",         'value': "1",     'flags' : cvar.CVAR_ARCHIVE};        
    sfxvolume         = {'name': "volume",            'value': "0.7",   'flags' : cvar.CVAR_ARCHIVE};
    precache          = {'name': "precache",          'value': "1",     'flags' : cvar.CVAR_NONE};
    loadas8bit        = {'name': "loadas8bit",        'value': "0",     'flags' : cvar.CVAR_NONE};
    sndspeed          = {'name': "sndspeed",          'value': "11025", 'flags' : cvar.CVAR_NONE};
    snd_mixspeed      = {'name': "snd_mixspeed",      'value': "44100", 'flags' : cvar.CVAR_NONE};

    snd_filterquality = {'name':"snd_filterquality",  'value':SND_FILTERQUALITY_DEFAULT, 'flags': cvar.CVAR_NONE};

    nosound           = {'name': "nosound",           'value': "0",     'flags' : cvar.CVAR_NONE};                    
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
        cvar.Cvar_SetQuickByName('mixspeed', common.com_argv[i + 1])

    cvar.Cvar_SetCallback(sfxvolume,         SND_Callback_sfxvolume);
    cvar.Cvar_SetCallback(snd_filterquality, SND_Callback_snd_filterquality);

    Snd_InitScaletable()

    known_sfx = [q_sound.sfx_t() for _ in range(MAX_SFX)]
    num_sfx = 0

    snd_initialized = True

    S_Startup()
    if sound_started == 0:
        return
    
    global ambient_sfx
    ambient_sfx[bspfile.AMBIENT_WATER] = S_PrecacheSound('ambience/water1.wav')
    ambient_sfx[bspfile.AMBIENT_SKY]   = S_PrecacheSound('ambience/wind2.wav')

    S_CodecInit()

    S_StopAllSounds(True)

