#protocol.py 

PROTOCOL_NETQUAKE  =  15
PROTOCOL_FITZQUAKE = 666
PROTOCOL_RMQ       = 999

# PROTOCOL_RMQ protocol flags
PRFL_SHORTANGLE  =  (1 << 1)
PRFL_FLOATANGLE  =  (1 << 2)
PRFL_24BITCOORD  =  (1 << 3)
PRFL_FLOATCOORD  =  (1 << 4)
PRFL_EDICTSCALE  =  (1 << 5)
PRFL_ALPHASANITY =  (1 << 6) # cleanup insanity with alpha
PRFL_INT32COORD  =  (1 << 7)
PRFL_MOREFLAGS   =  (1 << 31) # not supported

# if the high bit of the servercmd is set, the low bits are fast update flags:
U_MOREBITS = (1<<0)
U_ORIGIN1  = (1<<1)
U_ORIGIN2  = (1<<2)
U_ORIGIN3  = (1<<3)
U_ANGLE2   = (1<<4)
U_STEP     = (1<<5) #johnfitz -- was U_NOLERP, renamed since it's only used for MOVETYPE_STEP
U_FRAME    = (1<<6)
U_SIGNAL   = (1<<7) # just differentiates from other updates

# svc_update can pass all of the fast update bits, plus more
U_ANGLE1 = (1<<8)
U_ANGLE3 = (1<<9)
U_MODEL  = (1<<10)
U_COLORMAP=  (1<<11)
U_SKIN   =(1<<12)
U_EFFECTS  =(1<<13)
U_LONGENTITY= (1<<14)
#johnfitz -- PROTOCOL_FITZQUAKE -- new bits
U_EXTEND1 = (1<<15)
U_ALPHA  =(1<<16) # 1 byte, uses ENTALPHA_ENCODE, not sent if equal to baseline
U_FRAME2 = (1<<17) # 1 byte, this is .frame & 0xFF00 (second byte)
U_MODEL2 = (1<<18) # 1 byte, this is .modelindex & 0xFF00 (second byte)
U_LERPFINISH= (1<<19) # 1 byte, 0.0-1.0 maps to 0-255, not sent if exactly 0.1, this is ent->v.nextthink - sv.time, used for lerping
U_SCALE = (1<<20) # 1 byte, for PROTOCOL_RMQ PRFL_EDICTSCALE
U_UNUSED21=  (1<<21)
U_UNUSED22=  (1<<22)
U_EXTEND2 = (1<<23) # another byte to follow, future expansion
#johnfitz

#johnfitz -- PROTOCOL_NEHAHRA transparency
U_TRANS  = (1<<15)
#johnfitz

SU_VIEWHEIGHT=(1<<0)
SU_IDEALPITCH=(1<<1)
SU_PUNCH1= (1<<2)
SU_PUNCH2= (1<<3)
SU_PUNCH3= (1<<4)
SU_VELOCITY1=(1<<5)
SU_VELOCITY2=(1<<6)
SU_VELOCITY3=(1<<7)
SU_UNUSED8= (1<<8)  #AVAILABLE BIT
SU_ITEMS= (1<<9)
SU_ONGROUND= (1<<10) # no data follows, the bit is it
SU_INWATER= (1<<11) # no data follows, the bit is it
SU_WEAPONFRAME=(1<<12)
SU_ARMOR= (1<<13)
SU_WEAPON= (1<<14)
#johnfitz=-- PROTOCOL_FITZQUAKE -- new bits
SU_EXTEND1= (1<<15) # another byte to follow
SU_WEAPON2= (1<<16) # 1 byte, this is .weaponmodel & 0xFF00 (second byte)
SU_ARMOR2= (1<<17) # 1 byte, this is .armorvalue & 0xFF00 (second byte)
SU_AMMO2= (1<<18) # 1 byte, this is .currentammo & 0xFF00 (second byte)
SU_SHELLS2= (1<<19) # 1 byte, this is .ammo_shells & 0xFF00 (second byte)
SU_NAILS2= (1<<20) # 1 byte, this is .ammo_nails & 0xFF00 (second byte)
SU_ROCKETS2= (1<<21) # 1 byte, this is .ammo_rockets & 0xFF00 (second byte)
SU_CELLS2= (1<<22) # 1 byte, this is .ammo_cells & 0xFF00 (second byte)
SU_EXTEND2= (1<<23) # another byte to follow
SU_WEAPONFRAME2=(1<<24) # 1 byte, this is .weaponframe & 0xFF00 (second byte)
SU_WEAPONALPHA=(1<<25) # 1 byte, this is alpha for weaponmodel, uses ENTALPHA_ENCODE, not sent if ENTALPHA_DEFAULT
SU_UNUSED26= (1<<26)
SU_UNUSED27= (1<<27)
SU_UNUSED28= (1<<28)
SU_UNUSED29= (1<<29)
SU_UNUSED30= (1<<30)
SU_EXTEND3= (1<<31) # another byte to follow, future expansion
#johnfitz

# a sound with no channel is a local only sound
SND_VOLUME= (1<<0) # a byte
SND_ATTENUATION= (1<<1) # a byte
SND_LOOPING= (1<<2) # a long

DEFAULT_SOUND_PACKET_VOLUME= 255
DEFAULT_SOUND_PACKET_ATTENUATION=1.0

#johnfitz -- PROTOCOL_FITZQUAKE -- new bits
SND_LARGEENTITY=(1<<3) # a short + byte (instead of just a short)
SND_LARGESOUND=(1<<4) # a short soundindex (instead of a byte)
#johnfitz

#johnfitz -- PROTOCOL_FITZQUAKE -- flags for entity baseline messages
B_LARGEMODEL=(1<<0) # modelindex is short instead of byte
B_LARGEFRAME=(1<<1) # frame is short instead of byte
B_ALPHA=  (1<<2) # 1 byte, uses ENTALPHA_ENCODE, not sent if ENTALPHA_DEFAULT
B_SCALE=  (1<<3)
#johnfitz

#johnfitz -- PROTOCOL_FITZQUAKE -- alpha encoding
ENTALPHA_DEFAULT=0 #entity's alpha is "default" (i.e. water obeys r_wateralpha) -- must be zero so zeroed out memory works
ENTALPHA_ZERO= 1 #entity is invisible (lowest possible alpha)
ENTALPHA_ONE= 255 #entity is fully opaque (highest possible alpha)

#defines need to be fixed
def ENTALPHA_ENCODE(a):
    if a==0:
        return ENTALPHA_DEFAULT
    else:
        return Q_rint(CLAMP(1.0,(a)*254.0+1,255.0)) #server convert to byte to send to client

def ENTALPHA_DECODE(a):
    if a==ENTALPHA_DEFAULT:
        return 1.0
    else:
        returnfloat(a-1)/254 #client convert to float for rendering

def ENTALPHA_TOSAVE(a):
    if a==ENTALPHA_DEFAULT:
        return 0.0
    elif a==ENTALPHA_ZERO:
        return -1.0
    else:
        return float(a)-float(1/254) #server convert to float for savegame

#johnfitz
ENTSCALE_DEFAULT=16 # Equivalent to float 1.0f due to byte packing.

def ENTSCALE_ENCODE(a):
    if a:
        return (a) * ENTSCALE_DEFAULT 
    else: 
        return ENTSCALE_DEFAULT # Convert to byte

def ENTSCALE_DECODE(a):
    return float(a) / ENTSCALE_DEFAULT # Convert to float for rendering

#defines need to be fixed

# defaults for clientinfo messages
DEFAULT_VIEWHEIGHT =  22

# game types sent by serverinfo
# these determine which intermission screen plays
GAME_COOP=  0
GAME_DEATHMATCH= 1

#==================
# note that there are some defs.qc that mirror to these numbers
# also related to svc_strings[] in cl_parse
#==================

#
# server to client
#
svc_bad=    0
svc_nop=    1
svc_disconnect=  2
svc_updatestat=  3 # [byte] [long]
svc_version=   4 # [long] server version
svc_setview=   5 # [short] entity number
svc_sound=   6 # <see code>
svc_time=   7 # [float] server time
svc_print=   8 # [string] null terminated string
svc_stufftext=  9 # [string] stuffed into client's console buffer
                                # the string should be \n terminated
svc_setangle=  10 # [angle3] set the view angle to this absolute value
svc_serverinfo=  11 # [long] version
                                # [string] signon string
                                # [string]..[0]model cache
                                # [string]...[0]sounds cache
svc_lightstyle=  12 # [byte] [string]
svc_updatename=  13 # [byte] [string]
svc_updatefrags=  14 # [byte] [short]
svc_clientdata=  15 # <shortbits + data>
svc_stopsound=  16 # <see code>
svc_updatecolors= 17 # [byte] [byte]
svc_particle=  18 # [vec3] <variable>
svc_damage=   19
svc_spawnstatic=  20
#svc_spawnbinary = 21
svc_spawnbaseline= 22
svc_temp_entity=  23
svc_setpause=  24 # [byte] on / off
svc_signonnum=  25 # [byte]  used for the signon sequence
svc_centerprint=  26 # [string] to put in center of the screen
svc_killedmonster= 27
svc_foundsecret=  28
svc_spawnstaticsound=29 # [coord3] [byte] samp [byte] vol [byte] aten
svc_intermission= 30 # [string] music
svc_finale=   31 # [string] music [string] text
svc_cdtrack=   32 # [byte] track [byte] looptrack
svc_sellscreen=  33
svc_cutscene=  34

#johnfitz -- PROTOCOL_FITZQUAKE -- new server messages
svc_skybox=   37 # [string] name
svc_bf=    40
svc_fog=    41 # [byte] density [byte] red [byte] green [byte] blue [float] time
svc_spawnbaseline2= 42  # support for large modelindex, large framenum, alpha, using flags
svc_spawnstatic2= 43 # support for large modelindex, large framenum, alpha, using flags
svc_spawnstaticsound2=44 # [coord3] [short] samp [byte] vol [byte] aten
#johnfitz

# 2021 re-release server messages - see:
# https://steamcommunity.com/sharedfiles/filedetails/?id=2679459726
svc_botchat= 38
svc_setviews= 45
svc_updateping= 46
svc_updatesocial=47
svc_updateplinfo=48
svc_rawprint= 49
svc_servervars= 50
svc_seq=  51
#Note: svc_achievement has same value as svcdp_effect!
svc_achievement= 52 # [string] id
svc_chat= 53
svc_levelcompleted=54
svc_backtolobby= 55
svc_localsound= 56

#
# client to server
#
clc_bad=  0
clc_nop=  1
clc_disconnect=2
clc_move= 3  # [usercmd_t]
clc_stringcmd=4  # [string] message

#
# temp entity events
#
TE_SPIKE=  0
TE_SUPERSPIKE= 1
TE_GUNSHOT=  2
TE_EXPLOSION= 3
TE_TAREXPLOSION= 4
TE_LIGHTNING1= 5
TE_LIGHTNING2= 6
TE_WIZSPIKE=  7
TE_KNIGHTSPIKE= 8
TE_LIGHTNING3= 9
TE_LAVASPLASH= 10
TE_TELEPORT=  11
TE_EXPLOSION2= 12

# PGM 01/21/97
TE_BEAM =   13
# PGM 01/21/97

class entity_state_t:
    def __init__(self):
        self.origin : List[float] = [ 0., 0., 0. ]
        self.angles : List[float] = [ 0., 0., 0. ]
        self.modelindex = 0
        self.frame = 0
        self.colormap = 0
        self.skin = 0
        self.alpha = 0
        self.scale = 0
        self.effects = 0

class usercmd_t:
    def __init__(self):
        self.viewangles : List[float] = [ 0., 0., 0. ]

        self.forwardmove = 0.0
        self.sidemove = 0.0
        self.upmove = 0.0