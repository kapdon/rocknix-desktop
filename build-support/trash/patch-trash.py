#!/usr/bin/env python3
"""Patch isolated GLib/GVfs source trees, never installed libraries.

The Debian quilt package build records these transformations while preserving
Debian security patches and update semantics. Exact-match edits reject changed
upstream sources.
"""
from pathlib import Path
import sys


def replace(text, old, new):
    assert text.count(old) == 1, repr(old)
    return text.replace(old, new)


def opt_in(text):
    start = text.index('static gboolean\nignore_trash_mount (')
    end = text.index('\n}', start) + 2
    # Do not retain pointers into freed GUnixMountPoint storage. Explicit live
    # options win; fstab is consulted only for otherwise ignored internal mounts.
    replacement = '''static gboolean
rocknix_has_mount_option (const char *options, const char *wanted)
{
  char **tokens = g_strsplit (options, ",", -1);
  gboolean found = g_strv_contains ((const char *const *) tokens, wanted);
  g_strfreev (tokens);
  return found;
}

static gboolean
ignore_trash_mount (GUnixMountEntry *mount)
{
  const char *options = g_unix_mount_entry_get_options (mount);
  gboolean internal = g_unix_mount_entry_is_system_internal (mount);
  GUnixMountPoint *point;
  gboolean ignored;

  if (options != NULL)
    {
      if (rocknix_has_mount_option (options, "x-gvfs-notrash"))
        return TRUE;
      if (rocknix_has_mount_option (options, "x-gvfs-trash"))
        return FALSE;
    }

  if (!internal && options != NULL)
    return FALSE;

  point = g_unix_mount_point_at (g_unix_mount_entry_get_mount_path (mount), NULL);
  if (point == NULL)
    return internal;
  options = g_unix_mount_point_get_options (point);
  ignored = internal;
  if (options != NULL)
    {
      if (rocknix_has_mount_option (options, "x-gvfs-notrash"))
        ignored = TRUE;
      else if (rocknix_has_mount_option (options, "x-gvfs-trash"))
        ignored = FALSE;
    }
  g_unix_mount_point_free (point);
  return ignored;
}'''
    return text[:start] + replacement + text[end:]


def main():
    tree = Path(sys.argv[2])
    if sys.argv[1] == 'glib':
        path = tree / 'gio/glocalfile.c'
        text = path.read_text()
        text = replace(text, '#include "glib-private.h"',
                       '#include "glib-private.h"\n' +
                       Path(__file__).with_name('mount-identity.h').read_text())
        text = replace(text, 'if (parent_dev != dir_dev)',
                       'if (parent_dev != dir_dev || !rocknix_same_mount (dir, parent))')
        text = replace(text, 'else if (dir_dev == home_dev)',
                       'else if (dir_dev == home_dev &&\n'
                       '           rocknix_same_mount (dirname, g_get_home_dir ()))')
        text = replace(text, 'if (file_stat.st_dev == home_stat.st_dev)',
                       'if (file_stat.st_dev == home_stat.st_dev &&\n'
                       '      rocknix_same_mount (local->filename, homedir))')
    elif sys.argv[1] == 'gvfs':
        path = tree / 'daemon/trashlib/trashwatcher.c'
        text = path.read_text()
    else:
        raise SystemExit('expected glib or gvfs and source directory')
    path.write_text(opt_in(text))


if __name__ == '__main__':
    main()
