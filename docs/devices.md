# Device requirements and confirmation

**Retroid Pocket 6 is the only tested device.**
Other models using ROCKNIX's SM8550/QCS8550 platform require an automatic
untested-device confirmation. Versioned and development builds use the same
eligibility and confirmation rules. Other chipsets are currently out of scope. Eligibility is not proof of usable graphics, audio,
touch, controls or recovery on another handheld.

## Eligibility and installation

The installer requires native ROCKNIX, `aarch64`, a valid device-tree model,
and both `HW_DEVICE=SM8550` and `DISTRO_DEVICE=SM8550` in `/etc/os-release`.
The host-owned resolver selects the existing SM8550 profile. Its required
endpoints are fixed:

| Endpoint | Required identity |
| --- | --- |
| `/dev/dri/renderD128` | Root-owned character device, major/minor 226:128 |
| `/dev/video0` | Root-owned character device, major/minor 81:0, name `qcom-iris-decoder` |

The graphics environment selects `msm`/`freedreno`. This is a fixed platform
profile, not dynamic driver/device-number discovery. A missing or different
decoder rejects the profile; there is no missing-decoder software fallback.
Existing optional native FEX remains optional; see [FEX reuse](fex.md).

Exit Desktop and leave EmulationStation running. Read the
[installation/data-replacement rules](../README.md#install-or-update) first.
Use the [public installer command](../README.md#install-or-update). RP6
proceeds normally. For every Install/Update invocation on an eligible non-RP6
model, the installer asks whether to proceed at your own risk before download
or installation changes. The answer defaults to **No**; `--yes` cannot bypass
this warning. Unless `--yes` was supplied, a separate Install/Update confirmation
describes data replacement or preservation.

`--check` checks installer prerequisites only: it does not download the bundle,
check GPU/decoder endpoints or battery, or assess installation health. It does
not prompt and reports when installation will require device confirmation. Normal
Install/Update verifies the downloaded bundle's device check before classifying
or replacing the installation. A bundle without untested-device support
is refused before Desktop data replacement. Resolver failures retain
`device-check.log` in the reported staging path; no Desktop data is replaced
by a profile refusal.
Other preflight/runtime requirements (compositor, input, services, namespaces,
mounts and resources) still apply after confirmation.

## Consent and lifecycle

Installation stores model-bound consent at
`managed/host/state/device.json`, outside guest mounts. The record and ancestors
must be root-controlled; the record is mode 0600 and grants no configurable
mount paths, commands or guest-supplied profile selection.

Installed consent lets the launcher/preflight and internal maintenance tools
recognize the same model. Every public Install/Update invocation on that
non-RP6 model still asks for the device confirmation.
Uninstall checks identity/consent without requiring live GPU/decoder endpoints,
so removal remains possible when those endpoints are unavailable. Uninstall
retains data/tools/consent; replacement Install removes the managed/data trees
and records consent again after device confirmation.

## Reporting a problem

Include the device model, ROCKNIX build, installed Desktop version from
**About Desktop Mode**, and the failed operation or error message. Remove
private network details from logs and screenshots before sharing them.

Other chipsets are unsupported. Widening access to all devices, storage or
sockets is not a compatibility workaround.
