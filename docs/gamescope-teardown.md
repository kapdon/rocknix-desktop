# Guest Gamescope teardown

A PD2 session left `gamescopereaper` and a detached `winedevice.exe` alive after
Gamescope exited. Wine retained the launcher/game locks and controller event
handles. The original reaper sent TERM and waited without a bounded escalation;
a process-group-only fix cannot contain a helper that calls `setsid()`.
Upstream [3.16.22 reaper source](https://github.com/ValveSoftware/gamescope/blob/3.16.22/src/Apps/gamescopereaper.cpp)
and [issue 1482](https://github.com/ValveSoftware/gamescope/issues/1482)
match this failure pattern. The packaged SDL backend also destroyed a joinable `std::thread` during
`steamcompmgr_exit`, causing `std::terminate` on normal teardown. The guest
package backports upstream [16a44df7](https://github.com/ValveSoftware/gamescope/commit/16a44df7b4a067daf62a38d73d87a0a9cdca45a3):
post `SDL_QUIT`, return from the event loop, and join the SDL thread before
backend destruction. Window visibility and Vulkan presentation also share a
lock: SDL cannot unmap the outer Wayland surface while a frame is being
presented, and hidden windows are not presented to. Without this ordering,
closing the last app window can leave Mesa waiting indefinitely for a Wayland
frame callback. The surface can still hide and reopen during the same session.
The package also bounds reaper shutdown: signal handlers
only set a flag, primary-child waits poll that flag, and descendant cleanup
escalates TERM to KILL after three seconds. After five seconds it returns control
to Gamescope; the enclosing systemd service must still prove the cgroup empty.
This prevents a normal outer-window close from hanging on a detached Wine helper
after the SDL abort is repaired. Debian's source and packaging archives are checksum-pinned;
the package retains Debian's dependencies and installation paths. Sources,
build script and patch ship under
`/usr/local/share/rocknix-desktop/gamescope-source`.

## Lifetime boundary

`rocknix-gamescope` now creates a unique transient **user service**. Its
supervisor watches both the primary application and compositor. Primary exit
requests compositor shutdown, with a three-second grace before KILL. Compositor
exit ends the supervisor; systemd terminates all remaining service descendants,
including detached Wine helpers, with five-second TERM-to-KILL escalation.
Cleanup is accepted only once the unit is inactive/failed with no control group.
It never uses process-name killing or prefix-wide `wineserver -k`.

The original argv, working directory and desktop environment travel in a private
0600 request file. Only systemd control commands use `/run/user/1000/bus`; the
application retains the existing Desktop D-Bus and Wayland endpoints. The guest
user manager persists while LXC is running. Container shutdown ends its services.
No host account, native Steam launcher or native Steam scope changes.

The native FEX server starts separately as `rocknix-fex-server.service`, UID1000,
with its own runtime directory. Its readiness pipe gates Desktop startup, and
wrapped launches require it to be active when the native FEX provider exists.
This prevents the first game from owning a shared server inside its cleanup
boundary. FEX still uses the existing native binaries/rootfs and user config.

Direct `gamescope` calls bypass this wrapper. Apps forwarding into an existing
instance or an external D-Bus service cannot be pulled into this launch's group;
close existing instances first. Deliberately delegated user services are also
outside the boundary. Concurrent Wine apps sharing one prefix may already share
a wineserver: this does not create independent Wine-prefix ownership.

## Diagnostics

Per-launch JSON under `~/.local/state/rocknix-desktop/gamescope-sessions` records
application/compositor outcomes, whether the supervisor requested compositor
shutdown, and confirmed cleanup. A clean compositor exit with no application
status (for example closing the outer SDL window) is successful after cleanup.
SIGABRT and other compositor faults remain failures, even after app success;
only the supervisor's explicit TERM/KILL escalation is accepted. Startup faults
are not inferred from log strings or converted into success. Normal picker output is
in `~/.local/state/rocknix-desktop/gamescope-apps.log`. A cleanup timeout is not
concealed: a successful app may return success only after the service's empty
cleanup boundary is confirmed.

## Local regression checks

`python3 tests/gamescope-session.py` exercises exit status and supervision with
real child processes plus mocked service control. On a machine with a running
user systemd manager, `python3 tests/gamescope-service.py` additionally verifies
that detached TERM-resistant descendants are gone after normal exit and a
compositor abort or segfault, while an unrelated process survives. These synthetic fixtures
do not replace Mousepad/PD2, Wine cleanup or shared FEX validation on the RP6.

`python3 tests/gamescope-reaper.py /path/to/gamescopereaper` tests the actual
packaged reaper against native synthetic children. It also accepts an explicit
QEMU executable before the binary path. Cases cover primary exit, TERM during
a resistant primary, and TERM with respawn enabled; each checks descendant
removal and survival of an unrelated process.
