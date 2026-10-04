#!/usr/bin/env python3
"""Compile actual Fuzzel input callbacks against deterministic Wayland stubs.

Run against the patched pinned source directory; no compositor/device claim.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

source = Path(sys.argv[1])

def function(file, name):
    text = (source / file).read_text()
    start = re.search(r'(?:static )?(?:void|bool|ssize_t)\n' + name + r'\(', text).start()
    end = text.index('\n}', start) + 2
    return text[start:end]

stubs = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <sys/types.h>
#include <math.h>
#include <linux/input-event-codes.h>
typedef int32_t wl_fixed_t;
struct wl_pointer {}; struct wl_touch {}; struct wl_surface {};
struct matches { size_t selected; size_t count; };
struct render { int row_height; int first; int pad; };
struct wayland { bool enable_mouse; float scale; int width; struct render *render; struct matches *matches; int status; int exit_code; struct { struct {bool enabled;} dmenu;} *conf; };
struct seat { struct wayland *wayl; struct {int x,y; uint32_t serial; bool has_motion;} pointer;
struct {uint32_t serial; struct {int id; double start_x,start_y,current_x,current_y,last_y,accumulated_scroll; bool scrolling,is_tap; uint32_t start_time;} active_touch;} touch; };
#define WL_POINTER_BUTTON_STATE_RELEASED 0
#define EXIT 1
static int executed = -1;
static double wl_fixed_to_double(int x) {return x/256.0;}
static int wl_fixed_to_int(int x) {return x/256;}
static int row_bg_x(const struct render *r) {return r->pad;}
static int first_row_y(const struct render *r) {return r->first;}
static size_t matches_get_count(const struct matches *m) {return m->count;}
static size_t match_get_idx(const struct matches *m, size_t i) {return i;}
static bool attempt_cursor_shape(struct wayland *w, struct wl_pointer *p, uint32_t s) {return true;}
static void reload_cursor_theme(struct seat *s,float f) {}
static void update_cursor_surface(struct seat *s) {}
static void select_hovered_match(struct seat *s,bool b) {}
static void execute_selected(struct seat *s,bool b,int i) {executed=s->wayl->matches->selected;}
static void paste_from_primary(struct seat *s) {}
"""
callbacks = [('render.c', 'render_get_row_num'), ('match.c', 'matches_idx_select'),
             ('wayland.c', 'wl_pointer_enter'), ('wayland.c', 'wl_pointer_motion'),
             ('wayland.c', 'wl_pointer_button'), ('wayland.c', 'wl_touch_down'),
             ('wayland.c', 'wl_touch_up')]
main = r"""
int main(void) {
    for (int k=2;k<=4;k++) {
        float scale=k/2.0;
        struct render render={.row_height=48*scale,.first=56*scale,.pad=10*scale};
        struct matches matches={.count=8};
        struct wayland wayl={.enable_mouse=true,.scale=scale,.width=800*scale,.render=&render,.matches=&matches};
        struct seat seat={.wayl=&wayl};
        // Previously hovered row one, then leave/re-enter over row five.
        seat.pointer.x=100*scale; seat.pointer.y=80*scale;
        wl_pointer_enter(&seat,0,1,0,100*256,272*256);
        assert(matches.selected==0); // entry must not disturb keyboard selection
        wl_pointer_button(&seat,0,2,10,BTN_LEFT,WL_POINTER_BUTTON_STATE_RELEASED);
        assert(executed==4); // no motion is needed before the click
        matches.selected=0; executed=-1;
        wl_touch_down(&seat,0,3,100,0,7,100*256,272*256);
        wl_touch_up(&seat,0,4,200,7);
        assert(executed==4);
        matches.selected=0; executed=-1;
        wl_pointer_motion(&seat,0,210,100*256,176*256);
        wl_pointer_button(&seat,0,5,220,BTN_LEFT,WL_POINTER_BUTTON_STATE_RELEASED);
        assert(executed==2);
        executed=-1;
        wl_pointer_enter(&seat,0,6,0,100*256,10*256);
        wl_pointer_button(&seat,0,7,230,BTN_LEFT,WL_POINTER_BUTTON_STATE_RELEASED);
        assert(executed==-1); // prompt/background must not activate stale selection
    }
}
"""
with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)
    (path/'test.c').write_text(stubs+'\n'.join(function(*args) for args in callbacks)+main)
    subprocess.run(['cc','-std=gnu11',str(path/'test.c'),'-lm','-o',str(path/'test')],check=True)
    subprocess.run([str(path/'test')],check=True)
print('PASS: actual Fuzzel callbacks select clicked/tapped rows at 1, 1.5 and 2 scales')
