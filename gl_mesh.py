#gl_mesh.py

from OpenGL import GL

import cl_main
import gl_model
import quakedef  #remove me

MAXALIASTRIS = 4000

commands: list[int] = [[0] * ( MAXALIASTRIS * 7 + 1 )]
numcommands: int = 0

vertexorder: list[int] = [[0] * MAXALIASTRIS * 3]
numorder: int = 0

stripverts: list[int] = [ [0] * ( MAXALIASTRIS + 2 )]
striptris : list[int] = [ [0] * MAXALIASTRIS]
stripcount: int = 0

# Set during GL_MakeAliasModelDisplayLists / BuildTris
pheader: object = None
triangles: list = []
used: list[int] = []
MAX_COMMANDS = 16384
stverts: list = []
poseverts: list = []  # Matrix/List of pose vertex structures [numposes][numverts]

MESHXYZ_T_SIZEOF = 3
MESHST_SIZEOF = 4


def StripLength(starttri: int, startv: int) -> int:
    """Calculates maximum triangle strip length starting at starttri using startv.

    C equivalent:
    static int StripLength (int starttri, int startv) in gl_mesh.c
    """
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

    # Outer loop corresponding to 'nexttri' label in C
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

                # Found matching adjacent triangle in strip sequence

                # If triangle is already committed or staged, stop the strip construction
                if used[j]:
                    found_next = False
                    break

                # Determine new edge vertex
                new_vert = check.vertindex[(k + 2) % 3]
                if stripcount & 1:
                    m2 = new_vert
                else:
                    m1 = new_vert

                stripverts[stripcount + 2] = new_vert
                striptris[stripcount] = j
                stripcount += 1

                used[j] = 2

                # Set flag to restart search loop from starttri + 1 (goto nexttri)
                found_next = True
                break

            if found_next or (used[j] and check.vertindex[k] == m1 and check.vertindex[(k + 1) % 3] == m2):
                break

        if not found_next:
            break

    # Clear temporary candidate usage flags (marker 2 -> 0)
    for j_cleanup in range(starttri + 1, pheader.numtris):
        if used[j_cleanup] == 2:
            used[j_cleanup] = 0

    return stripcount


def FanLength(starttri: int, startv: int) -> int:
    """Calculates maximum triangle fan length starting at starttri using startv as root.

    C equivalent:
    static int FanLength (int starttri, int startv) in gl_mesh.c
    """
    global stripcount, stripverts, striptris, used, triangles, pheader

    used[starttri] = 2

    last = triangles[starttri]

    stripverts[0] = last.vertindex[startv % 3]
    stripverts[1] = last.vertindex[(startv + 1) % 3]
    stripverts[2] = last.vertindex[(startv + 2) % 3]

    striptris[0] = starttri
    stripcount = 1

    # m1 remains the fixed central hub vertex of the fan
    m1 = last.vertindex[startv % 3]
    # m2 tracks the trailing edge vertex along the fan's outer perimeter
    m2 = last.vertindex[(startv + 2) % 3]

    # Outer loop corresponding to 'nexttri' label in C
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

                # Found next adjacent triangle in fan sequence

                # If triangle is already committed or staged, stop fan construction
                if used[j]:
                    found_next = False
                    break

                # Update trailing perimeter vertex (m1 remains fixed)
                m2 = check.vertindex[(k + 2) % 3]

                stripverts[stripcount + 2] = m2
                striptris[stripcount] = j
                stripcount += 1

                used[j] = 2

                # Restart search loop from starttri + 1 (goto nexttri)
                found_next = True
                break

            if found_next or (used[j] and check.vertindex[k] == m1 and check.vertindex[(k + 1) % 3] == m2):
                break

        if not found_next:
            break

    # Clear temporary candidate usage flags (marker 2 -> 0)
    for j_cleanup in range(starttri + 1, pheader.numtris):
        if used[j_cleanup] == 2:
            used[j_cleanup] = 0

    return stripcount





def BuildTris() -> None:
    """Builds optimized GL triangle strips/fans for alias model rendering.

    C equivalent:
    static void BuildTris (void) in gl_mesh.c
    """
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
        # Pick an unused triangle and attempt starting a strip or fan
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

        # Mark used triangles on the best strip as used
        for j in range(bestlen):
            used[besttris[j]] = 1

        # Command code: positive count = TRIANGLE_STRIP, negative = TRIANGLE_FAN
        if besttype == 1:
            commands[numcommands] = bestlen + 2
        else:
            commands[numcommands] = -(bestlen + 2)
        numcommands += 1

        for j in range(bestlen + 2):
            # Emit vertex index into the reorder buffer
            k = bestverts[j]
            vertexorder[numorder] = k
            numorder += 1

            # Extract texture coordinates
            s = float(stverts[k].s)
            t = float(stverts[k].t)

            # Adjust s-coordinate if triangle is on back face skin seam
            if not triangles[besttris[0]].facesfront and stverts[k].onseam:
                s += pheader.skinwidth / 2.0

            # Normalize UV coordinates to [0.0, 1.0] range
            s = (s + 0.5) / float(pheader.skinwidth)
            t = (t + 0.5) / float(pheader.skinheight)

            # Bitcast float -> 32-bit signed int (C memcpy (&tmp, &s, 4))
            tmp_s = struct.unpack("i", struct.pack("f", s))[0]
            commands[numcommands] = tmp_s
            numcommands += 1

            tmp_t = struct.unpack("i", struct.pack("f", t))[0]
            commands[numcommands] = tmp_t
            numcommands += 1

    # End of command stream marker
    commands[numcommands] = 0
    numcommands += 1



def TexMgr_PadConditional(size: int) -> int:
    """Returns power-of-two padded texture dimension if GL hardware requires it."""
    # Placeholder: returns size directly or next power-of-two depending on GL capabilities
    return size


def GL_MakeAliasModelDisplayLists(m: object, hdr: object) -> None:
    """Generates optimized mesh commands, texture scaling, and pose vertex buffers.

    Args:
        m: qmodel_t instance representing the alias model.
        hdr: aliashdr_t structure containing model header metadata.

    C equivalent:
    void GL_MakeAliasModelDisplayLists (qmodel_t *m, aliashdr_t *hdr) in gl_mesh.c
    """
    global pheader, triangles, stverts, poseverts
    global numorder, numcommands, commands, vertexorder

    # Bind active header and data references to module state for BuildTris
    pheader = hdr
    triangles = getattr(hdr, "triangles", [])
    stverts = getattr(hdr, "stverts", [])
    poseverts = getattr(hdr, "poseverts_data", [])

    paliashdr = hdr

    # Calculate padded skin scale factors
    hscale = float(hdr.skinwidth) / float(TexMgr_PadConditional(hdr.skinwidth))
    vscale = float(hdr.skinheight) / float(TexMgr_PadConditional(hdr.skinheight))

    # Generate mesh commands and vertex reorder indices
    BuildTris()

    # Save poseverts count
    paliashdr.poseverts = numorder

    # Process and scale command stream texture coordinates
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
            # Unpack float s/t coords stored as raw bit-packed ints in commands stream
            s_raw = commands[load_idx]
            load_idx += 1
            s_float = struct.unpack("f", struct.pack("i", s_raw))[0]

            t_raw = commands[load_idx]
            load_idx += 1
            t_float = struct.unpack("f", struct.pack("i", t_raw))[0]

            # Apply texture padding scaling
            scaled_s = hscale * s_float
            scaled_t = vscale * t_float

            # Repack scaled float UVs back to bit-identical int representation
            out_cmds.append(struct.unpack("i", struct.pack("f", scaled_s))[0])
            out_cmds.append(struct.unpack("i", struct.pack("f", scaled_t))[0])

    paliashdr.commands = out_cmds

    # Flatten pose vertex data according to vertexorder mapping
    flat_verts = []
    for i in range(paliashdr.numposes):
        for j in range(numorder):
            vert_idx = vertexorder[j]
            flat_verts.append(poseverts[i][vert_idx])

    paliashdr.posedata = flat_verts

    # Optional VBO generation path (ericw extension)
    if hasattr(gl_mesh, "GL_MakeAliasModelDisplayLists_VBO"):
        gl_mesh.GL_MakeAliasModelDisplayLists_VBO(m, paliashdr)


# gl_mesh.py module globals matching C static globals
gl_glsl_alias_able: bool = True


class aliasmesh_t:
    """Structure matching aliasmesh_t C struct for VBO mesh generation."""

    def __init__(self):
        self.vertindex: int = 0
        self.st: list[int] = [0, 0]


def GL_MakeAliasModelDisplayLists_VBO( aliasmodel: object, paliashdr: object) -> None:
    """Generates VBO mesh descriptors, element index lists, and uploads VBO buffers.

    Args:
        aliasmodel: qmodel_t instance representing the alias model.
        paliashdr: aliashdr_t structure containing model header metadata.

    C equivalent:
    static void GL_MakeAliasModelDisplayLists_VBO (qmodel_t *aliasmodel, aliashdr_t *paliashdr) in gl_mesh.c
    """
    global gl_glsl_alias_able, pheader, triangles, stverts, poseverts

    if not gl_glsl_alias_able:
        return

    # First, copy pose vertices directly in raw linear order
    verts = []
    for i in range(paliashdr.numposes):
        for j in range(paliashdr.numverts):
            verts.append(poseverts[i][j])

    paliashdr.vertexes = verts

    # Pre-allocate descriptor list (up to numverts * 2 for seam adjustments)
    desc = [aliasmesh_t() for _ in range(pheader.numverts * 2)]

    # Pre-allocate element index array
    indexes = [0] * (pheader.numtris * 3)

    pheader.meshdesc = desc
    pheader.indexes = indexes
    pheader.numindexes = 0
    pheader.numverts_vbo = 0

    # Remap array tracks unique emitted vertices (1-based index marker; 0 = unmapped)
    remap = [0] * (paliashdr.numverts * 2)

    for i in range(pheader.numtris):
        for j in range(3):
            # Index into header vertex arrays
            vertindex = triangles[i].vertindex[j]

            # Index into remap table
            v = vertindex * 2

            # Check for back-side seam vertex duplicate requirement
            if not triangles[i].facesfront and stverts[vertindex].onseam:
                v += 1

            # Emit new unique VBO vertex if not already processed
            if not remap[v]:
                s = stverts[vertindex].s
                t = stverts[vertindex].t

                # Check for back-side seam offset adjustment
                if v & 1:
                    s += paliashdr.skinwidth // 2

                desc[pheader.numverts_vbo].vertindex = vertindex
                desc[pheader.numverts_vbo].st[0] = s
                desc[pheader.numverts_vbo].st[1] = t

                pheader.numverts_vbo += 1
                remap[v] = pheader.numverts_vbo

            # Emit element array index (converting back from 1-based remap index)
            indexes[pheader.numindexes] = remap[v] - 1
            pheader.numindexes += 1

    # Upload generated vertex/index buffers to GPU hardware
    if hasattr(gl_mesh, "GLMesh_LoadVertexBuffer"):
        gl_mesh.GLMesh_LoadVertexBuffer(aliasmodel, pheader)



def GLMesh_LoadVertexBuffer(m: object, hdr: object) -> None:
    """Builds and uploads hardware vertex and element index VBOs for alias models."""
    global gl_glsl_alias_able, r_avertexnormals

    if not gl_glsl_alias_able:
        return

    m.vboindexofs = 0
    m.vboxyzofs = 0

    SIZEOF_MESHXYZ = 8
    SIZEOF_MESHST = 8

    totalvbosize = (hdr.numposes * hdr.numverts_vbo * SIZEOF_MESHXYZ)
    m.vbostofs = totalvbosize
    totalvbosize += (hdr.numverts_vbo * SIZEOF_MESHST)

    if not hdr.numindexes or not totalvbosize:
        return

    # Direct struct field access matching C pointer arithmetic
    desc = hdr.meshdesc
    indexes = hdr.indexes
    trivertexes = hdr.vertexes

    # 1. Upload Element Index Buffer
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

    # Allocate linear byte buffer for vertex attributes
    vbodata = bytearray(totalvbosize)

    # 2. Fill Vertex Positions and Normals
    xyz_offset = 0
    for f in range(hdr.numposes):
        tv_base = f * hdr.numverts

        for v in range(hdr.numverts_vbo):
            vert_idx = desc[v].vertindex
            trivert = trivertexes[tv_base + vert_idx]

            v0, v1, v2 = trivert.v[0], trivert.v[1], trivert.v[2]

            norm_idx = trivert.lightnormalindex
            norm_vec = r_avertexnormals[norm_idx]
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

    # 3. Fill ST Texture Coordinates
    hscale = 1.0 / float(TexMgr_PadConditional(hdr.skinwidth))
    vscale = 1.0 / float(TexMgr_PadConditional(hdr.skinheight))

    st_offset = m.vbostofs
    for f in range(hdr.numverts_vbo):
        s_val = hscale * (float(desc[f].st[0]) + 0.5)
        t_val = vscale * (float(desc[f].st[1]) + 0.5)

        struct.pack_into("<2f", vbodata, st_offset, s_val, t_val)
        st_offset += SIZEOF_MESHST

    # 4. Upload Array Vertex Buffer
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

def GLMesh_LoadVertexBuffers():
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
    """Deletes hardware VBOs for all alias models in the precache array.

    C equivalent:
    void GLMesh_DeleteVertexBuffers (void) in gl_mesh.c
    """
    if not gl_glsl_alias_able:
        return

    for j in range(1, quakedef.MAX_MODELS):
        m = cl_main.cl.model_precache[j]
        if not m:
            break
        if m.type != quakedef.modtype_t.mod_alias:
            continue

        # Delete vertex array VBO
        if m.meshvbo:
            GL.glDeleteBuffers(1, [m.meshvbo])
            m.meshvbo = 0

        # Delete element index VBO
        if m.meshindexesvbo:
            GL.glDeleteBuffers(1, [m.meshindexesvbo])
            m.meshindexesvbo = 0

    GL_ClearBufferBindings()