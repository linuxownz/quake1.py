# r_part.py

import math
import random

import OpenGL.GL as gl

import cl_main
import common
import cvar
import gl_rmain
import gl_texmgr
import glquake
import mathlib
import quakedef
import r_alias
import render

ABSOLUTE_MAX_PARTICLES =  32768
ABSOLUTE_MIN_PARTICLES =  512

DEFAULT_NUM_PARTICLES  = 16384

ramp1 = [ 0x6f, 0x6d, 0x6b, 0x69, 0x67, 0x65, 0x63, 0x61 ]
ramp2 = [ 0x6f, 0x6e, 0x6d, 0x6c, 0x6b, 0x6a, 0x68, 0x66 ]
ramp3 = [ 0x6d, 0x6b, 6, 5, 4, 3 ]

active_particles : glquake.particle_t = None
free_particles   : glquake.particle_t = None
particles        : list[glquake.particle_t] = []

r_numparticles = 0

particletexture  : gl_texmgr.gltexture_t = None
particletexture1 : gl_texmgr.gltexture_t = None
particletexture2 : gl_texmgr.gltexture_t = None
particletexture3 : gl_texmgr.gltexture_t = None

texturescalefactor = 0.0

avelocities: list[quakedef.vec3_t] = [[0, 0, 0] for _ in range(162)] # quakedef.NUMVERTEXNORMALS
beamlength = 16.


def R_ParticleTextureLookup(x:int, y:int, sharpness:int) -> int:
    x -= 16; y -= 16
    r = x * x + y * y
    r = min(255, r)
    a = sharpness * ( 255 - r )
    a = min(a, 255)
    a = max(0, a)
    return a


def R_SetParticleTexture_f():
    global particletexture, texturescalefactor
    r_particles = int(cvar.Cvar_GetCvar('r_particles').value)

    match r_particles:
        case 1:
            particletexture = particletexture1
            texturescalefactor = 1.27
        case 2:
            particletexture = particletexture2
            texturescalefactor = 1.0


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

    particles = parts
    for i in range(r_numparticles - 1):
        parts[i].next = parts[i+1]

    c = 0
    x = particles[0] if particles else None
    while x:
        c += 1
        x = x.next
    print('num particles %d' % c)  # noqa: UP031
    assert(c == r_numparticles)

    r_particles     = {'name':"r_particles",     'value':"1", 'flags': cvar.CVAR_ARCHIVE} #johnfitz
    r_quadparticles = {'name':"r_quadparticles", 'value':"1", 'flags': cvar.CVAR_ARCHIVE} #johnfitz

    cvar.Cvar_RegisterVariable(r_particles)
    cvar.Cvar_RegisterVariable(r_quadparticles)

    cvar.Cvar_SetCallback(r_particles, R_SetParticleTexture_f)

    R_InitParticleTextures()


def R_EntityParticles(ent: render.entity_t):
    global free_particles, active_particles
    dist = 64
    forward: quakedef.vec3_t = [0, 0, 0]

    if not avelocities[0][0]:
        for i in range(glquake.NUMVERTEXNORMALS):
            avelocities[i][0] = random.randint(0, 255) * 0.01
            avelocities[i][1] = random.randint(0, 255) * 0.01
            avelocities[i][2] = random.randint(0, 255) * 0.01

    for i in range(glquake.NUMVERTEXNORMALS):
        angle = cl_main.cl.time * avelocities[i][0]
        sy = math.sin(angle)
        cy = math.cos(angle)
        angle = cl_main.cl.time * avelocities[i][1]
        sp = math.sin(angle)
        cp = math.cos(angle)
        angle = cl_main.cl.time * avelocities[i][2]

        forward[0] = cp * cy
        forward[1] = cp * sy
        forward[2] = -sp

        if not free_particles:
            return

        p = free_particles
        free_particles = p.next
        p.next = active_particles
        active_particles = p

        p.die = cl_main.cl.time + 0.01
        p.color = 0x6f
        p.type = glquake.ptype_t.pt_explode

        p.org[0] = ent.origin[0] + r_alias.r_avertexnormals[i][0] * dist + forward[0] * beamlength
        p.org[1] = ent.origin[1] + r_alias.r_avertexnormals[i][1] * dist + forward[1] * beamlength
        p.org[2] = ent.origin[2] + r_alias.r_avertexnormals[i][2] * dist + forward[2] * beamlength


def R_ClearParticles():
    global free_particles, active_particles

    free_particles = particles[0] if particles else None
    active_particles = None

    for i in range(r_numparticles - 1):
        particles[i].next = particles[i+1]
    if particles:
        particles[r_numparticles-1].next = None


def R_ReadPointFile_f():
    raise NotImplementedError


def R_ParseParticleEffect():
    org: quakedef.vec3_t = [0, 0, 0]
    _dir: quakedef.vec3_t = [0, 0, 0]

    for i in range(3):
        org[i] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
    for i in range(3):
        _dir[i] = common.MSG_ReadChar() * (1.0/16)
    msgcount = common.MSG_ReadByte()
    color = common.MSG_ReadByte()

    if msgcount == 255:
        count = 1024
    else:
        count = msgcount

    R_RunParticleEffect(org, _dir, color, count)


def R_ParticleExplosion(org: quakedef.vec3_t):
    global free_particles, active_particles
    p: glquake.particles_t = None

    for i in range(1024):
        if not free_particles:
            return
        p = free_particles
        free_particles = p.next
        p.next = active_particles
        active_particles = p

        p.die = cl_main.cl.time + 5
        p.color = ramp1[0]
        p.ramp = random.randint(0, 3)

        if i & 1:
            p.type = glquake.ptype_t.pt_explode
            for j in range(3):
                p.org[j] = org[j] + random.randint(0, 32) - 16
                p.vel[j] = random.randint(0, 512) - 256

        else:
            p.type = glquake.ptype_t.pt_explode2
            for j in range(3):
                p.org[j] = org[j] + random.randint(0, 32) - 16
                p.vel[j] = random.randint(0, 512) - 256


def R_ParticleExplosion2(org: quakedef.vec3_t, colorStart, colorLength):
    global free_particles, active_particles
    colorMod = 0
    for i in range(512):
        if not free_particles:
            return

        p = free_particles
        free_particles = p.next
        p.next = active_particles
        active_particles = p

        p.die = cl_main.cl.time + 0.3
        p.color = colorStart + ( colorMod % colorLength )
        colorMod += 1  # noqa: SIM113

        p.type = glquake.ptype_t.pt_blob
        for j in range(3):
            p.org[j] = org[j] + random.randint(0, 32) - 16
            p.vel[j] = random.randint(0, 512) - 256


def R_BlobExplosion(org: quakedef.vec3_t):
    global free_particles, active_particles
    for i in range(1024):
        if not free_particles:
            return

        p = free_particles
        free_particles = p.next
        p.next = active_particles
        active_particles = p

        p.die = cl_main.cl.time + 1 + random.randint(0, 8) * 0.5

        if i & 1:
            p.type = glquake.ptype_t.pt_blob
            p.color = 66 + random.randint(0, 6)

            for j in range(3):
                p.org[j] = org[j] + random.randint(0, 32) - 16
                p.vel[j] = random.randint(0, 512) - 256

        else:
            p.type = glquake.ptype_t.pt_blob2
            p.color = 150 + random.randint(0, 6)

            for j in range(3):
                p.org[j] = org[j] + random.randint(0, 32) - 16
                p.vel[j] = random.randint(0, 512) - 256


def R_RunParticleEffect(org: quakedef.vec3_t, _dir: quakedef.vec3_t, color, count):
    global free_particles, active_particles

    for i in range(count):
        if not free_particles:
            return
        p = free_particles
        free_particles = p.next
        p.next = active_particles
        active_particles = p

        if count == 1024:
            p.die = cl_main.cl.time + 5
            p.color = ramp1[0]
            p.ramp = random.randint(0, 3)

            if i & 1:
                p.type = glquake.ptype_t.pt_explode
                for j in range(3):
                    p.org[j] = org[j] + random.randint(0, 32) - 16
                    p.vel[j] = random.randint(0, 512) - 256

            else:
                p.type = glquake.ptype_t.pt_explode2
                for j in range(3):
                    p.org[j] = org[j] + random.randint(0, 32) - 16
                    p.vel[j] = random.randint(0, 512) - 256

        else:
            p.die = cl_main.cl.time + 0.1 * random.randint(0, 5)
            p.color = (color & ~7) + random.randint(0, 7)
            p.type = glquake.ptype_t.pt_slowgrav
            for j in range(3):
                p.org[j] = org[j] + random.randint(0, 15) - 8
                p.vel[j] = _dir[j] * 15


def R_LavaSplash(org: quakedef.vec3_t):
    global free_particles, active_particles

    _dir: quakedef.vec3_t = [0, 0, 0]

    for i in range(16):
        for j in range(16):
            for k in range(16):
                if not free_particles:
                    return
                p = free_particles
                free_particles = p.next
                p.next = active_particles
                active_particles = p

                p.die = cl_main.cl.time + 2 + random.randint(0, 32) * 0.02
                p.color = 224 + random.randint(0, 7)
                p.type = glquake.ptype_t.pt_slowgrav

                _dir[0] = j * 8 + random.randint(0, 7)
                _dir[1] = i * 8 + random.randint(0, 7)
                _dir[2] = 256

                p.org[0] = org[0] + _dir[0]
                p.org[1] = org[1] + _dir[1]
                p.org[2] = org[2] + random.randint(0, 63)

                mathlib.VectorNormalize(_dir)
                vel = 50 + random.randint(0, 63)
                mathlib.VectorScale(_dir, vel, p.vel)


def R_TeleportSplash(org: quakedef.vec3_t):
    global free_particles, active_particles
    _dir: quakedef.vec3_t = [0, 0, 0]

    for i in range(-16, 16, 4):
        for j in range(-16, 16, 4):
            for k in range(-24, 32, 4):
                if not free_particles:
                    return

                p = free_particles
                free_particles = p.next
                p.next = active_particles
                active_particles = p

                p.die = cl_main.cl.time + 0.2 + random.randint(0, 7) * 0.02
                p.color = 7 + random.randint(0, 7)
                p.type = glquake.ptype_t.pt_slowgrav

                _dir[0] = j * 8
                _dir[1] = i * 8
                _dir[2] = k * 8

                p.org[0] = org[0] + i + random.randint(0, 3)
                p.org[1] = org[1] + j + random.randint(0, 3)
                p.org[2] = org[2] + k + random.randint(0, 3)

                mathlib.VectorNormalize(_dir)
                vel = 50 + random.randint(0, 63)
                mathlib.VectorScale(_dir, vel, p.vel)


tracercount = 0
def R_RocketTrail(start: quakedef.vec3_t, end: quakedef.vec3_t, _type: int):
    global free_particles, active_particles, tracercount
    vec: quakedef.vec3_t = [0, 0, 0]

    mathlib.VectorSubtract(end, start, vec)
    len = mathlib.VectorNormalize(vec)

    if _type < 128:
        dec = 3
    else:
        dec = 1
        _type -= 128

    while len > 0:
        len -= dec

        if not free_particles:
            return

        p = free_particles
        free_particles = p.next
        p.next = active_particles
        active_particles = p

        mathlib.VectorCopy(mathlib.vec3_origin, p.vel)
        p.die = cl_main.cl.time + 2

        match _type:
            case 0: # rocket trail
                p.ramp = random.randint(0, 3)
                p.color = ramp3[int(p.ramp)]
                p.type = glquake.ptype_t.pt_fire
                for j in range(3):
                    p.org[j] = start[j] + random.randint(0, 6) - 3
            case 1: # smoke smoke
                p.ramp = random.randint(0, 3)
                p.color = ramp3[int(p.ramp)]
                p.type = glquake.ptype_t.pt_fire
                for j in range(3):
                    p.org[j] = start[j] + random.randint(0, 6) - 3
            case 2: # blood
                p.type = glquake.ptype_t.pt_grav
                p.color = 67 + random.randint(0,3)
                for j in range(3):
                    p.org[j] = start[j] + random.randint(0, 6) - 3

            case 3 | 5: # tracer
                p.die = cl_main.cl.time + 0.5
                p.type = glquake.ptype_t.pt_static

                if _type == 3:
                    p.color = 52 + (( tracercount & 4) << 1)
                else:
                    p.color = 230 + (( tracercount & 4) << 1)

                tracercount += 1

                mathlib.VectorCopy(start, p.org)

                if tracercount & 1:
                    p.vel[0] = 30 * vec[1]
                    p.vel[1] = 30 * -vec[0]
                else:
                    p.vel[0] = 30 * -vec[1]
                    p.vel[1] = 30 * vec[0]

            case 4: #slight blood
                p.type = glquake.ptype_t.pt_grav
                p.color = 67 + random.randint(0, 3)
                for j in range(3):
                    p.org[j] = start[j] + ( random.randint(0, 6) - 3 )
                len -= 3
            case 6: # voor trail
                p.color = 9 * 16 + 8 + random.randint(0, 3)
                p.type = glquake.ptype_t.pt_static
                p.die = cl_main.cl.time + 0.3
                for j in range(3):
                    p.org[j] = start[j] + random.randint(0, 15) - 8

        mathlib.VectorAdd(start, vec, start)


def CL_RunParticles():
    global free_particles, active_particles

    frametime = cl_main.cl.time - cl_main.cl.oldtime
    time3 = frametime * 15
    time2 = frametime * 10
    time1 = frametime * 5

    grav = frametime * cvar.Cvar_GetCvar('sv_gravity').value * 0.05
    dvel = 4 * frametime

    while True:
        kill = active_particles
        if kill and kill.die < cl_main.cl.time:
            active_particles = kill.next
            kill.next = free_particles
            free_particles = kill
            continue
        break

    p = active_particles
    while p:
        while True:
            kill = p.next
            if kill and kill.die < cl_main.cl.time:
                p.next = kill.next
                kill.next = free_particles
                free_particles = kill
                continue
            break

        p.org[0] += p.vel[0] * frametime
        p.org[1] += p.vel[1] * frametime
        p.org[2] += p.vel[2] * frametime

        match p.type:
            case glquake.ptype_t.pt_static:
                pass
            case glquake.ptype_t.pt_fire:
                p.ramp += time1
                if p.ramp >= 6:
                    p.die = -1
                else:
                    p.color = ramp3[int(p.ramp)]
                p.vel[2] += grav
            case glquake.ptype_t.pt_explode:
                p.ramp += time2
                if p.ramp >= 8:
                    p.die = -1
                else:
                    p.color = ramp1[int(p.ramp)]
                for i in range(3):
                    p.vel[i] += p.vel[i] * dvel
                p.vel[2] -= grav
            case glquake.ptype_t.pt_explode2:
                p.ramp += time3
                if p.ramp >= 8:
                    p.die = -1
                else:
                    p.color = ramp2[int(p.ramp)]
                for i in range(3):
                    p.vel[i] -= p.vel[i] * frametime
                p.vel[2] -= grav
            case glquake.ptype_t.pt_blob:
                for i in range(3):
                    p.vel[i] += p.vel[i] * dvel
                p.vel[2] -= grav
            case glquake.ptype_t.pt_blob2:
                for i in range(2):
                    p.vel[i] -= p.vel[i] * dvel
                p.vel[2] -= grav
            case glquake.ptype_t.pt_grav | glquake.ptype_t.pt_slowgrav:
                p.vel[2] -= grav
        p = p.next


def R_DrawParticles():
    p: glquake.particle_t = None
    up: quakedef.vec3_t = [0, 0, 0]
    right: quakedef.vec3_t = [0, 0, 0]
    p_up: quakedef.vec3_t = [0, 0, 0]
    p_right: quakedef.vec3_t = [0, 0, 0]
    p_upright: quakedef.vec3_t = [0, 0, 0]

    color: list[int] = [0, 0, 0, 0]

    r_particles = cvar.Cvar_GetCvar('r_particles').value
    r_quadparticles = cvar.Cvar_GetCvar('r_quadparticles').value

    if not r_particles:
        return

    if not active_particles:
        return

    mathlib.VectorScale(gl_rmain.vup, 1.5, up)
    mathlib.VectorScale(gl_rmain.vright, 1.5, right)

    gl_texmgr.GL_Bind(particletexture)

    gl.glEnable(gl.GL_BLEND)
    gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
    gl.glDepthMask(gl.GL_FALSE)

    if r_quadparticles:
        gl.glBegin(gl.GL_QUADS)

        p = active_particles
        while p:
            scale = (
                (p.org[0] - gl_rmain.r_origin[0]) * gl_rmain.vpn[0] +
                (p.org[1] - gl_rmain.r_origin[1]) * gl_rmain.vpn[1] +
                (p.org[2] - gl_rmain.r_origin[2]) * gl_rmain.vpn[2]
            )

            if scale < 20:
                scale = 1 + 0.08
            else:
                scale = 1 + scale * 0.004

            scale /= 2.0
            scale *= texturescalefactor

            base_idx = int(p.color) * 4
            color[0] = gl_texmgr.d_8to24table[base_idx + 0]  # Red
            color[1] = gl_texmgr.d_8to24table[base_idx + 1]  # Green
            color[2] = gl_texmgr.d_8to24table[base_idx + 2]  # Blue
            color[3] = 255

            gl.glColor4ubv(color)

            gl.glTexCoord2f(0, 0)
            gl.glVertex3fv(p.org)

            gl.glTexCoord2f(0.5, 0)
            mathlib.VectorMA(p.org, scale, up, p_up)
            gl.glVertex3fv(p_up)

            gl.glTexCoord2f (0.5,0.5)
            mathlib.VectorMA (p_up, scale, right, p_upright)
            gl.glVertex3fv (p_upright)

            gl.glTexCoord2f (0,0.5)
            mathlib.VectorMA (p.org, scale, right, p_right)
            gl.glVertex3fv (p_right)
            p = p.next
        gl.glEnd()
    else:
        gl.glBegin(gl.GL_TRIANGLES)
        p = active_particles
        while p:

            scale = (
                (p.org[0] - gl_rmain.r_origin[0]) * gl_rmain.vpn[0] +
                (p.org[1] - gl_rmain.r_origin[1]) * gl_rmain.vpn[1] +
                (p.org[2] - gl_rmain.r_origin[2]) * gl_rmain.vpn[2]
            )

            if scale < 20:
                scale = 1 + 0.08
            else:
                scale = 1 + scale * 0.004

            scale *= texturescalefactor

            base_idx = int(p.color) * 4
            color[0] = gl_texmgr.d_8to24table[base_idx + 0]  # Red
            color[1] = gl_texmgr.d_8to24table[base_idx + 1]  # Green
            color[2] = gl_texmgr.d_8to24table[base_idx + 2]  # Blue
            color[3] = 255

            gl.glColor4ubv(color)

            gl.glTexCoord2f (0,0)
            gl.glVertex3fv (p.org)

            gl.glTexCoord2f (1,0)
            mathlib.VectorMA (p.org, scale, up, p_up)
            gl.glVertex3fv (p_up)

            gl.glTexCoord2f (0,1)
            mathlib.VectorMA (p.org, scale, right, p_right)
            gl.glVertex3fv (p_right)

            p = p.next
        gl.glEnd()
    gl.glDepthMask(gl.GL_TRUE)
    gl.glDisable(gl.GL_BLEND)
    gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
    gl.glColor3f(1, 1, 1)


def R_DrawParticles_ShowTris():
    p: glquake.particle_t = None
    up: quakedef.vec3_t = [0, 0, 0]
    right: quakedef.vec3_t = [0, 0, 0]
    p_up: quakedef.vec3_t = [0, 0, 0]
    p_right: quakedef.vec3_t = [0, 0, 0]
    p_upright: quakedef.vec3_t = [0, 0, 0]

    r_particles = cvar.Cvar_GetCvar('r_particles').value
    r_quadparticles = cvar.Cvar_GetCvar('r_quadparticles').value

    if not r_particles:
        return

    mathlib.VectorScale(gl_rmain.vup, 1.5, up)
    mathlib.VectorScale(gl_rmain.vright, 1.5, right)

    if r_quadparticles:
        p = active_particles
        while p:
            gl.glBegin(gl.GL_TRIANGLE_FAN)

            scale = (
                (p.org[0] - gl_rmain.r_origin[0]) * gl_rmain.vpn[0] +
                (p.org[1] - gl_rmain.r_origin[1]) * gl_rmain.vpn[1] +
                (p.org[2] - gl_rmain.r_origin[2]) * gl_rmain.vpn[2]
            )

            if scale < 20:
                scale = 1 + 0.08
            else:
                scale = 1 + scale * 0.004

            scale /= 2.0

            scale *= texturescalefactor

            gl.glVertex3fv(p.org)

            mathlib.VectorMA(p.org, scale, up, p_up)
            gl.glVertex3fv(p_up)

            mathlib.VectorMA(p_up, scale, right, p_upright)
            gl.glVertex3fv (p_upright)

            mathlib.VectorMA (p.org, scale, right, p_right)
            gl.glVertex3fv (p_right)

            gl.glEnd ()

            p = p.next
    else:
        gl.glBegin(gl.GL_TRIANGLES)
        p = active_particles
        while p:

            scale = (
                (p.org[0] - gl_rmain.r_origin[0]) * gl_rmain.vpn[0] +
                (p.org[1] - gl_rmain.r_origin[1]) * gl_rmain.vpn[1] +
                (p.org[2] - gl_rmain.r_origin[2]) * gl_rmain.vpn[2]
            )

            if scale < 20:
                scale = 1 + 0.08
            else:
                scale = 1 + scale * 0.004

            scale *= texturescalefactor

            gl.glVertex3fv (p.org)

            mathlib.VectorMA (p.org, scale, up, p_up)
            gl.glVertex3fv (p_up)

            mathlib.VectorMA (p.org, scale, right, p_right)
            gl.glVertex3fv (p_right)

            p = p.next
        gl.glEnd()