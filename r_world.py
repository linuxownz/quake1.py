#r_world.py 

import gl_rmisc
import gl_vidsdl
import glquake

vertAttrIndex      = 0
texCoordsAttrIndex = 1
LMCoordsAttrIndex  = 2

r_world_program     = 0
texLoc              = 0
LMTexLoc            = 0
fullbrightTexLoc    = 0
useFullbrightTexLoc = 0
useOverbrightLoc    = 0
useAlphaTestLoc     = 0
useLightmapWideLoc  = 0
useLightmapOnlyLoc  = 0
alphaLoc            = 0

def GLWorld_CreateShaders():
    global texLoc             
    global LMTexLoc           
    global fullbrightTexLoc   
    global useFullbrightTexLoc
    global useOverbrightLoc   
    global useAlphaTestLoc    
    global useLightmapWideLoc 
    global useLightmapOnlyLoc 
    global alphaLoc           

    global r_world_program

    bindings : list[glquake.glsl_attrib_binding_t] = [
        glquake.glsl_attrib_binding_t('Vert', vertAttrIndex),
        glquake.glsl_attrib_binding_t('Vert', texCoordsAttrIndex),
        glquake.glsl_attrib_binding_t('Vert', LMCoordsAttrIndex),
    ]

    vertSource = '''#version 110                                          
    attribute vec4 Vert;
    attribute vec2 TexCoords;
    attribute vec2 LMCoords;
    
    varying float FogFragCoord;
    
    void main()
    {
       gl_TexCoord[0] = vec4(TexCoords, 0.0, 0.0);
       gl_TexCoord[1] = vec4(LMCoords, 0.0, 0.0);
       gl_Position = gl_ModelViewProjectionMatrix * Vert;
       FogFragCoord = gl_Position.w;
    };'''

    fragSource = '''#version 110
    uniform sampler2D Tex;                                                                               
    uniform sampler2D LMTex;
    uniform sampler2D FullbrightTex;
    uniform bool UseFullbrightTex;
    uniform bool UseOverbright;
    uniform bool UseAlphaTest;
    uniform bool UseLightmapWide;
    uniform bool UseLightmapOnly;
    uniform float Alpha;
    
    varying float FogFragCoord;
    
    void main()
    {
       vec4 result = texture2D(Tex, gl_TexCoord[0].xy);
       if (UseLightmapOnly)
           result = vec4(0.5, 0.5, 0.5, 1.0);
       if (UseAlphaTest && (result.a < 0.666))
           discard;
       result *= texture2D(LMTex, gl_TexCoord[1].xy);
       if (UseLightmapWide)
           result.rgb *= 4.0;
       if (UseOverbright)
           result.rgb *= 2.0;
       if (UseFullbrightTex)
           result += texture2D(FullbrightTex, gl_TexCoord[0].xy);
       result = clamp(result, 0.0, 1.0);
       float fog = exp(-gl_Fog.density * gl_Fog.density * FogFragCoord * FogFragCoord);
       fog = clamp(fog, 0.0, 1.0);
       result = mix(gl_Fog.color, result, fog);
       result.a = Alpha; // FIXME: This will make almost transparent things cut holes though heavy fog
       gl_FragColor = result;
    };'''

    if not gl_vidsdl.gl_glsl_alias_able:
        return 

    r_world_program = gl_rmisc.GL_CreateProgram(vertSource, fragSource, len(bindings), bindings)

    if r_world_program != 0:
        texLoc              = gl_rmisc.GL_GetUniformLocation(r_world_program, "Tex")                          
        LMTexLoc            = gl_rmisc.GL_GetUniformLocation (r_world_program, "LMTex")
        fullbrightTexLoc    = gl_rmisc.GL_GetUniformLocation (r_world_program, "FullbrightTex")
        useFullbrightTexLoc = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseFullbrightTex")
        useOverbrightLoc    = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseOverbright")
        useAlphaTestLoc     = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseAlphaTest")
        useLightmapWideLoc  = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseLightmapWide")
        useLightmapOnlyLoc  = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseLightmapOnly")
        alphaLoc            = gl_rmisc.GL_GetUniformLocation (r_world_program, "Alpha")
