# Guest Gamescope teardown

A PD2 session left `gamescopereaper` and a detached `winedevice.exe` alive after
Gamescope exited. Wine retained the launcher/game locks and controller event
handles. The installed reaper sends TERM and waits without a bounded escalation;
a process-group-only fix cannot contain a helper that calls `setsid()`.
Upstream [3.16.22 reaper source](https://github.com/ValveSoftware/gamescope/blob/3.16.22/src/Apps/gamescopereaper.cpp)
and [issue 1482](https://github.com/ValveSoftware/gamescope/issues/1482)
match this failure pattern. The separate SDL teardown abort lacks a backtrace;
this change contains its consequences rather than claiming an upstream repair.

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
application/compositor outcomes and confirmed cleanup. Normal picker output is
in `~/.local/state/rocknix-desktop/gamescope-apps.log`. A cleanup timeout is not
concealed: a successful app may return success only after the service's empty
cleanup boundary is confirmed.
