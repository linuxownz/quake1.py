#gl_rsurf.py 

import OpenGL.GL as gl

import gl_texmgr


def R_DrawBaseSurface(fa):
    poly = fa.polys
    if not poly:
        return

    # Pass 1: Texture
    # (Your existing glBegin loop)
    gl.glBegin(gl.GL_POLYGON)
    for i in range(poly.numverts):
        v = poly.verts[i]
        gl.glTexCoord2f(v[3], v[4])
        gl.glVertex3f(v[0], v[1], v[2])
    gl.glEnd()

    # Pass 2: Lightmap (The 'Glow' or 'Shadow' layer)
    # Only draw if the face has lighting data (skip sky, etc.)
    if fa.lightofs != -1:
        gl.glEnable(gl.GL_BLEND)
        # GL_DST_COLOR * GL_ZERO multiplies the texture by the lightmap
        gl.glBlendFunc(gl.GL_DST_COLOR, gl.GL_ZERO)
        
        # Note: In a modern engine, we'd use glActiveTexture(GL_TEXTURE1)
        # for a single-pass, but multi-pass is easier to debug initially.
        gl_texmgr.GL_Bind(fa.lightmap_texture) 

        gl.glBegin(gl.GL_POLYGON)
        for i in range(poly.numverts):
            v = poly.verts[i]
            # Lightmap S/T coordinates (we need to calculate these next)
            gl.glTexCoord2f(v[5], v[6]) 
            gl.glVertex3f(v[0], v[1], v[2])
        gl.glEnd()
        
        gl.glDisable(gl.GL_BLEND)

def R_DrawTextureChains(model):
    """Walks the model's textures and draws all faces attached to them."""
    for tex in model.textures:
        if not tex.texturechains:
            continue
            
        # Bind the texture once for the whole chain (Optimization!)
        gl_texmgr.GL_Bind(tex.gltexture)
        
        for face in tex.texturechains:
            R_DrawBaseSurface(face)

def R_RenderWorld(model):
    """The main entry point for drawing the map geometry."""
    gl.glEnable(gl.GL_TEXTURE_2D)
    
    # In a full engine, we'd do PVS/Recursive World Culling here.
    # For now, we draw the whole 'Texture Chain'.
    R_DrawTextureChains(model)