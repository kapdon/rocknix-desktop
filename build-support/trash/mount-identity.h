/* SPDX-License-Identifier: MIT
 * Linux-only mount helper. Never equate separate bind mounts by st_dev.
 */
#include <fcntl.h>
#include <sys/stat.h>

static gboolean
rocknix_same_mount (const char *left, const char *right)
{
  struct statx a, b;
  int flags = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT;

  if (statx (AT_FDCWD, left, flags, STATX_MNT_ID, &a) != 0 ||
      statx (AT_FDCWD, right, flags, STATX_MNT_ID, &b) != 0 ||
      !(a.stx_mask & STATX_MNT_ID) || !(b.stx_mask & STATX_MNT_ID))
    return FALSE;

  return a.stx_mnt_id == b.stx_mnt_id;
}
