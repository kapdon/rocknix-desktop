#!/bin/bash
# Launch through Apps. Quiet synthetic output-monitor test, never microphone.
set -Eeuo pipefail
exec >"${HOME}/.cache/rocknix-audio-check.log" 2>&1
test "$(id -u)" = 62000
test "${PULSE_SERVER}" = tcp:127.0.0.1:4713
test -z "$(pactl list short sink-inputs)"
sink=$(pactl get-default-sink)
before=$(pactl get-sink-volume "$sink")
test "$(LC_ALL=C pactl get-sink-mute "$sink")" = 'Mute: no'
monitor=$sink.monitor
pactl list short sources | awk '{print $2}' | grep -Fx "$monitor"
work=$(mktemp -d /tmp/rocknix-audio-check.XXXXXX)
record=
cleanup() {
  if [ -n "$record" ]; then kill "$record" 2>/dev/null || true; wait "$record" 2>/dev/null || true; fi
  rm -f -- "$work/tone.raw" "$work/monitor.raw"
  rmdir "$work"
}
trap cleanup EXIT
awk 'BEGIN {for(n=0;n<48000;n++){v=int(6000*sin(2*3.141592653589793*440*n/48000)); if(v<0)v+=65536; printf "%c%c",v%256,int(v/256)}}' >"$work/tone.raw"
test "$(wc -c <"$work/tone.raw")" = 96000
parec --device="$monitor" --raw --format=s16le --rate=48000 --channels=1 --latency-msec=50 >"$work/monitor.raw" &
record=$!
sleep .3
timeout 8 pacat --playback --device="$sink" --raw --format=s16le --rate=48000 --channels=1 --latency-msec=50 --volume=32768 --client-name=ROCKNIX-Synthetic-Audio-Test <"$work/tone.raw"
sleep 1
kill "$record"
wait "$record" || true
record=
nonzero=$(od -An -v -td2 "$work/monitor.raw" | awk '{for(i=1;i<=NF;i++)if($i!=0)n++}END{print n+0}')
printf 'Captured %s monitor bytes, %s nonzero samples\n' "$(wc -c <"$work/monitor.raw")" "$nonzero"
test "$nonzero" -gt 1000
after=$(pactl get-sink-volume "$sink")
test "$before" = "$after"
test "$(LC_ALL=C pactl get-sink-mute "$sink")" = 'Mute: no'
test "$(pactl get-default-sink)" = "$sink"
printf 'PASS: UID %s; output %s; monitor %s; %s nonzero samples; route/volume/mute preserved\n' "$(id -u)" "$sink" "$monitor" "$nonzero"
