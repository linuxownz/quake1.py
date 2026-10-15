#!/usr/bin/python
# main_sdl.py for main_sdl.c

import atexit
import sys

import sdl2
import sdl2.ext

import cl_main
import common
import console
import gl_vidsdl
import host
import sv_main
import sys_sdl_unix
import sys_sdl_unix as unix


def Sys_AtExit():
    sdl2.SDL_Quit()
    console.LOG_Close()

def Sys_InitSDL():
    version = sdl2.SDL_version()
    sdl2.SDL_GetVersion(version)

    print(f"SDL Version: {version.major}.{version.minor}.{version.patch}")

    if sdl2.SDL_Init(0) < 0:
        print(f"Couldn't init SDL: {sdl2.SDL_GetError()}");
        sys.exit(1)

    atexit.register( Sys_AtExit )

def main():
    global cvar
    import cvar
    host.membase = bytearray(host.memsize)

    if host.membase is None:
        unix.Sys_Error(f"failed to alloc {host.memsize} bytes of memory")

    common.COM_InitArgv()
    Sys_InitSDL()
    unix.Sys_Init()

    print("Initializing QuakeSpasm.py v1.0")

    sys_sdl_unix.Sys_Printf('host init')
    host.Host_Init()

    oldtime = sys_sdl_unix.Sys_DoubleTime()
    if sys_sdl_unix.Sys_IsDedicated():
        while True:
            sys_ticrate = int(cvar.Cvar_GetCvar('sys_ticrate').value)
            newtime = sys_sdl_unix.Sys_DoubleTime()
            time = newtime - oldtime

            while time < sys_ticrate:
                sdl2.SDL_Delay(1)
                newtime = sys_sdl_unix.Sys_DoubleTime()
                time = newtime - oldtime

            host.Host_Frame(time)
            oldtime = newtime

    else:
        sys_throttle = float(cvar.Cvar_GetCvar('sys_throttle').value)

        # optional profiling: run with  -profile <seconds>  (default 20).  Profiling starts
        # once a map is fully loaded (signon complete) and 60 frames have rendered, so the
        # numbers show steady-state frame cost, not level loading.  Stats are printed and
        # written to profile.txt when time is up, then the game exits.
        prof = None
        _acc = [0.0, 0.0, 0.0, 0]  # Host_Frame, SwapWindow, Delay, loops (profile mode only)
        prof_secs = 0.0
        prof_end = 0.0
        prof_ready_frame = None
        pi = common.COM_CheckParm('-profile')
        if pi:
            import cProfile
            import quakedef
            try:
                prof_secs = float(common.com_argv[pi + 1])
            except (IndexError, ValueError):
                prof_secs = 20.0

        while True:
            if pi and prof is None and prof_secs:
                if cl_main.cls.signon == quakedef.SIGNONS and not cl_main.cls.demoplayback:
                    if prof_ready_frame is None:
                        prof_ready_frame = host.host_framecount + 60
                    elif host.host_framecount >= prof_ready_frame:
                        prof = cProfile.Profile()
                        prof_end = sys_sdl_unix.Sys_DoubleTime() + prof_secs
                        prof.enable()
                else:
                    prof_ready_frame = None
            if prof is not None and sys_sdl_unix.Sys_DoubleTime() > prof_end:
                prof.disable()
                import io
                import pstats
                out = io.StringIO()
                st = pstats.Stats(prof, stream=out)
                st.sort_stats('tottime').print_stats(30)
                out.write('\n--- by cumulative time ---\n')
                st.sort_stats('cumulative').print_stats(30)
                out.write('\nmain loop wall time: Host_Frame %.2fs, SwapWindow %.2fs, SDL_Delay %.2fs over %d iterations\n' % tuple(_acc))
                print(out.getvalue())
                with open('profile.txt', 'w') as f:
                    f.write(out.getvalue())
                break

            #print(f"cls.state: {cl_main.cls.state} | host_frametime: {host.host_frametime} | sv.time: {sv_main.sv.time}")


            if not gl_vidsdl.VID_HasMouseOrInputFocus() or cl_main.cl.paused:
                sdl2.SDL_Delay(16)

            if gl_vidsdl.VID_IsMinimized():
                gl_vidsdl.scr_skipupdate = True
                sdl2.SDL_Delay(32)
            else:
                gl_vidsdl.scr_skipupdate = False

            newtime = sys_sdl_unix.Sys_DoubleTime()
            time = newtime - oldtime

            # swap only when a frame was actually drawn (Host_FilterTime may skip it);
            # swapping an undrawn back buffer presents stale frames
            framecount = host.host_framecount
            swaps = gl_vidsdl.swap_count
            _t0 = sys_sdl_unix.Sys_DoubleTime()
            host.Host_Frame(time)
            _t1 = sys_sdl_unix.Sys_DoubleTime()
            # swap here only if a frame was drawn AND the renderer did not already swap
            # (GL_EndRendering): a second swap presents the stale back buffer from
            # a previous frame right before the new one
            if host.host_framecount != framecount and gl_vidsdl.swap_count == swaps:
                gl_vidsdl.swap_count += 1
                sdl2.SDL_GL_SwapWindow(gl_vidsdl.draw_context)
            _t2 = sys_sdl_unix.Sys_DoubleTime()

            if time < sys_throttle and not cl_main.cls.timedemo:
                sdl2.SDL_Delay(1)
            _t3 = sys_sdl_unix.Sys_DoubleTime()
            if prof is not None:
                _acc[0] += _t1 - _t0
                _acc[1] += _t2 - _t1
                _acc[2] += _t3 - _t2
                _acc[3] += 1

            oldtime = newtime

    return 0

if __name__ == '__main__':
    main()
