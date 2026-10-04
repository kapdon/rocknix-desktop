# Native Steam integration decision

Desktop reuses ROCKNIX's native Steam launcher and scope, including its host-root
execution model. This preserves the installed Steam library, launch settings and
native Gaming Mode behavior.

## Native launch identity

The upstream [ROCKNIX launcher source](https://github.com/ROCKNIX/distribution/tree/4a92dd9202eec29514705d84a68f0a7f602adfac)
starts EmulationStation as a root system service with `HOME=/storage`.
`steam_scope_reexec_if_needed` in `start_steam.sh` uses
`systemd-run --scope --slice=system.slice --unit=steam-bigpicture --collect` and
forwards `_STEAM_SCOPE`, `HOME`, `USER` and `TZ`. Setting `USER` is environment
propagation, not a credential change. The native ARM64 launch chain does not drop
privileges before starting Gamescope and Steam.

## Current design

One shared Steam installation and game library remain editable from Desktop.
No recursive ownership changes, second Steam installation, separate Proton
library or changes to the installed ROCKNIX scripts are required.

- **Close Desktop:** resolve the native `.desktop` shortcut and invoke installed
  `runemu.sh`. Allow ROCKNIX to create `steam-bigpicture.scope` normally, choose
  DRM presentation and apply native game settings.
- **Keep Desktop:** source the installed Steam scope helper and let it re-execute
  our nested-session entry point in the same native scope. The full native
  launcher currently selects DRM and stops Sway, so the nested Gamescope command
  remains Desktop-specific. A missing helper fails explicitly; there is no
  silent alternate launcher. Keep mode captures Steam's own exit status and
  restarts the nested session on its update/restart code 42 within the same scope.
  Normal exits, compositor failures without a client restart request, and stop
  signals end the session. Keep starts Steam without `-silent`;
  **Apps → Steam games → Show Steam** requests its main window again
  after the game exits or the client has been hidden. This reuses the current native client, including
  its display and shared-memory namespace. It is available only for Keep mode.
- `rocknix-desktop-games.service` supervises Desktop transitions, the available
  memory guard. Each launch receives a private tmpfs at `/dev/shm`, inherited
  by the native scope. Steam IPC and FEX statistics therefore share the session
  lifetime: stopping the scope releases that mount after its final process exits,
  including forced recovery. Host and LXC shared-memory objects are untouched.
  Steam and its children live in the native scope, not the
  supervisor service. Desktop owns the always-available one-tap controller
  override. Until tapped, automatic focus detection recognizes the native Steam
  scope and Gamescope Wayland clients in the mapped LXC. After a tap, the choice
  stays manual for the rest of that Desktop session.
- Stop/failure recovery stops the native scope before restoring binfmt,
  Desktop when it was closed. Manual controller selection in a retained Desktop
  survives game exit. Failed cleanup retains the journal. The
  native scope receives the session task limit after it appears.
- Maintenance checks refuse a live Steam scope, an active/transitional supervisor
  or an unfinished session journal. This covers the interval after the
  supervisor releases its lock and before recovery completes. The standalone
  installer checks before and after acquiring its lock, before downloading;
  copied updaters resolve this guard from their trusted helper directory.

Both modes retain the previously validated common SDR policy that disables the
optional Gamescope WSI bypass. This is a Desktop launch policy, not a firmware
modification. Scope reuse does not imply that Keep mode inherits every native
game setting.

## Nested virtual display sizing

**Settings → Gamescope settings → Virtual display · fit desktop** controls the
initial resolution for nested launches. It defaults to On, including when
upgrading older settings. On uses the current tiled client content
size published by the host Sway policy, excluding its decorations. If there are
no tiled clients, it uses the usable workspace bounds. Output scale converts
logical Sway dimensions to display pixels. Missing, invalid or stale geometry
fails the launch instead of silently substituting a guessed resolution.

For example, a current 1920×953 client gives Gamescope `-w 1920 -h 953` and
`-W 1920 -H 953`. This is a launch-time snapshot: opening a new tab, splitting a
workspace, showing the keyboard or moving the window can change the actual
allocation afterwards. Gamescope scales the complete internal display into its
outer window; the game resolution stays fixed until the next launch. This
avoids requiring legacy games to resize their rendering buffers. Aspect-ratio
differences can produce letterboxing. The game must still support the selected
resolution and its own fullscreen behavior inside that display.

The setting applies to Steam **Keep Desktop** launches. **Close Desktop** still
uses ROCKNIX's unchanged native DRM launch path. Gamescope always provides an
isolated display; Off uses the monitor's full resolution, without subtracting
panels or tabs. It does not revert to a fixed 720p resolution.
Changing either setting preserves the other and affects only future launches.

**Apps → Launch with Gamescope → choose an app** uses the same installed
`.desktop` catalog as normal Apps. The Gamescope entry is kept first when Apps
opens with an empty search; typing still filters normally. Other app usage
counts are preserved. The Gamescope picker has its own usage ordering.
Both this entry and Steam games use the installed Adwaita `input-gaming` icon.

Close existing instances before using this path: an application may otherwise
forward the request to its existing process outside Gamescope. This option is
for X11/Wine applications; Wayland-only applications should use normal Apps.
Steam games and shortcuts that already start Gamescope should also use normal
Apps. Launch failures show a menu and write
`~/.local/state/rocknix-desktop/gamescope-app.log` (or `$XDG_STATE_HOME`).
The original desktop entries and Wine/game settings are not rewritten.

LXC programs can also use the same policy from a terminal:

```sh
rocknix-gamescope -- wine /path/to/game.exe
rocknix-gamescope -- rocknix-fex /path/to/wine /path/to/game.exe
rocknix-gamescope --virtual-display off -- /path/to/game
```

Commands and arguments are passed directly, without shell evaluation. This
launcher targets X11/Wine games, uses the guest SDL/Wayland backend, and retains
the shared WSI-disable baseline. Its children select X11 so they cannot bypass
the virtual display by connecting to the outer Wayland compositor. Direct calls
to the upstream `gamescope` binary and applications with their own compositor launch logic
are not intercepted. The guest base includes Debian's Gamescope backport; no
host library tree or additional DRM primary device is exposed for it.

The host and guest packages contain the same sizing helper from one canonical
source. Source regressions cover toggle persistence, legacy settings, content
bounds, scale, stale/invalid geometry, argument preservation, native DRM routing
and Steam restart behavior. The display policy was installed on RP6 at `fd0c7c2`: X11 probe checks covered
fit/native dimensions and keyboard resizing, and the user confirmed PD2
fullscreen works through a Gamescope-wrapped launcher. This does not qualify
all games, physical input or frame times. The later generic Apps picker was applied as a live UI preview without restarting
LXC. RP6 checks verified its pinned entry and icons, real Fuzzel selection into
Gamescope, quoted arguments and working directory, and normal launches remaining
on the outer display. Fullscreen game acceptance remains the user's PD2 test.
Guest launches now use a separate unprivileged systemd service for each
`rocknix-gamescope` invocation. Closing the primary application or losing the
compositor triggers bounded cleanup, including detached Wine children. A shared
native FEX server runs in a separate guest service so closing one game cannot
kill the translator server used by another application. User-manager persistence
is enabled only inside Debian; stopping Desktop powers off the container.

Outcomes are recorded under
`~/.local/state/rocknix-desktop/gamescope-sessions/` (or `$XDG_STATE_HOME`).
Application exit, compositor exit and confirmed service cleanup are distinct:
a forced cleanup after a successful application exit does not produce a false
application-failure popup. A missing manager or shared FEX service fails closed.
Do not treat the absence of a popup as proof that Gamescope itself exited cleanly.
See [Gamescope cleanup](gamescope-teardown.md) for the lifetime boundary and limits.

## Accepted trust tradeoff

Installing games, editing prefixes, adding mods and managing non-Steam games
need access to their files, not inherently host-root privileges. Desktop's
idmapped shared mounts provide that access without changing stored ownership.

However, shared executable content can subsequently be loaded by host-root
Steam, Proton or Gamescope. The fixed-command request bridge is not a security
boundary against software that can modify that content. This is an explicit
compatibility choice matching ROCKNIX's appliance model. A small root helper
that merely validates an app ID and launches root Steam would retain this risk.

Native Gaming Mode does not participate in Desktop's advisory launch lock.
Already-running native Steam is rejected, but an external simultaneous native
launch/replacement of the single scope is not qualified. The scope helper is an
installed script function rather than a documented stable API; firmware changes
still require integration validation.

## Troubleshooting

Check the host game service journal and the guest Gamescope session logs when a
launch fails or leaves a cleanup warning. Steam and Proton can fail when shared
memory is exhausted; investigate live owners before removing files. Desktop does
not delete pre-existing host shared-memory files. Older leaked objects survive
until their original mount is cleared (for example by a reboot). New Desktop
Steam sessions use their own tmpfs; inspecting only the host `/dev/shm` does not
measure a running session. Inspect `/proc/<steam-pid>/root/dev/shm` and the host
game-service journal instead. The existing host available-memory guard still
covers those pages. This does not change native Gaming Mode launches or clean
up FEX processes launched outside the Desktop Steam session.
