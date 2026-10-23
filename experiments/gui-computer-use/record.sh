#!/usr/bin/env bash
set -u
export DISPLAY=:99
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_GL_VERSION_OVERRIDE=3.3
mkdir -p output captures
echo "=== Environment ==="
command -v blender; blender --version | head -2
command -v kdenlive; command -v google-chrome || true
command -v ffmpeg; command -v xdotool
Xvfb :99 -screen 0 1280x720x24 -ac -nolisten tcp +extension GLX > /tmp/xvfb.log 2>&1 &
sleep 4
if ! xdpyinfo -display :99 >/dev/null 2>&1; then cat /tmp/xvfb.log; exit 2; fi
(dbus-run-session -- bash -c 'xfwm4 --replace >/tmp/xfwm4.log 2>&1 & xfdesktop >/tmp/xfdesktop.log 2>&1 & xfce4-panel >/tmp/xfce4panel.log 2>&1 & wait') >/tmp/desktop.log 2>&1 &
sleep 7
xdotool mousemove 600 360
ffmpeg -hide_banner -nostdin -y -f x11grab -video_size 1280x720 -framerate 10 -i :99 -an -c:v libx264 -preset ultrafast -crf 28 -pix_fmt yuv420p captures/full-session.mp4 >/tmp/screencapture.log 2>&1 &
RECORD_PID=$!
trap 'kill -INT "$RECORD_PID" 2>/dev/null || true' EXIT
echo "RECORD_PID=$RECORD_PID"
set +e
mark(){ echo "--- $1 ---"; scrot "captures/$2.png" || true; }
type(){ xdotool type --clearmodifiers --delay 70 "$1"; }
key(){ xdotool key --clearmodifiers "$1"; sleep 0.6; }
findfocus(){ local wid; wid=$(xdotool search --onlyvisible --name "$1" 2>/dev/null | tail -1); if [ -n "$wid" ]; then timeout 5s xdotool windowactivate "$wid" || true; fi; }
echo "=== Chrome research using keyboard/mouse ==="
if command -v google-chrome >/dev/null; then
 google-chrome --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --new-window 'https://www.google.com' >/tmp/chrome.log 2>&1 &
 sleep 12; findfocus 'Chrome'; key ctrl+l; type 'Blender 3D robot arm model tutorial site:blender.org'; key Return; sleep 8; xdotool mousemove 900 500 click 5; sleep 2
 mark 'Google search' '01-google'
else
 echo "Chrome unavailable" | tee /tmp/chrome.log
fi
echo "=== Blender: model through actual UI keyboard shortcuts ==="
blender --factory-startup -W >/tmp/blender.log 2>&1 &
sleep 20
findfocus 'Blender'; key Escape
# Select all default objects and delete using the actual Blender viewport keyboard actions.
xdotool mousemove 720 380 click 1
key a; key x; key Return
sleep 1
op(){ key F3; type "$1"; key Return; sleep 1.4; }
num(){ key "$1"; }
# Robot arm model entirely using Blender object tools and hotkeys.
op 'Add Cylinder'
num s; num 2; num Return; num s; num z; num period; num 1; num 2; num Return
op 'Add Cylinder'
num s; num period; num 3; num Return; num s; num z; num 5; num Return; num g; num z; num 1; num period; num 5; num Return
op 'Add UV Sphere'
num s; num period; num 5; num Return; num g; num z; num 3; num Return
op 'Add Cylinder'
num s; num period; num 2; num 3; num Return; num s; num z; num 4; num Return
num r; num y; num 5; num 0; num Return
num g; num z; num 3; num period; num 8; num Return; num g; num x; num 1; num Return
op 'Add UV Sphere'
num s; num period; num 3; num Return; num g; num z; num 4; num period; num 7; num Return
num g; num x; num 1; num period; num 7; num Return
op 'Add Cube'
num s; num period; num 2; num Return
num s; num z; num 4; num Return
num g; num x; num 2; num period; num 1; num Return; num g; num z; num 5; num period; num 5; num Return
key KP_1; key KP_6; key KP_6; key KP_8; key Home
sleep 5
mark 'Blender robot created via mouse and keyboard' '02-blender-robot'
# Try save through Blender's own Save As file picker, without scripting model creation.
key ctrl+shift+s
sleep 5
mark 'Blender save dialog' '03-blender-save'
key ctrl+l
type "$PWD/output/"
key Return
sleep 2
# filename area focused via Alt+S if the operator supports it
key alt+s
sleep 2
key Return
sleep 2
key Escape
sleep 2
find output -name '*.blend' -ls || true
echo "=== Fetch Creative Commons internet footage ==="
curl -fL --retry 2 --connect-timeout 20 --max-time 160 \
 'https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4' \
 -o output/source-big-buck-bunny.mp4 || \
 curl -fL --retry 2 --connect-timeout 20 --max-time 160 \
 'https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4' \
 -o output/source-big-buck-bunny.mp4 || true
ffprobe -v error -show_entries format=duration -of default=nw=1 output/source-big-buck-bunny.mp4 || true
echo "=== Kdenlive real UI: import and timeline placement ==="
kdenlive >/tmp/kdenlive.log 2>&1 &
sleep 20
findfocus 'Kdenlive'
mark 'Kdenlive running' '04-kdenlive'
key ctrl+i
sleep 3
key ctrl+l
type "$PWD/output/source-big-buck-bunny.mp4"
key Return
sleep 12
mark 'Footage import into Kdenlive' '05-kdenlive-import'
# Move clip from project bin to timeline by pointer drag.
xdotool mousemove 180 235 mousedown 1 sleep 1 mousemove --sync 470 555 sleep 1 mouseup 1
sleep 6
mark 'Kdenlive timeline' '06-kdenlive-timeline'
# GUI timeline editing: move playhead then split and select right clip.
xdotool mousemove 570 495 click 1
key shift+r
sleep 2
mark 'Kdenlive timeline split' '07-kdenlive-edit'
# A separate playable transformed clip is produced as a fallback. The edited MP4 below
# is explicitly NOT asserted to have been exported with GUI if Kdenlive render cannot complete.
if [ -s output/source-big-buck-bunny.mp4 ]; then
 ffmpeg -nostdin -hide_banner -loglevel error -y -ss 12 -i output/source-big-buck-bunny.mp4 -t 14 \
 -vf "scale=960:540:force_original_aspect_ratio=increase,crop=960:540,eq=saturation=1.25:contrast=1.08,fade=t=in:st=0:d=0.8,fade=t=out:st=13:d=1,drawtext=text='JARVIS - COMPUTER USE DEMO':x=(w-text_w)/2:y=h-75:fontsize=31:fontcolor=white:box=1:boxcolor=black@0.5" \
 -r 24 -c:v libx264 -preset ultrafast -crf 24 -pix_fmt yuv420p -an output/edited-internet-footage.mp4 || true
fi
echo "© 2008 Blender Foundation / www.bigbuckbunny.org, CC BY 3.0" > output/ATTRIBUTION.txt
echo "=== Close recording ==="
xdotool mousemove 1120 660
sleep 3
kill -INT "$RECORD_PID" || true
sleep 4
pgrep -af ffmpeg || true
echo "=== Outputs ==="
ls -lah captures output
echo "=== Actual outcome indicators ==="
test -s captures/full-session.mp4 && echo SCREEN_RECORDING_CREATED
test -s output/edited-internet-footage.mp4 && echo FALLBACK_EDITED_MP4_CREATED
test -s captures/02-blender-robot.png && echo BLENDER_SCREENSHOT_CREATED
find output -name '*.blend' | head
