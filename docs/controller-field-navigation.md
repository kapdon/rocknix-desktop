# Controller field navigation

Implemented Desktop Mode mapping, 2026-09-28. The original investigation was
based on `e7801dae6d41b822db4a72ba61708a12aabf6a87`.
Only the desktop input profile changes at runtime. No new host binding, helper,
service, launcher styling or restoration path is introduced.

| Physical control | Desktop action |
| --- | --- |
| West / left face | Next field: Tab |
| North / top face | Previous field: Shift+Tab |
| South / bottom face | Enter / confirm |
| East / right face; Start | Escape / back |
| D-pad | Arrow keys; launcher selection |
| Select | Cycle apps, including tiled and floating windows |
| L3 | Toggle keyboard |
| R3 | Normal close of focused window; no repeat |
| Right stick | Pointer |
| Left / right trigger | Left / right mouse click |
| Right / left bumper | Scroll up / down |
| Left stick | W/A/S/D (unchanged) |
| Guide / Quick Access | Existing InputPlumber UI events |

## Decision and limits

Impeccable's Operate/input-adaptation principles favor reachable, direct
controls that preserve established actions. West and North previously sent plain
`f` and `r`, rather than actual Find/Refresh shortcuts. Replacing those accidental
text-entry actions leaves scroll, clicks, launcher confirm/back and app controls
intact. Physical positions avoid dependence on printed Nintendo/Xbox labels.

North uses InputPlumber's ordered target list: Left Shift, then Tab. Upstream
[translation and chord handling at ea60d873](https://github.com/ShadowBlip/InputPlumber/blob/ea60d873cca17edd1cb655ede26f557108135252/src/input/composite_device/mod.rs)
keeps press order and reverses release order, with staggered chord events.
This was source inspection, not verification of the installed RP6 version.

Tap and release for individual steps. Holding North holds Shift too: it can
modify simultaneous clicks/keys. Avoid overlapping North and West; they share
the virtual Tab key. Rapid alternating taps and release timing require physical
validation. Focus follows the app's tab order, including buttons and links;
Tab may insert indentation in editors/terminals. Use D-pad and bottom/right
buttons in Apps; Tab's launcher behavior is not a field-navigation guarantee.
Left-stick W/A/S/D text input is unchanged and outside this change's scope.

## Verification

Run `python3 tests/controller-fields.py` and `bash tests/check.sh`. The focused
contract test checks both field actions, modifier ordering, unique source
buttons, and every preserved controller action without a new CI dependency.
It does not emulate InputPlumber, Wayland focus, or key release on hardware.
The existing suite checks lifecycle, return confirmation, launcher, normal close,
window policy and app cycling. No device access is needed for these tests.

For changes to this mapping, build/install the candidate and repeat these
physical checks:

1. In network settings, move forward/back across editable fields and buttons.
   Verify West then North returns to the prior focus without inserting `f`/`r`.
2. In Firefox, traverse inputs, links and buttons; check visible focus. In Files,
   check location entry and a dialog. Repeat with L3 keyboard shown/hidden.
3. Tap North briefly, hold it, release it, then type lowercase with the keyboard
   and click text: no stuck Shift, unwanted selection, or continued navigation.
   Repeat rapid taps and alternating West/North; record missed/reversed steps.
4. Verify triggers still click and bumpers still scroll. In Apps, confirm and
   dismiss with bottom/right buttons after using both field-navigation buttons.
5. Verify Select reaches tiled apps, settings and PiP; R3 closes only the focused
   window, does not repeat when held, and respects application save dialogs.
6. Return to Gaming and re-enter Desktop; confirm prior profile/targets restore
   and neither Tab nor Shift remains held. Include exit while North is held.

Local results: the full `bash tests/check.sh` suite passed, including the new
controller contract. Both changed mappings validate against the upstream schema
at `ea60d873`. Full-profile schema validation reports two pre-existing bumper
`mouse.wheel` mismatches, identical on the base and this candidate. Those scroll
mappings are intentionally preserved for the coordinator's physical check.
`git diff --check` passed. No bundle was built or installed by this task.

After integration, the user confirmed that West and North work as intended on
the RP6. This confirms the basic mappings, not every stress/held-key case listed
above. Launcher comparison remains discarded; Fuzzel sizing, floating policy
and theme were outside that input change's scope.
