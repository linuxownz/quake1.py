#in_sdl.py


import ctypes

import sdl2
import sdl2.ext

import cl_input
import cl_main
import common
import console
import keys
import sys_sdl_unix

windowhasfocus = True
textmode = False

joy_active_instanceid: sdl2.SDL_JoystickID     = -1
joy_active_controller: sdl2.SDL_GameController = None

no_mouse = False

buttonremap = []
total_dx = 0
total_dy = 0

def IN_ClearStates():
    pass

def IN_FilterMouseEvents(event:sdl2.SDL_Event):
    match sdl2.event.type:
        case  sdl2.SDL_MOUSEMOTION:
            return 0

    return 1

def IN_SDL2_FilterMouseEvents(userdata, event: sdl2.SDL_Event):
    return IN_FilterMouseEvents(event)

cl_sensitivity = None

def IN_Init():
    global textmode
    global no_mouse
    global buttonremap
    global cl_sensitivity

    buttonremap = [
        keys.K_MOUSE1,
        keys.K_MOUSE3,
        keys.K_MOUSE2,
        keys.K_MOUSE4,
        keys.K_MOUSE5
    ]

    import cvar

    #cvar.Cvar_RegisterVariable({ 'name': 'sensitivity', 'value': '3', 'flags': cvar.CVAR_ARCHIVE })

    cl_sensitivity = cvar.Cvar_GetCvar('sensitivity')

    in_debugkeys             = { 'name':'in_debugkeys',             'value':'0',     'flags':cvar.CVAR_NONE}
    joy_deadzone_look        = { 'name':"joy_deadzone_look",        'value':"0.175", 'flags':cvar.CVAR_ARCHIVE }
    joy_deadzone_move        = { 'name':"joy_deadzone_move",        'value':"0.175", 'flags':cvar.CVAR_ARCHIVE }
    joy_outer_threshold_look = { 'name':"joy_outer_threshold_look", 'value':"0.02",  'flags':cvar.CVAR_ARCHIVE }
    joy_outer_threshold_move = { 'name':"joy_outer_threshold_move", 'value':"0.02",  'flags':cvar.CVAR_ARCHIVE }
    joy_deadzone_trigger     = { 'name':"joy_deadzone_trigger",     'value':"0.2",   'flags':cvar.CVAR_ARCHIVE }
    joy_sensitivity_yaw      = { 'name':"joy_sensitivity_yaw",      'value':"240",   'flags':cvar.CVAR_ARCHIVE }
    joy_sensitivity_pitch    = { 'name':"joy_sensitivity_pitch",    'value':"130",   'flags':cvar.CVAR_ARCHIVE }
    joy_invert               = { 'name':"joy_invert",               'value': "0",    'flags':cvar.CVAR_ARCHIVE }
    joy_exponent             = { 'name':"joy_exponent",             'value': "2",    'flags':cvar.CVAR_ARCHIVE }
    joy_exponent_move        = { 'name':"joy_exponent_move",        'value': "2",    'flags':cvar.CVAR_ARCHIVE }
    joy_swapmovelook         = { 'name':"joy_swapmovelook",         'value': "0",    'flags':cvar.CVAR_ARCHIVE }
    joy_enable               = { 'name':"joy_enable",               'value': "1",    'flags':cvar.CVAR_ARCHIVE }

    textmode = keys.Key_TextEntry()

    if textmode:
        sdl2.SDL_StartTextInput()
    else:
        sdl2.SDL_StopTextInput()

    if common.safemode or common.COM_CheckParm('-nomouse'):
        no_mouse = True
        IN_BeginIgnoringMouseEvents()

    cvar.Cvar_RegisterVariable(in_debugkeys);
    cvar.Cvar_RegisterVariable(joy_sensitivity_yaw);
    cvar.Cvar_RegisterVariable(joy_sensitivity_pitch);
    cvar.Cvar_RegisterVariable(joy_deadzone_look);
    cvar.Cvar_RegisterVariable(joy_deadzone_move);
    cvar.Cvar_RegisterVariable(joy_outer_threshold_look);
    cvar.Cvar_RegisterVariable(joy_outer_threshold_move);
    cvar.Cvar_RegisterVariable(joy_deadzone_trigger);
    cvar.Cvar_RegisterVariable(joy_invert);
    cvar.Cvar_RegisterVariable(joy_exponent);
    cvar.Cvar_RegisterVariable(joy_exponent_move);
    cvar.Cvar_RegisterVariable(joy_swapmovelook);
    cvar.Cvar_RegisterVariable(joy_enable);

    IN_Activate()
    IN_StartupJoystick()

def IN_Activate():
    if no_mouse:
        return

    if sdl2.SDL_SetRelativeMouseMode(sdl2.SDL_TRUE) != 0:
        console.Con_Printf('warning: SDL_SetRelativeMouseMode(sdl2.SDL_TRUE) failed \n')

    IN_EndIgnoringMouseEvents()

    total_dx = total_dy = 0

def IN_StartupJoystick():
    global joy_active_instanceid, joy_active_controller

    if common.COM_CheckParm('-nojoy'):
        return

    if sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_GAMECONTROLLER) == -1:
        console.Con_Warning('could not initialize game controller')
        return

    controllerdb = f'{common.com_basedir}/gamecontrollerdb.txt'.encode()
    nummappings = sdl2.SDL_GameControllerAddMappingsFromFile(controllerdb)

    if nummappings > 0:
        console.Con_Printf(f'{nummappings} mappings loaded from {controllerdb}')

    for i in range(sdl2.SDL_NumJoysticks()):
        joyname = sdl2.SDL_JoystickNameForIndex(i)
        if sdl2.SDL_IsGameController(i):
            controllername = sdl2.SDL_GameControllerNameForIndex(i)
            gamecontroller = sdl2.SDL_GameControllerOpen(i)

            if gamecontroller:
                console.Con_Printf('detected controller {controllername}')
                joy_active_instanceid = sdl2.SDL_JoystickInstanceID(sdl2.SDL_GameControllerGetJoystick(gamecontroller))
                joy_active_controller = gamecontroller
                break
            else:
                console.Con_Warning(f'failed to open controller {controllername}')
        else:
            console.Con_Warning(f'joystick missing controller mappings {joyname}')

def IN_MouseMotion(dx, dy):
    global total_dx, total_dy

    # 1. Check console state
    if keys.key_dest != keys.keydest_t.key_game:
        return

    # 2. Use the parameters 'dx' and 'dy' passed from SDL
    # Instead of total_dx, use the actual movement 'dx'
    sensitivity = 3.0
    m_yaw = 0.022
    m_pitch = 0.022

    # 3. Apply directly to the angles
    cl_main.cl.viewangles[1] -= dx * sensitivity * m_yaw
    cl_main.cl.viewangles[0] -= dy * sensitivity * m_pitch

    # 4. Clamp Pitch
    if cl_main.cl.viewangles[0] > 80:
        cl_main.cl.viewangles[0] = 80
    elif cl_main.cl.viewangles[0] < -70:
        cl_main.cl.viewangles[0] = -70

def IN_SendKeyEvents():
    global joy_active_controller
    global joy_active_instanceid
    global windowhasfocus

    sdl2.SDL_StartTextInput()
    #in_debugkeys = int(cvar.Cvar_GetCvar('in_debugkeys').value)

    event : sdl2.SDL_Event = sdl2.SDL_Event()

    while sdl2.SDL_PollEvent(event):
        match event.type:
            case sdl2.SDL_WINDOWEVENT:
                if event.window.event == sdl2.SDL_WINDOWEVENT_FOCUS_GAINED:
                    windowhasfocus = True
                    #S_UnblockSound()
                elif event.window.event == sdl2.SDL_WINDOWEVENT_FOCUS_LOST:
                    windowhasfocus = False
                    #S_BlockSound()

            case sdl2.SDL_TEXTINPUT:
                if keys.key_dest == keys.keydest_t.key_console:
                    text = event.text.text.decode('utf-8').split('\x00')[0]
                    # Don't type the character if it's the console toggle
                    if text not in ('`', '~'):
                        for char in text:
                            keys.Key_Console(ord(char))


            case sdl2.SDL_KEYDOWN | sdl2.SDL_KEYUP:
                down = (event.key.state == sdl2.SDL_PRESSED)
                key = IN_SDL2_ScancodeToQuakeKey(event.key.keysym.scancode)

                if isinstance(key, str):
                    key = ord(key)

                # 1. ALWAYS handle the console toggle first
                # 96 is the ASCII for ` (backquote)
                if key == 96:
                    keys.Key_Event(key, down)
                    continue

                if keys.key_dest == keys.keydest_t.key_game:
                    down = (event.key.state == sdl2.SDL_PRESSED)

                    # --- STRAFING (A/D) ---
                    if key == ord('w'):
                        cl_input.in_forward.state = (cl_input.in_forward.state | 1 | 2) if down else (cl_input.in_forward.state & ~1)
                    elif key == ord('s'):
                        cl_input.in_back.state = (cl_input.in_back.state | 1 | 2) if down else (cl_input.in_back.state & ~1)
                    elif key == ord('a'):
                        cl_input.in_strafe_left.state = (cl_input.in_strafe_left.state | 1 | 2) if down else (cl_input.in_strafe_left.state & ~1)
                    elif key == ord('d'):
                        cl_input.in_strafe_right.state = (cl_input.in_strafe_right.state | 1 | 2) if down else (cl_input.in_strafe_right.state & ~1)

                    # --- TURNING (Arrow Keys) ---
                    if key == keys.K_LEFTARROW:
                        cl_input.in_turn_left.state = (cl_input.in_turn_left.state | 1) if down else 0
                    elif key == keys.K_RIGHTARROW:
                        cl_input.in_turn_right.state = (cl_input.in_turn_right.state | 1) if down else 0
                    elif key == keys.K_UPARROW:
                        cl_input.in_pitch_up.state = (cl_input.in_pitch_up.state | 1) if down else 0
                    elif key == keys.K_DOWNARROW:
                        cl_input.in_pitch_down.state = (cl_input.in_pitch_down.state | 1) if down else 0

                # 2. If console is open, handle navigation keys
                if keys.key_dest == keys.keydest_t.key_console:

                    if keys.keydown[keys.K_CTRL]:
                        if key == ord('l'):
                            console.Con_Clear_f()

                    control_keys = (
                        keys.K_ENTER, keys.K_ESCAPE, keys.K_BACKSPACE,
                        keys.K_UPARROW, keys.K_DOWNARROW,
                        keys.K_LEFTARROW, keys.K_RIGHTARROW,
                        keys.K_TAB, keys.K_PGUP, keys.K_PGDN,
                        keys.K_CTRL, keys.K_ALT
                    )
                    if key in control_keys:
                        keys.Key_Event(key, down)
                    continue

                # 3. Standard gameplay path
                if key:
                    keys.Key_EventWithKeycode(key, down, event.key.keysym.sym)

            case sdl2.SDL_MOUSEBUTTONDOWN | sdl2.SDL_MOUSEBUTTONUP:
                if event.button.button < 1 or event.button.button > len(buttonremap):
                    console.Con_Printf('ignored event for mouse button %d' % event.button.button)
                else:
                    keys.Key_Event(buttonremap[event.button.button - 1], event.button.state == sdl2.SDL_PRESSED)

            case sdl2.SDL_MOUSEWHEEL:
                if event.wheel.y > 0:
                    keys.Key_Event(keys.K_MWHEELUP, True)
                    keys.Key_Event(keys.K_MWHEELUP, False)
                elif event.wheel.y < 0:
                    keys.Key_Event(keys.K_MWHEELDOWN, True)
                    keys.Key_Event(keys.K_MWHEELDOWN, False)

            case sdl2.SDL_MOUSEMOTION:
                IN_MouseMotion(event.motion.xrel, event.motion.yrel)

            case sdl2.SDL_CONTROLLERDEVICEADDED:
                if joy_active_instanceid == -1:
                    joy_active_controller = sdl2.SDL_GameControllerOpen(event.cdevice.which)

                    if joy_active_controller is None:
                        console.Con_Printf('Couldnt open game controller\n')
                    else:
                        joy = sdl2.SDL_GameControllerGetJoystick(joy_active_controller)
                        joy_active_instanceid = sdl2.SDL_JoystickInstanceID(joy)
                else:
                    console.Con_Printf('ignoring SDL_CONTROLLERDEVICEADDED\n')
            case sdl2.SDL_CONTROLLERDEVICEREMOVED:
                if joy_active_instanceid != -1 and event.cdevice.which == joy_active_instanceid:
                    sdl2.SDL_GameControllerClose(joy_active_controller)
                    joy_active_controller = None
                    joy_active_instanceid = -1
                else:
                    console.Con_Printf('Ignoring SDL_CONTROLLERDEVICEREMOVED\n')
            case sdl2.SDL_CONTROLLERDEVICEREMAPPED:
                console.Con_Printf('Ignoring SDL_CONTROLLERDEVICEREMAPPED\n')

            case sdl2.SDL_QUIT:
                cl_main.CL_Disconnect()
                sys_sdl_unix.Sys_Quit()

def IN_SDL2_ScancodeToQuakeKey(scancode):

    match scancode:
        case sdl2.SDL_SCANCODE_TAB:     return keys.K_TAB
        case sdl2.SDL_SCANCODE_RETURN:  return keys.K_ENTER
        case sdl2.SDL_SCANCODE_RETURN2: return keys.K_ENTER
        case sdl2.SDL_SCANCODE_ESCAPE:  return keys.K_ESCAPE
        case sdl2.SDL_SCANCODE_SPACE:   return keys.K_SPACE

        case sdl2.SDL_SCANCODE_A: return 'a'
        case sdl2.SDL_SCANCODE_B: return 'b'
        case sdl2.SDL_SCANCODE_C: return 'c'
        case sdl2.SDL_SCANCODE_D: return 'd'
        case sdl2.SDL_SCANCODE_E: return 'e'
        case sdl2.SDL_SCANCODE_F: return 'f'
        case sdl2.SDL_SCANCODE_G: return 'g'
        case sdl2.SDL_SCANCODE_H: return 'h'
        case sdl2.SDL_SCANCODE_I: return 'i'
        case sdl2.SDL_SCANCODE_J: return 'j'
        case sdl2.SDL_SCANCODE_K: return 'k'
        case sdl2.SDL_SCANCODE_L: return 'l'
        case sdl2.SDL_SCANCODE_M: return 'm'
        case sdl2.SDL_SCANCODE_N: return 'n'
        case sdl2.SDL_SCANCODE_O: return 'o'
        case sdl2.SDL_SCANCODE_P: return 'p'
        case sdl2.SDL_SCANCODE_Q: return 'q'
        case sdl2.SDL_SCANCODE_R: return 'r'
        case sdl2.SDL_SCANCODE_S: return 's'
        case sdl2.SDL_SCANCODE_T: return 't'
        case sdl2.SDL_SCANCODE_U: return 'u'
        case sdl2.SDL_SCANCODE_V: return 'v'
        case sdl2.SDL_SCANCODE_W: return 'w'
        case sdl2.SDL_SCANCODE_X: return 'x'
        case sdl2.SDL_SCANCODE_Y: return 'y'
        case sdl2.SDL_SCANCODE_Z: return 'z'

        case sdl2.SDL_SCANCODE_1: return '1'
        case sdl2.SDL_SCANCODE_2: return '2'
        case sdl2.SDL_SCANCODE_3: return '3'
        case sdl2.SDL_SCANCODE_4: return '4'
        case sdl2.SDL_SCANCODE_5: return '5'
        case sdl2.SDL_SCANCODE_6: return '6'
        case sdl2.SDL_SCANCODE_7: return '7'
        case sdl2.SDL_SCANCODE_8: return '8'
        case sdl2.SDL_SCANCODE_9: return '9'
        case sdl2.SDL_SCANCODE_0: return '0'

        case sdl2.SDL_SCANCODE_MINUS: return '-'
        case sdl2.SDL_SCANCODE_EQUALS: return '='
        case sdl2.SDL_SCANCODE_LEFTBRACKET: return '['
        case sdl2.SDL_SCANCODE_RIGHTBRACKET: return ']'
        case sdl2.SDL_SCANCODE_BACKSLASH: return '\\'
        case sdl2.SDL_SCANCODE_NONUSHASH: return '#'
        case sdl2.SDL_SCANCODE_SEMICOLON: return '';
        case sdl2.SDL_SCANCODE_APOSTROPHE: return '\''
        case sdl2.SDL_SCANCODE_GRAVE: return '`'
        case sdl2.SDL_SCANCODE_COMMA: return ','
        case sdl2.SDL_SCANCODE_PERIOD: return '.'
        case sdl2.SDL_SCANCODE_SLASH: return '/'
        case sdl2.SDL_SCANCODE_NONUSBACKSLASH: return '\\'

        case sdl2.SDL_SCANCODE_BACKSPACE: return keys.K_BACKSPACE
        case sdl2.SDL_SCANCODE_UP:        return keys.K_UPARROW
        case sdl2.SDL_SCANCODE_DOWN:      return keys.K_DOWNARROW
        case sdl2.SDL_SCANCODE_LEFT:      return keys.K_LEFTARROW
        case sdl2.SDL_SCANCODE_RIGHT:     return keys.K_RIGHTARROW

        case sdl2.SDL_SCANCODE_LALT: return keys.K_ALT
        case sdl2.SDL_SCANCODE_RALT: return keys.K_ALT
        case sdl2.SDL_SCANCODE_LCTRL: return keys.K_CTRL
        case sdl2.SDL_SCANCODE_RCTRL: return keys.K_CTRL
        case sdl2.SDL_SCANCODE_LSHIFT: return keys.K_SHIFT
        case sdl2.SDL_SCANCODE_RSHIFT: return keys.K_SHIFT

        case sdl2.SDL_SCANCODE_F1: return  keys.K_F1
        case sdl2.SDL_SCANCODE_F2: return  keys.K_F2
        case sdl2.SDL_SCANCODE_F3: return  keys.K_F3
        case sdl2.SDL_SCANCODE_F4: return  keys.K_F4
        case sdl2.SDL_SCANCODE_F5: return  keys.K_F5
        case sdl2.SDL_SCANCODE_F6: return  keys.K_F6
        case sdl2.SDL_SCANCODE_F7: return  keys.K_F7
        case sdl2.SDL_SCANCODE_F8: return  keys.K_F8
        case sdl2.SDL_SCANCODE_F9: return  keys.K_F9
        case sdl2.SDL_SCANCODE_F10: return keys.K_F10
        case sdl2.SDL_SCANCODE_F11: return keys.K_F11
        case sdl2.SDL_SCANCODE_F12: return keys.K_F12
        case sdl2.SDL_SCANCODE_INSERT: return keys.K_INS
        case sdl2.SDL_SCANCODE_DELETE: return keys.K_DEL
        case sdl2.SDL_SCANCODE_PAGEDOWN: return keys.K_PGDN
        case sdl2.SDL_SCANCODE_PAGEUP: return keys.K_PGUP
        case sdl2.SDL_SCANCODE_HOME: return keys.K_HOME
        case sdl2.SDL_SCANCODE_END: return keys.K_END

        case sdl2.SDL_SCANCODE_NUMLOCKCLEAR: return keys.K_KP_NUMLOCK
        case sdl2.SDL_SCANCODE_KP_DIVIDE: return keys.K_KP_SLASH
        case sdl2.SDL_SCANCODE_KP_MULTIPLY: return keys.K_KP_STAR
        case sdl2.SDL_SCANCODE_KP_MINUS: return keys.K_KP_MINUS
        case sdl2.SDL_SCANCODE_KP_7: return keys.K_KP_HOME
        case sdl2.SDL_SCANCODE_KP_8: return keys.K_KP_UPARROW
        case sdl2.SDL_SCANCODE_KP_9: return keys.K_KP_PGUP
        case sdl2.SDL_SCANCODE_KP_PLUS: return keys.K_KP_PLUS
        case sdl2.SDL_SCANCODE_KP_4: return keys.K_KP_LEFTARROW
        case sdl2.SDL_SCANCODE_KP_5: return keys.K_KP_5
        case sdl2.SDL_SCANCODE_KP_6: return keys.K_KP_RIGHTARROW
        case sdl2.SDL_SCANCODE_KP_1: return keys.K_KP_END
        case sdl2.SDL_SCANCODE_KP_2: return keys.K_KP_DOWNARROW
        case sdl2.SDL_SCANCODE_KP_3: return keys.K_KP_PGDN
        case sdl2.SDL_SCANCODE_KP_ENTER: return keys.K_KP_ENTER
        case sdl2.SDL_SCANCODE_KP_0: return keys.K_KP_INS
        case sdl2.SDL_SCANCODE_KP_PERIOD: return keys.K_KP_DEL

        case sdl2.SDL_SCANCODE_LGUI: return keys.K_COMMAND
        case sdl2.SDL_SCANCODE_RGUI: return keys.K_COMMAND

        case sdl2.SDL_SCANCODE_PAUSE: return keys.K_PAUSE

        case _: return 0;

def IN_Shutdown():
    pass
    #IN_Deactivate(True)
    #IN_ShutdownJoystick()

def IN_MouseMove():
    global total_dx, total_dy

    # 1. Don't move the camera if the console is open or we have no focus
    if keys.key_dest != keys.keydest_t.key_game or not windowhasfocus:
        total_dx = 0
        total_dy = 0
        return

    # 2. Get the Cvar values
    # We use the cached cl_sensitivity object we created in IN_Init
    # We'll also define m_yaw and m_pitch (Quake defaults)
    import cvar

    cl_sensitivity = float(cvar.Cvar_GetCvar('sensitivity').value)

    m_yaw = cvar.Cvar_VariableValue('m_yaw') if cvar.Cvar_FindVar('m_yaw') else 0.022
    m_pitch = cvar.Cvar_VariableValue('m_pitch') if cvar.Cvar_FindVar('m_pitch') else 0.022

    # 3. Apply the scaling: (Delta * Sensitivity * QuakeConstant)
    # The cl_sensitivity.value is updated LIVE by your console logic
    view_x = total_dx * cl_sensitivity * m_yaw
    view_y = total_dy * cl_sensitivity * m_pitch

    # 4. Apply to the client's view angles
    # Index 1 is Yaw (Left/Right), Index 0 is Pitch (Up/Down)
    cl_main.cl.viewangles[1] -= view_x
    cl_main.cl.viewangles[0] += view_y

    # 5. Clamp the pitch so the player can't flip upside down
    cl_main.cl.viewangles[0] = min(cl_main.cl.viewangles[0], 80)
    cl_main.cl.viewangles[0] = max(cl_main.cl.viewangles[0], -70)

    # 6. RESET the accumulation for the next frame
    total_dx = 0
    total_dy = 0


# Prototype: int (*SDL_EventFilter)(void* userdata, SDL_Event* event)
SDL_EVENTFILTER_PTR = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(sdl2.SDL_Event))

def IN_BeginIgnoringMouseEvents():
    sdl2.SDL_SetEventFilter(IN_SDL2_FilterMouseEvents_Callback, None)

def IN_EndIgnoringMouseEvents():
    null_filter = ctypes.cast(None, SDL_EVENTFILTER_PTR)
    sdl2.SDL_SetEventFilter(null_filter, None)

def IN_Deactivate(free_cursor):
    if no_mouse:
        return

    if free_cursor:
        sdl2.SDL_SetRelativeMouseMode(sdl2.SDL_FALSE)

    IN_BeginIgnoringMouseEvents()

def IN_SDL2_FilterMouseEvents_Logic(userdata, event_ptr):
    event = event_ptr.contents
    # Filter out mouse events
    if event.type in (sdl2.SDL_MOUSEMOTION, sdl2.SDL_MOUSEBUTTONDOWN,
                      sdl2.SDL_MOUSEBUTTONUP, sdl2.SDL_MOUSEWHEEL):
        return 0 # Drop event
    return 1 # Keep event

# This MUST be a global variable to prevent Garbage Collection
IN_SDL2_FilterMouseEvents_Callback = SDL_EVENTFILTER_PTR(IN_SDL2_FilterMouseEvents_Logic)

def IN_UpdateInputMode():
    import cvar
    global textmode

    want_textmode = keys.Key_TextEntry()

    if textmode != want_textmode:
        if textmode:
            sdl2.SDL_StartTextInput()
            if cvar.Cvar_GetCvar('in_debugkeys').value:
                console.Con_Printf('SDL_StartTextInput time %g' % sys_sdl_unix.Sys_DoubleTime())
        else:
            sdl2.SDL_StopTextInput()
            if cvar.Cvar_GetCvar('in_debugkeys').value:
                console.Con_Printf('SDL_StopTextInput time %g' % sys_sdl_unix.Sys_DoubleTime())


def IN_Commands():
    return
    # not implemented


