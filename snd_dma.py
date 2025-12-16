#snd_dma.py 

import sdl2.sdlmixer

import bspfile
import console
import q_sound

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

known_sfx : q_sound.sfx_t = None
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
    _cmd.Cmd_AddCommand("play",      S_Play); 
    _cmd.Cmd_AddCommand("playvol",   S_PlayVol);
    _cmd.Cmd_AddCommand("stopsound", S_StopAllSoundsC);
    _cmd.Cmd_AddCommand("soundlist", S_SoundList);
    _cmd.Cmd_AddCommand("soundinfo", S_SoundInfo_f);

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

