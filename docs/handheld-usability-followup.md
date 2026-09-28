# Handheld desktop usability follow-up

Read-only investigation, 2026-09-28. These are proposals, not hardware-validated
features. Preserve the tabbed default, current Art Book styling, Debian app
runtime, and Desktop Mode lifecycle/restoration boundary.

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

## Next bounded implementation

1. Replace layout-local `focus next` with a Desktop-workspace window cycle
   covering tiled and floating leaf windows. Do this before adding exceptions.
2. Identify Firefox PiP on the installed ESR using the actual Sway tree. Record
   `app_id`, `name`, `shell` and IDs for both PiP and ordinary browser windows.
   Keep normal Firefox tabbed. Do not float all Firefox windows or assume an
   English title is a stable unique identity.
3. Preserve native transient-dialog floating behavior. Consider bounded floating
   audio/network settings only when their content fits the usable logical area;
   otherwise retain full-area tabs. A floating app near Waybar is not a popover.
4. Evaluate quick audio/network actions in the existing settings menu, leaving
   advanced settings as explicit app entries.
5. Evaluate Tab/Shift-Tab controller navigation and visible controller help.
   West/North currently type `f`/`r`, which can unexpectedly edit focused fields.

Sway has separate floating/tiling focus operations, and its native Wayland
implementation already considers parented/fixed-size windows for floating.
`window_role`/`window_type` are X11-specific; Firefox runs natively on Wayland.
Mozilla's internal PiP window type is not proof of a Sway-visible role, and its
title is localized.

Sources: [Sway commands](https://raw.githubusercontent.com/swaywm/sway/1.11/sway/sway.5.scd),
[native window handling](https://raw.githubusercontent.com/swaywm/sway/1.11/sway/desktop/xdg_shell.c),
[Mozilla PiP player](https://raw.githubusercontent.com/mozilla-firefox/firefox/main/toolkit/components/pictureinpicture/content/player.xhtml).

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
configuration-only checks. No floating-policy or cross-layer switching change
is approved or implemented by this investigation alone.
