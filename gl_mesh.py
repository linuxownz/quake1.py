# gl_mesh.py

import struct

from OpenGL import GL

import cl_main
import gl_model
import modelgen
import quakedef  # remove me when types are migrated
import r_alias

# External renderer globals needed for lighting normals

MAXALIASTRIS = 4000
MAXALIASVERTS = 2000
MAXALIASFRAMES = 1024
MAX_COMMANDS = 16384

commands: list[int] = [0 for _ in range(MAXALIASTRIS * 7 + 1)]
numcommands: int = 0

vertexorder: list[int] = [0 for _ in range(MAXALIASTRIS * 3)]
numorder: int = 0

stripverts: list[int] = [0 for _ in range(MAXALIASTRIS + 2)]
striptris: list[int] = [0 for _ in range(MAXALIASTRIS)]
stripcount: int = 0


# These three tables are shared C globals (gl_model.c fills them while parsing the
# .mdl, gl_mesh.c reads them).  They are bound from gl_model in
# GL_MakeAliasModelDisplayLists; poseverts is converted from raw bytes to
# _trivertx objects there.
triangles: list = []
stverts: list = []
poseverts: list = []


class _trivertx:
    """trivertx_t: three packed byte coordinates plus a lightnormalindex."""

    __slots__ = ("v", "lightnormalindex")

    def __init__(self, x: int, y: int, z: int, n: int):
        self.v = (x, y, z)
        self.lightnormalindex = n


MESHXYZ_T_SIZEOF = 3
MESHST_SIZEOF = 4

used: list[int] = []
gl_glsl_alias_able: bool = True


class aliasmesh_t:
    """Structure matching aliasmesh_t C struct for VBO mesh generation."""

    def __init__(self):
        self.vertindex: int = 0
        self.st: list[int] = [0, 0]


def GL_ClearBufferBindings() -> None:
    """Unbinds active OpenGL array and element array VBOs."""
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
    GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)


def StripLength(starttri: int, startv: int) -> int:
    """Calculates maximum triangle strip length starting at starttri using startv."""
    global stripcount, stripverts, striptris, used, triangles, pheader

    used[starttri] = 2
    last = triangles[starttri]

    stripverts[0] = last.vertindex[startv % 3]
    stripverts[1] = last.vertindex[(startv + 1) % 3]
    stripverts[2] = last.vertindex[(startv + 2) % 3]

    striptris[0] = starttri
    stripcount = 1

    m1 = last.vertindex[(startv + 2) % 3]
    m2 = last.vertindex[(startv + 1) % 3]

    while True:
        found_next = False

        for j in range(starttri + 1, pheader.numtris):
            check = triangles[j]

            if check.facesfront != last.facesfront:
                continue

            for k in range(3):
                if check.vertindex[k] != m1:
                    continue
                if check.vertindex[(k + 1) % 3] != m2:
                    continue

                if used[j]:
                    found_next = False
                    break

                new_vert = check.vertindex[(k + 2) % 3]
                if stripcount & 1:
                    m2 = new_vert
                else:
                    m1 = new_vert

                stripverts[stripcount + 2] = new_vert
                striptris[stripcount] = j
                stripcount += 1

                used[j] = 2
                found_next = True
                break

            if found_next:
                break

        if not found_next:
            break

    for j_cleanup in range(starttri + 1, pheader.numtris):
        if used[j_cleanup] == 2:
            used[j_cleanup] = 0

    return stripcount


def FanLength(starttri: int, startv: int) -> int:
    """Calculates maximum triangle fan length starting at starttri using startv as root."""
    global stripcount, stripverts, striptris, used, triangles, pheader

    used[starttri] = 2
    last = triangles[starttri]

    stripverts[0] = last.vertindex[startv % 3]
    stripverts[1] = last.vertindex[(startv + 1) % 3]
    stripverts[2] = last.vertindex[(startv + 2) % 3]

    striptris[0] = starttri
    stripcount = 1

    m1 = last.vertindex[startv % 3]
    m2 = last.vertindex[(startv + 2) % 3]

    while True:
        found_next = False

        for j in range(starttri + 1, pheader.numtris):
            check = triangles[j]

            if check.facesfront != last.facesfront:
                continue

            for k in range(3):
                if check.vertindex[k] != m1:
                    continue
                if check.vertindex[(k + 1) % 3] != m2:
                    continue

                if used[j]:
                    found_next = False
                    break

                m2 = check.vertindex[(k + 2) % 3]

                stripverts[stripcount + 2] = m2
                striptris[stripcount] = j
                stripcount += 1

                used[j] = 2
                found_next = True
                break

            if found_next:
                break

        if not found_next:
            break

    for j_cleanup in range(starttri + 1, pheader.numtris):
        if used[j_cleanup] == 2:
            used[j_cleanup] = 0

    return stripcount


def BuildTris() -> None:
    """Builds optimized GL triangle strips/fans for alias model rendering."""
    global numorder, numcommands, used, commands, vertexorder
    global pheader, triangles, stverts
    global stripverts, striptris

    numorder = 0
    numcommands = 0
    commands = [0] * MAX_COMMANDS
    vertexorder = [0] * MAX_COMMANDS
    used = [0] * pheader.numtris

    bestverts = [0] * (MAXALIASTRIS + 2)
    besttris = [0] * MAXALIASTRIS

    for i in range(pheader.numtris):
        if used[i]:
            continue

        bestlen = 0
        besttype = 0

        for type_idx in range(2):  # 0 = Fan, 1 = Strip
            for startv in range(3):
                if type_idx == 1:
                    length = StripLength(i, startv)
                else:
                    length = FanLength(i, startv)

                if length > bestlen:
                    besttype = type_idx
                    bestlen = length
                    for j in range(bestlen + 2):
                        bestverts[j] = stripverts[j]
                    for j in range(bestlen):
                        besttris[j] = striptris[j]

        for j in range(bestlen):
            used[besttris[j]] = 1

        if besttype == 1:
            commands[numcommands] = bestlen + 2
        else:
            commands[numcommands] = -(bestlen + 2)
        numcommands += 1

        for j in range(bestlen + 2):
            k = bestverts[j]
            vertexorder[numorder] = k
            numorder += 1

            s = float(stverts[k].s)
            t = float(stverts[k].t)

            if not triangles[besttris[0]].facesfront and stverts[k].onseam:
                s += pheader.skinwidth / 2.0

            s = (s + 0.5) / float(pheader.skinwidth)
            t = (t + 0.5) / float(pheader.skinheight)

            tmp_s = struct.unpack("i", struct.pack("f", s))[0]
            commands[numcommands] = tmp_s
            numcommands += 1

            tmp_t = struct.unpack("i", struct.pack("f", t))[0]
            commands[numcommands] = tmp_t
            numcommands += 1

    commands[numcommands] = 0
    numcommands += 1


def TexMgr_PadConditional(size: int) -> int:
    """Returns power-of-two padded texture dimension if GL hardware requires it."""
    return size


def GL_MakeAliasModelDisplayLists(m: object, hdr: object) -> None:
    """Generates optimized mesh commands, texture scaling, and pose vertex buffers."""
    global pheader
    global numorder, numcommands, commands, vertexorder
    global triangles, stverts, poseverts

    pheader = hdr
    paliashdr = hdr

    # Share the tables gl_model just filled (see comment at top of module)
    triangles = gl_model.triangles
    stverts = gl_model.stverts
    poseverts = []
    for i in range(hdr.numposes):
        raw = gl_model.poseverts[i]
        poseverts.append([
            _trivertx(raw[o], raw[o + 1], raw[o + 2], raw[o + 3])
            for o in range(0, hdr.numverts * 4, 4)
        ])

    hscale = float(hdr.skinwidth) / float(TexMgr_PadConditional(hdr.skinwidth))
    vscale = float(hdr.skinheight) / float(TexMgr_PadConditional(hdr.skinheight))

    BuildTris()

    paliashdr.poseverts = numorder

    out_cmds = []
    load_idx = 0

    while True:
        count = commands[load_idx]
        load_idx += 1

        out_cmds.append(count)

        if count == 0:
            break

        if count < 0:
            count = -count

        for _ in range(count):
            s_raw = commands[load_idx]
            load_idx += 1
            s_float = struct.unpack("f", struct.pack("i", s_raw))[0]

            t_raw = commands[load_idx]
            load_idx += 1
            t_float = struct.unpack("f", struct.pack("i", t_raw))[0]

            scaled_s = hscale * s_float
            scaled_t = vscale * t_float

            out_cmds.append(struct.unpack("i", struct.pack("f", scaled_s))[0])
            out_cmds.append(struct.unpack("i", struct.pack("f", scaled_t))[0])

    paliashdr.commands = out_cmds

    flat_verts = []
    for i in range(paliashdr.numposes):
        for j in range(numorder):
            vert_idx = vertexorder[j]
            flat_verts.append(poseverts[i][vert_idx])

    paliashdr.posedata = flat_verts
    GL_MakeAliasModelDisplayLists_VBO(m, paliashdr)


def GL_MakeAliasModelDisplayLists_VBO(aliasmodel: object, paliashdr: object) -> None:
    """Generates VBO mesh descriptors, element index lists, and uploads VBO buffers."""
    global gl_glsl_alias_able, pheader, triangles, stverts, poseverts

    if not gl_glsl_alias_able:
        return

    verts = []
    for i in range(paliashdr.numposes):
        for j in range(paliashdr.numverts):
            verts.append(poseverts[i][j])

    paliashdr.vertexes = verts

    desc = [aliasmesh_t() for _ in range(pheader.numverts * 2)]
    indexes = [0] * (pheader.numtris * 3)

    pheader.meshdesc = desc
    pheader.indexes = indexes
    pheader.numindexes = 0
    pheader.numverts_vbo = 0

    remap = [0] * (paliashdr.numverts * 2)

    for i in range(pheader.numtris):
        for j in range(3):
            vertindex = triangles[i].vertindex[j]
            v = vertindex * 2

            if not triangles[i].facesfront and stverts[vertindex].onseam:
                v += 1

            if not remap[v]:
                s = stverts[vertindex].s
                t = stverts[vertindex].t

                if v & 1:
                    s += paliashdr.skinwidth // 2

                desc[pheader.numverts_vbo].vertindex = vertindex
                desc[pheader.numverts_vbo].st[0] = s
                desc[pheader.numverts_vbo].st[1] = t

                pheader.numverts_vbo += 1
                remap[v] = pheader.numverts_vbo

            indexes[pheader.numindexes] = remap[v] - 1
            pheader.numindexes += 1

    # Direct local invocation without gl_mesh prefix or hasattr
    GLMesh_LoadVertexBuffer(aliasmodel, pheader)


def GLMesh_LoadVertexBuffer(m: object, hdr: object) -> None:
    """Builds and uploads hardware vertex and element index VBOs for alias models."""
    global gl_glsl_alias_able

    if not gl_glsl_alias_able:
        return

    m.vboindexofs = 0
    m.vboxyzofs = 0

    SIZEOF_MESHXYZ = 8
    SIZEOF_MESHST = 8

    totalvbosize = hdr.numposes * hdr.numverts_vbo * SIZEOF_MESHXYZ
    m.vbostofs = totalvbosize
    totalvbosize += hdr.numverts_vbo * SIZEOF_MESHST

    if not hdr.numindexes or not totalvbosize:
        return

    desc = hdr.meshdesc
    indexes = hdr.indexes
    trivertexes = hdr.vertexes

    if m.meshindexesvbo:
        GL.glDeleteBuffers(1, [m.meshindexesvbo])
        m.meshindexesvbo = 0

    m.meshindexesvbo = int(GL.glGenBuffers(1))
    GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, m.meshindexesvbo)

    index_bytes = struct.pack(f"<{hdr.numindexes}H", *indexes[: hdr.numindexes])
    GL.glBufferData(
        GL.GL_ELEMENT_ARRAY_BUFFER,
        len(index_bytes),
        index_bytes,
        GL.GL_STATIC_DRAW,
    )

    vbodata = bytearray(totalvbosize)

    xyz_offset = 0
    for f in range(hdr.numposes):
        tv_base = f * hdr.numverts

        for v in range(hdr.numverts_vbo):
            vert_idx = desc[v].vertindex
            trivert = trivertexes[tv_base + vert_idx]

            v0, v1, v2 = trivert.v[0], trivert.v[1], trivert.v[2]

            norm_idx = trivert.lightnormalindex
            norm_vec = r_alias.r_avertexnormals[norm_idx]
            n0 = int(127.0 * norm_vec[0]) & 0xFF
            n1 = int(127.0 * norm_vec[1]) & 0xFF
            n2 = int(127.0 * norm_vec[2]) & 0xFF

            struct.pack_into(
                "4B4B",
                vbodata,
                xyz_offset,
                v0, v1, v2, 1,
                n0, n1, n2, 0,
            )
            xyz_offset += SIZEOF_MESHXYZ

    hscale = 1.0 / float(TexMgr_PadConditional(hdr.skinwidth))
    vscale = 1.0 / float(TexMgr_PadConditional(hdr.skinheight))

    st_offset = m.vbostofs
    for f in range(hdr.numverts_vbo):
        s_val = hscale * (float(desc[f].st[0]) + 0.5)
        t_val = vscale * (float(desc[f].st[1]) + 0.5)

        struct.pack_into("<2f", vbodata, st_offset, s_val, t_val)
        st_offset += SIZEOF_MESHST

    if m.meshvbo:
        GL.glDeleteBuffers(1, [m.meshvbo])
        m.meshvbo = 0

    m.meshvbo = int(GL.glGenBuffers(1))
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, m.meshvbo)
    GL.glBufferData(
        GL.GL_ARRAY_BUFFER,
        totalvbosize,
        bytes(vbodata),
        GL.GL_STATIC_DRAW,
    )

    GL_ClearBufferBindings()


def GLMesh_LoadVertexBuffers() -> None:
    """Uploads VBOs for all alias models in precache."""
    if not gl_glsl_alias_able:
        return

    for j in range(quakedef.MAX_MODELS):
        m = cl_main.cl.model_precache[j]
        if not m:
            break
        if m.type != quakedef.modtype_t.mod_alias:
            continue

        hdr = gl_model.Mod_Extradata(m)
        GLMesh_LoadVertexBuffer(m, hdr)


def GLMesh_DeleteVertexBuffers() -> None:
    """Deletes hardware VBOs for all alias models in precache."""
    if not gl_glsl_alias_able:
        return

    for j in range(1, quakedef.MAX_MODELS):
        m = cl_main.cl.model_precache[j]
        if not m:
            break
        if m.type != quakedef.modtype_t.mod_alias:
            continue

        if m.meshvbo:
            GL.glDeleteBuffers(1, [m.meshvbo])
            m.meshvbo = 0

        if m.meshindexesvbo:
            GL.glDeleteBuffers(1, [m.meshindexesvbo])
            m.meshindexesvbo = 0

    GL_ClearBufferBindings()