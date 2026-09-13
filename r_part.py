#r_part.py 

import common
import cvar
import gl_texmgr
import glquake

ABSOLUTE_MAX_PARTICLES =  32768
ABSOLUTE_MIN_PARTICLES =  512  
                             
DEFAULT_NUM_PARTICLES  = 16384

ramp1 = [ 0x6f, 0x6d, 0x6b, 0x69, 0x67, 0x65, 0x63, 0x61 ]
ramp2 = [ 0x6f, 0x6e, 0x6d, 0x6c, 0x6b, 0x6a, 0x68, 0x66 ]
ramp3 = [ 0x6d, 0x6b, 6, 5, 4, 3 ]

active_particles : list[glquake.particle_t] = []
free_particles   : list[glquake.particle_t] = []
particles        : list[glquake.particle_t] = []

r_numparticles = 0

particletexture  : gl_texmgr.gltexture_t = None
particletexture1 : gl_texmgr.gltexture_t = None
particletexture2 : gl_texmgr.gltexture_t = None
particletexture3 : gl_texmgr.gltexture_t = None

texturescalefactor = 0.0


def R_SetParticleTexture_f():
    r_particles = int(cvar.Cvar_GetCvar('r_particles').value)

    match r_particles:
        case 1:
            particletexture = particletexture1
            texturescalefactor = 1.27
        case 2:
            particletexture = particletexture2
            texturescalefactor = 1.0


def R_ParticleTextureLookup(x, y, sharpness):
    x -= 16
    y -= 16

    r = x * x + y * y

    r = min(r, 255)
    a = sharpness * ( 255 - r )
    a = min(a, 255)
    return a


def R_InitParticleTextures():
    global particletexture
    global particletexture1
    global particletexture2
    global particletexture3
    global texturescalefactor

    particle1_data = bytearray(64*64*4)
    particle2_data = bytearray(2*2*4)
    particle3_data = bytearray(64*64*4)

    dst = particle1_data
    pos = 0
    for x in range(64):
        for y in range(64):
            dst[pos + 0] = 255
            dst[pos + 1] = 255
            dst[pos + 2] = 255
            dst[pos + 3] = R_ParticleTextureLookup(x, y, 8)
            pos += 4

    particletexture1 = gl_texmgr.TexMgr_LoadImage(None, 'particle1', 64, 64, gl_texmgr.srcformat.SRC_RGBA, \
        particle1_data, '', particle1_data, gl_texmgr.TEXPREF_PERSIST | gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_LINEAR)

    dst = particle2_data
    pos = 0
    for x in range(2):
        for y in range(2):
            dst[pos + 0] = 255
            dst[pos + 1] = 255
            dst[pos + 2] = 255
            dst[pos + 3] = 0 if x or y else 255
            pos += 2

    particletexture2 = gl_texmgr.TexMgr_LoadImage(None, 'particle2', 2, 2, gl_texmgr.srcformat.SRC_RGBA, \
        particle2_data, '', particle2_data, gl_texmgr.TEXPREF_PERSIST | gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_LINEAR)

    dst = particle3_data
    pos = 0
    for x in range(64):
        for y in range(64):
            dst[pos + 0] = 255
            dst[pos + 1] = 255
            dst[pos + 2] = 255
            dst[pos + 3] = R_ParticleTextureLookup(x, y, 2)
            pos += 4

    particletexture3 = gl_texmgr.TexMgr_LoadImage(None, 'particle3', 64, 64, gl_texmgr.srcformat.SRC_RGBA, \
        particle3_data, '', particle3_data, gl_texmgr.TEXPREF_PERSIST | gl_texmgr.TEXPREF_ALPHA | gl_texmgr.TEXPREF_LINEAR)

    particletexture = particletexture1
    texturescalefactor = 1.27





def R_InitParticles():
    global r_numparticles
    global particles

    
    i = common.COM_CheckParm('-particles')

    if i and i < common.com_argc - 1:
        r_numparticles = int(common.com_argv[i + 1])
        if r_numparticles < ABSOLUTE_MIN_PARTICLES:
            r_numparticles = ABSOLUTE_MIN_PARTICLES
        elif r_numparticles > ABSOLUTE_MAX_PARTICLES:
            r_numparticles = ABSOLUTE_MAX_PARTICLES
    else:
        r_numparticles = DEFAULT_NUM_PARTICLES

    parts = [glquake.particle_t() for _ in range(r_numparticles)]

    particles = parts[0]
    for i in range(r_numparticles - 1):
        if i == 0:
            particles.next = parts[1]
        parts[i].next = parts[i+1]

    c = 0
    x = particles
    while x:
        c +=1
        x = x.next
    print('num particles %d' % c)
    assert(c == r_numparticles)
    #sys.exit

    r_particles     = {'name':"r_particles",     'value':"1", 'flags': cvar.CVAR_ARCHIVE}; #johnfitz         
    r_quadparticles = {'name':"r_quadparticles", 'value':"1", 'flags': cvar.CVAR_ARCHIVE}; #johnfitz

    cvar.Cvar_RegisterVariable(r_particles)
    cvar.Cvar_RegisterVariable(r_quadparticles)

    cvar.Cvar_SetCallback (r_particles, R_SetParticleTexture_f);

    R_InitParticleTextures()



    
    
