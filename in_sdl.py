#in_sdl.py


import ctypes
import math

import sdl2
import sdl2.ext

import cl_input
import cl_main
import common
import console
import cvar
import host
import host_cmd
import keys
import protocol
import quakedef
import snd_dma
import sys_sdl_unix
import view

windowhasfocus = True
textmode = False

joy_active_instanceid: sdl2.SDL_JoystickID     = -1
joy_active_controller: sdl2.SDL_GameController = None

no_mouse = False

buttonremap = []
total_dx = 0
total_dy = 0

class joyaxis_t:
    def __init__(self):
        self.x = 0
        self.y = 0

class joybuttonstate_t:
    def __init__(self):
        self.buttondown: list[bool] = [False for _ in range(sdl2.SDL_CONTROLLER_BUTTON_MAX)]

class joyaxisstate_t:
    def __init__(self):
        self.axisvalue: list[float] = [0.0 for _ in range(sdl2.SDL_CONTROLLER_AXIS_MAX)]

joy_buttonstate: joybuttonstate_t = joybuttonstate_t()
joy_axisstate: joyaxisstate_t = joyaxisstate_t()
joy_buttontimer: list[float] = [0.0 for _ in range(sdl2.SDL_CONTROLLER_BUTTON_MAX)]
joy_emulatedkeytimer: list[float] = [0.0 for _ in range(6)]

def IN_ClearStates():
    # empty in original source
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
        keys.Key.K_MOUSE1,
        keys.Key.K_MOUSE3,
        keys.Key.K_MOUSE2,
        keys.Key.K_MOUSE4,
        keys.Key.K_MOUSE5
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

def IN_ShutdownJoystick():
    sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_GAMECONTROLLER)



def IN_MouseMotion(dx, dy):
    global total_dx, total_dy
    if not windowhasfocus:
        dx = dy = 0
    total_dx += dx
    total_dy += dy

    return


    # gemini code
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


def IN_AxisMagnitude(axis: joyaxis_t) -> float:
    magnitude: float = math.sqrt((axis.x * axis.x) + (axis.y * axis.y))
    return magnitude

def IN_ApplyEasing(axis: joyaxis_t, exponent: float) -> joyaxis_t:
    result: joyaxis_t = joyaxis_t()
    eased_magnitude: float = 0.0
    magnitude: float = IN_AxisMagnitude(axis)

    if magnitude == 0.0:
        return result

    eased_magnitude = math.pow(magnitude, exponent)

    result.x = axis.x * ( eased_magnitude / magnitude)
    result.y = axis.y * ( eased_magnitude / magnitude)
    return result


def IN_ApplyDeadzone(axis: joyaxis_t, deadzone: float, outer_threshold: float) -> joyaxis_t:
    result: joyaxis_t = joyaxis_t()
    magnitude: float = IN_AxisMagnitude(axis)

    if magnitude > deadzone:
        new_magnitude: float = min(1.0, (magnitude - deadzone) / (1.0 - deadzone - outer_threshold))
        scale: float = new_magnitude / magnitude
        result.x = axis.x * scale
        result.y = axis.y * scale

    return result



def IN_KeyForControllerButton(button: sdl2.SDL_GameControllerButton) -> int:
    match button:
        case sdl2.SDL_CONTROLLER_BUTTON_A: return keys.K_ABUTTON
        case sdl2.SDL_CONTROLLER_BUTTON_B: return keys.K_BBUTTON
        case sdl2.SDL_CONTROLLER_BUTTON_X: return keys.K_XBUTTON
        case sdl2.SDL_CONTROLLER_BUTTON_Y: return keys.K_YBUTTON
        case sdl2.SDL_CONTROLLER_BUTTON_BACK: return keys.K_TAB
        case sdl2.SDL_CONTROLLER_BUTTON_START: return keys.K_ESCAPE
        case sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK: return keys.K_LTHUMB
        case sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK: return keys.K_RTHUMB
        case sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER: return keys.K_LSHOULDER
        case sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: return keys.K_RSHOULDER
        case sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP: return keys.K_UPARROW
        case sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN: return keys.K_DOWNARROW
        case sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT: return keys.K_LEFTARROW
        case sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT: return keys.K_RIGHTARROW
        case _: return 0



def IN_JoyKeyEvent(wasdown: bool, isdown: bool, key: int, timer: float) -> float:
    currenttime = sys_sdl_unix.Sys_DoubleTime()
    result = timer

    if wasdown:
        if isdown:
            if currenttime >= timer:
                result = currenttime + 0.1
                keys.Key_Event(key, True)
        else:
            result = 0
            keys.Key_Event(key, False)
    else:
        if isdown:
            result = currenttime + 0.5
            keys.Key_Event(key,  True)

    return result


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
                    snd_dma.S_UnblockSound()
                elif event.window.event == sdl2.SDL_WINDOWEVENT_FOCUS_LOST:
                    windowhasfocus = False
                    snd_dma.S_BlockSound()

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

                keys.Key_EventWithKeycode(key, down, event.key.keysym.sym)

            case sdl2.SDL_MOUSEBUTTONDOWN | sdl2.SDL_MOUSEBUTTONUP:
                if event.button.button < 1 or event.button.button > len(buttonremap):
                    console.Con_Printf('ignored event for mouse button %d' % event.button.button)  # noqa: UP031
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


def IN_DebugTextEvent(event: sdl2.SDL_Event):
    console.Con_Printf(f'SDL_TEXTINPUT: {event.text.text} {sys_sdl_unix.Sys_DoubleTime()}')


def IN_DebugKeyEvent(event: sdl2.SDL_Event):
    eventtype = 'SDL_KEYDOWN' if event.key.state == sdl2.SDL_PRESSED else 'SDL_KEYUP'
    console.Con_Printf(f'{eventtype} {sdl2.SDL_GetScancodeName(event.key.keysym.scancode)} {sdl2.SDL_GetKeyName(event.key.keysym.sym)} {sys_sdl_unix.Sys_DoubleTime()}')



def IN_Shutdown():
    IN_Deactivate(True)
    IN_ShutdownJoystick()

def IN_MouseMove(cmd: protocol.usercmd_t):
    global total_dx, total_dy

    sensitivity = cvar.Cvar_GetCvar('sensitivity').value

    dmx = total_dx * sensitivity
    dmy = total_dy * sensitivity

    total_dx = total_dy = 0

    if cl_main.cl.paused or keys.key_dest != keys.keydest_t.key_game:
        return

    lookstrafe = cvar.Cvar_GetCvar('lookstrafe').value
    m_side = cvar.Cvar_GetCvar('m_side').value
    m_yaw  = cvar.Cvar_GetCvar('m_yaw').value
    m_pitch = cvar.Cvar_GetCvar('m_pitch').value
    m_forward = cvar.Cvar_GetCvar('m_forward').value
    cl_maxpitch = cvar.Cvar_GetCvar('cl_maxpitch')
    cl_minpitch = cvar.Cvar_GetCvar('cl_minpitch')

    if ( cl_input.in_strafe.state & 1 ) or lookstrafe and ( cl_input.in_mlook.state & 1 ):
        cmd.sidemove += m_side * dmx
    else:
        cl_main.cl.viewangles[quakedef.YAW] -= m_yaw * dmx

    if cl_input.in_mlook.state & 1 and (dmx or dmy):
        view.V_StopPitchDrift()

    if ( cl_input.in_mlook.state & 1 ) and not ( cl_input.in_strafe.state & 1 ):
        cl_main.cl.viewangles[quakedef.PITCH] += m_pitch * dmy
        cl_main.cl.viewangles[quakedef.PITCH] = min(cl_main.cl.viewangles[quakedef.PITCH], cl_maxpitch)
        cl_main.cl.viewangles[quakedef.PITCH] = max(cl_main.cl.viewangles[quakedef.PITCH], cl_minpitch)

    else:
        if ( cl_input.in_strafe.state & 1 ) and host_cmd.noclip_anglehack:
            cmd.upmove -= m_forward * dmy
        else:
            cmd.forwardmove -= m_forward * dmy


def IN_Move(cmd: protocol.usercmd_t):
    IN_JoyMove(cmd)
    IN_MouseMove(cmd)


def IN_UpdateInputMode():
    global textmode

    want_textmode = keys.Key_TextEntry()
    if textmode != want_textmode:
        textmode = want_textmode

        in_debugkeys = cvar.Cvar_GetCvar('in_debugkeys').value

        if textmode:
            sdl2.SDL_StartTextInput()
            if in_debugkeys:
                console.Con_Printf(f'SDL_StartTextInput: time {sys_sdl_unix.Sys_DoubleTime()}')

        else:
            sdl2.SDL_StopTextInput()
            if in_debugkeys:
                console.Con_Printf(f'SDL_StopTextInput: time {sys_sdl_unix.Sys_DoubleTime()}')




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


def IN_Commands():
    global joy_axisstate
    newaxisstate: joyaxisstate_t = joyaxisstate_t()
    stickthreshold = 0.9
    triggerthreshold = cvar.Cvar_GetCvar('joy_deadzone_trigger').value

    if not cvar.Cvar_GetCvar('joy_enable').value:
        return

    if not joy_active_controller:
        return

    for i in range(sdl2.SDL_CONTROLLER_BUTTON_MAX):
        newstate: bool = sdl2.SDL_GameControllerGetButton(joy_active_controller, i)
        oldstate: bool = joy_buttonstate.buttondown[i]

        joy_buttonstate.buttondown[i] = newstate
        joy_buttontimer[i] = IN_JoyKeyEvent(oldstate, newstate, IN_KeyForControllerButton(i), joy_buttontimer[i])

    for i in range(sdl2.SDL_CONTROLLER_AXIS_MAX):
        newaxisstate.axisvalue[i] = sdl2.SDL_GameControllerGetAxis(joy_active_controller, i / 32768.0)

    if keys.key_dest != keys.keydest_t.key_game:
        joy_emulatedkeytimer[0] = IN_JoyKeyEvent(joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTX] < -stickthreshold, newaxisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTX] < -stickthreshold, keys.K_LEFTARROW, joy_emulatedkeytimer[0])
        joy_emulatedkeytimer[1] = IN_JoyKeyEvent(joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTX] > stickthreshold,  newaxisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTX] > stickthreshold, keys.K_RIGHTARROW, joy_emulatedkeytimer[1])
        joy_emulatedkeytimer[2] = IN_JoyKeyEvent(joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTY] < -stickthreshold, newaxisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTY] < -stickthreshold, keys.K_UPARROW,   joy_emulatedkeytimer[2])
        joy_emulatedkeytimer[3] = IN_JoyKeyEvent(joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTY] > stickthreshold,  newaxisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTY] > stickthreshold, keys.K_DOWNARROW,  joy_emulatedkeytimer[3])

    joy_emulatedkeytimer[4] = IN_JoyKeyEvent(joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT] > triggerthreshold,  newaxisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT] > triggerthreshold,  keys.K_LTRIGGER, joy_emulatedkeytimer[4])
    joy_emulatedkeytimer[5] = IN_JoyKeyEvent(joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT] > triggerthreshold, newaxisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT] > triggerthreshold,  keys.K_RTRIGGER, joy_emulatedkeytimer[5])

    joy_axisstate = newaxisstate


def IN_JoyMove(cmd: protocol.usercmd_t):
    speed = 0.0
    moveRaw: joyaxis_t = joyaxis_t()
    moveDeadzone: joyaxis_t = joyaxis_t()
    moveEased: joyaxis_t = joyaxis_t()
    lookRaw: joyaxis_t = joyaxis_t()
    lookDeadzone: joyaxis_t = joyaxis_t()
    lookEased: joyaxis_t = joyaxis_t()

    if not cvar.Cvar_GetCvar('joy_enable').value:
        return

    if not joy_active_controller:
        return

    if cl_main.cl.paused or keys.key_dest != keys.keydest_t.key_game:
        return

    moveRaw.x = joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTX]
    moveRaw.y = joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_LEFTY]
    lookRaw.x = joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_RIGHTX]
    lookRaw.y = joy_axisstate.axisvalue[sdl2.SDL_CONTROLLER_AXIS_RIGHTY]

    if cvar.Cvar_GetCvar('joy_swapmovelook').value:
        temp: joyaxis_t = moveRaw
        moveRaw = lookRaw
        lookRaw = temp

    joy_exponent = cvar.Cvar_GetCvar('joy_exponent').value
    joy_deadzone_move = cvar.Cvar_GetCvar('joy_deadzone_move').value
    joy_deadzone_look = cvar.Cvar_GetCvar('joy_deadzone_look').value
    joy_exponent_move = cvar.Cvar_GetCvar('joy_exponent_move').value
    joy_outer_threshold_move = cvar.Cvar_GetCvar('joy_outer_threshold_move').value
    joy_outer_threshold_look = cvar.Cvar_GetCvar('joy_outer_threshold_look').value


    moveDeadzone = IN_ApplyDeadzone(moveRaw, joy_deadzone_move, joy_outer_threshold_move)
    lookDeadzone = IN_ApplyDeadzone(lookRaw, joy_deadzone_look, joy_outer_threshold_look)

    moveEased = IN_ApplyEasing(moveDeadzone, joy_exponent_move)
    lookEased = IN_ApplyEasing(lookDeadzone, joy_exponent)

    cl_alwaysrun = cvar.Cvar_GetCvar('cl_alwaysrun').value
    cl_forwardspeed = cvar.Cvar_GetCvar('cl_forwardspeed').value
    sv_maxspeed = cvar.Cvar_GetCvar('sv_maxspeed').value
    cl_movespeedkey = cvar.Cvar_GetCvar('cl_movespeedkey').value

    if ( cl_input.in_speed.state & 1 ) ^ ( cl_alwaysrun != 0.0 or cl_forwardspeed >= sv_maxspeed ):
        speed = sv_maxspeed
    elif cl_forwardspeed >= sv_maxspeed:
        speed = min(sv_maxspeed, cl_forwardspeed/ cl_movespeedkey.value)
    else:
        speed = cl_forwardspeed

    cmd.sidemove += speed * moveEased.x
    cmd.forwardmove += speed * moveEased.y

    joy_sensitivity_yaw = cvar.Cvar_GetCvar('joy_sensitivity_yaw').value
    joy_sensitivity_pitch = cvar.Cvar_GetCvar('joy_sensitivity_pitch').value
    joy_invert = cvar.Cvar_GetCvar('joy_invert').value

    cl_main.cl.viewangles[quakedef.YAW] -= lookEased.x * joy_sensitivity_yaw * host.host_frametime
    cl_main.cl.viewangles[quakedef.PITCH] -= lookEased.y * joy_sensitivity_pitch * host.host_frametime * -1.0 if joy_invert else 1.0

    if lookEased.x != 0 or lookEased.y != 0:
        view.V_StopPitchDrift()

    cl_main.cl.viewangles[quakedef.PITCH] = min(cl_main.cl.viewangles[quakedef.PITCH], cl_main.cl_maxpitch.value)
    cl_main.cl.viewangles[quakedef.PITCH] = max(cl_main.cl.viewangles[quakedef.PITCH], cl_main.cl_minpitch.value)



