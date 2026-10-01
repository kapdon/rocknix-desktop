"""Apply the Desktop-only layout to checksum-pinned upstream wvkbd v0.17."""
from pathlib import Path
import re
import sys

source = Path(sys.argv[1])
assets = Path(__file__).parent
layout = source / 'layout.mobintl.h'
text = layout.read_text()
text, count = re.subn(r'static struct key keys_special\[\] = \{.*?\n\};',
                     lambda _: (assets / 'symbols.h').read_text().strip(),
                     text, count=1, flags=re.S)
assert count == 1
# Preserve A's staggered geometry and Compose access, with readable labels.
text = text.replace('"⌨͕", "⌨͔"', '"123", "123"')
text = text.replace('"⇧", "⇫"', '"Shift", "Caps"')
text = text.replace('"⌫", "⌫"', '"Back", "Back"')
text = text.replace('"", "Tab", 3.0, Code, KEY_SPACE',
                    '"Space", "Tab", 3.0, Code, KEY_SPACE')
layout.write_text(text)
config = (source / 'config.def.h').read_text()
config = config.replace('"Sans 14"', '"Roboto 20"').replace('DEFAULT_ROUNDING 5', 'DEFAULT_ROUNDING 0')
config = re.sub(r'(static enum layout_id (?:landscape_)?layers\[\] = \{).*?\};',
                r'\1\n  Simple, Special, NumLayouts\n};', config, flags=re.S)
(source / 'config.h').write_text(config)

# Upstream ignores enter coordinates. With Sway's idle-hidden pointer, the
# first click after re-entering could be dropped until another motion event.
main = source / 'main.c'
text = main.read_text()
text, count = re.subn(
    r'(void\nwl_pointer_enter\([^)]*\)\n\{)\n\}',
    r'\1\n    cur_x = wl_fixed_to_int(surface_x);\n    cur_y = wl_fixed_to_int(surface_y);\n}',
    text, count=1)
assert count == 1
main.write_text(text)
