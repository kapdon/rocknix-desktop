# Handheld desktop usability follow-up

Investigation and implementation notes, 2026-09-28. Preserve the tabbed default,
current Art Book styling, Debian runtime, and Desktop lifecycle/restoration.

## Close-window decision

The user selected direct R3 close, without a desktop confirmation. The helper
must resolve exactly one focused leaf view in `98:Desktop`, then request a
normal close using its numeric container ID. Empty workspace, parent-container
focus, foreign workspace, invalid tree and failed IPC query must be no-ops.
Suppress key repeat. East/Start remain Escape. The application owns any
save/discard dialog; Firefox currently disables its multi-tab close warning.

Do not replace this with bare Sway `kill` or `con_id=__focused__` criteria:
Sway 1.11 treats focused parents and missing focus differently from a single
leaf view. See [Sway criteria implementation](https://raw.githubusercontent.com/swaywm/sway/1.11/sway/criteria.c).

Local regression tests are not proof of physical R3 behavior. The device still
needs a new build/install and guided acceptance after this change.

## Implemented adaptive window policy

`rocknix-window-policy` replaces the existing one-second window-count poll. It
uses numeric leaf IDs only inside `98:Desktop`, including Sway's `floating_con`
type. PiP uses 42% of available width, limited to 45% of available height, with
its initial aspect ratio preserved. Its bottom/right inset is a quarter of the
measured bar height. Workspace geometry excludes panel/keyboard reserved areas.

Only the observed main utility titles (`Volume Control` and `Network
Connections`) qualify; same-app editors/confirmation dialogs stay unmanaged.
Audio/network settings use their initial client size or a 720x480 baseline
scaled by bar height, whichever is larger. They float centered only if that
size fits with insets; otherwise they use the tabbed workspace. Re-evaluation
occurs on workspace bounds changes, not every focus change, so the defaults do
not continuously fight manual dragging. Fullscreen windows are left alone.

The cycle helper visits tiled and floating leaves by stable container ID and
wraps. It does nothing with no unique focused app (e.g. a layer-shell launcher).
The R3 helper now handles `floating_con` too. All helpers remain session-owned;
no persistent Sway config is written and cleanup still stops the existing poll.

RP6 Sway 1.11 / Firefox 140.16.0esr observations before packaging:

- Actual PiP: `app_id=firefox-esr`, `name=Picture-in-Picture`.
- Normal Firefox title includes the page title and Mozilla Firefox suffix.
- Audio: `org.pulseaudio.pavucontrol`; network: `nm-connection-editor`.
- Injected IPC cycle reached Files, Firefox, audio and PiP, then wrapped.
- At 1920x1000 usable area PiP was 768x432 at 1132,548.
- With keyboard, usable height was 622; PiP became 464x261 at 1436,341,
  and both settings apps became tabbed. Hidden keyboard restored floating.

These are rendered-device/IPC checks, not physical controller acceptance.
Fixtures cover narrow bounds, malicious IDs, nonmatching titles, fullscreen,
empty/foreign workspaces, repeat ticks, keyboard changes and cross-layer cycling.

## Remaining follow-up

1. Revalidate PiP identity after Firefox updates or localization changes. The
   compatibility match requires an exact English title plus Firefox app ID;
   it is not a universal localized PiP detector. Unknown titles stay unchanged.
2. Evaluate quick audio/network actions in the existing settings menu, leaving
   advanced settings as explicit app entries.
3. Validate the separately implemented West/North field navigation on hardware;
   see [controller field navigation](controller-field-navigation.md). Visible
   controller help remains a follow-up.

Sway has separate floating/tiling focus operations, and its native Wayland
implementation already considers parented/fixed-size windows for floating.
`window_role`/`window_type` are X11-specific; Firefox runs natively on Wayland.
Mozilla's internal PiP window type is not proof of a Sway-visible role, and its
title is localized.

Sources: [Sway commands](https://raw.githubusercontent.com/swaywm/sway/1.11/sway/sway.5.scd),
[native window handling](https://raw.githubusercontent.com/swaywm/sway/1.11/sway/desktop/xdg_shell.c),
[Mozilla PiP player](https://raw.githubusercontent.com/mozilla-firefox/firefox/main/toolkit/components/pictureinpicture/content/player.xhtml).

The general utility-floating pattern was compared with
[Sway-DE's own configuration](https://github.com/madic-creates/Sway-DE/blob/master/config/sway/sway.d/06_floating.conf),
but its broad title rules and hardcoded coordinates were not copied.
[Mozilla tracks the native PiP identification limitation](https://bugzilla.mozilla.org/show_bug.cgi?id=1958013).
The launcher comparison is discarded at the user's request. Fuzzel remains;
its current large sizing is accepted for now, not a claim of universal fit.

## Physical acceptance matrix

- Open Files, Firefox, PiP and audio settings; reach every window and return.
- Close PiP without closing Firefox; close settings without leaving Desktop.
- Hold R3: only one close request. Close the last app: panel remains usable.
- Test R3 with Apps/Return confirmation open, empty workspace and parent focus.
- Test an app's unsaved-change dialog without bypassing its save/discard choice.
- Show/hide keyboard with floating dialogs: all fields/buttons remain reachable.
- Check narrow logical resolutions, long titles and PiP controls near the panel.
- Return to Gaming: restore host configuration and input bindings.

Distinguish actual finger/controller tests from injected pointer events and
configuration-only checks. Guided approval of the installed build still gates
the merge into dev; controller field navigation remains a separate task.
