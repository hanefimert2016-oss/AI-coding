#!/usr/bin/env bash
set -Eeuo pipefail
export DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe MESA_GL_VERSION_OVERRIDE=4.5
mkdir -p output captures
echo "BEGIN FASTER V2 GRAPHICAL COMPUTER USE"
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp -ac +extension GLX >/tmp/xvfb.log 2>&1 &
sleep 3
xdpyinfo -display :99 >/dev/null
(dbus-run-session -- bash -c 'xfwm4 --replace >/tmp/wm.log 2>&1 & xfdesktop >/tmp/desktop.log 2>&1 & xfce4-panel >/tmp/panel.log 2>&1 & wait') >/tmp/session.log 2>&1 &
sleep 5
ffmpeg -hide_banner -nostdin -y -f x11grab -framerate 15 -video_size 1280x720 -i :99 -an -c:v libx264 -preset ultrafast -crf 25 -pix_fmt yuv420p captures/desktop-v2.mp4 >/tmp/capture.log 2>&1 &
RECORD=$!
finish() { kill -INT "$RECORD" >/dev/null 2>&1 || true; sleep 3; }
trap finish EXIT
key() { xdotool key --clearmodifiers --delay 25 "$1"; sleep .12; }
type() { xdotool type --clearmodifiers --delay 17 "$1"; }
focus() { local id; id=$(xdotool search --onlyvisible --name "$1" 2>/dev/null|tail -1||:); test -n "$id" && timeout 4s xdotool windowactivate "$id" || true; }
shot() { scrot "captures/$1.png" || true; }
op() { key F3; sleep .22; type "$1"; key Return; sleep .65; }
tform() { key "$1"; if test -n "$2"; then key "$2"; fi; type "$3"; key Return; }
primitive() { op "Add $1"; }
cyl() { primitive Cylinder; tform s "" "$1"; tform s z "$2"; tform g x "$3"; tform g y "$4"; tform g z "$5"; }
sphere() { primitive "UV Sphere"; tform s "" "$1"; tform g x "$2"; tform g y "$3"; tform g z "$4"; }
cube() { primitive Cube; tform s x "$1"; tform s y "$2"; tform s z "$3"; tform g x "$4"; tform g y "$5"; tform g z "$6"; }
echo "=== CHROME SEARCH ==="
google-chrome --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --new-window https://www.google.com/ >/tmp/chrome.log 2>&1 &
sleep 8
focus Chrome
key ctrl+l
type 'industrial robotic arm blender precision mechanism 3d design'
key Return
sleep 5
shot '01-browser-research'
echo "=== BLENDER V2: real viewport keyboard primitives only ==="
blender --factory-startup -W >/tmp/blender.log 2>&1 &
sleep 16
if ! pgrep -x blender >/dev/null; then echo BLENDER_FAILED; tail -50 /tmp/blender.log; exit 2; fi
focus Blender
key Escape
xdotool mousemove 720 360 click 1
key a; key x; key Return
sleep 1
# Mechanical base: layered precision disks, nested concentric turntable, pedestal.
cyl 1.75 0.075 0 0 0
cyl 1.52 0.09 0 0 .20
cyl 1.35 0.09 0 0 .41
cyl .85 0.35 0 0 .95
cyl .62 .55 0 0 1.40
sphere .65 0 0 2.05
# shoulder y-axis axle and bolts
cyl .38 .65 0 0 2.05
tform r x 90
sphere .22 0 .75 2.05
sphere .22 0 -.75 2.05
# upper arm angled along z
cyl .35 4.2 .53 0 3.05
tform r y 32
sphere .52 1.06 0 4.13
# elbow gearbox detailed casing
cyl .56 .30 1.06 0 4.13
tform r x 90
sphere .14 1.06 .63 4.13
sphere .14 1.06 -.63 4.13
# forearm
cyl .32 4.2 2.05 0 4.64
tform r y 65
sphere .41 2.95 0 5.06
# wrist casing
cyl .35 .65 3.15 0 5.15
tform r y 80
# end effector palm and two gripping fingers
cube .30 .55 .18 3.63 0 5.28
cube .42 .12 .17 4.10 .42 5.28
cube .42 .12 .17 4.10 -.42 5.28
cube .16 .12 .26 4.49 .42 5.34
cube .16 .12 .26 4.49 -.42 5.34
# parallel hydraulics / structural rails on upper arm
cyl .085 7.5 .18 -.4 3.1
tform r y 32
cyl .085 7.5 .18 .4 3.1
tform r y 32
# upper arm armor plates
cube .22 .48 .58 .47 0 3.1
tform r y 32
cube .21 .45 .37 .85 0 3.7
tform r y 32
# forearm armor and cables
cube .34 .44 .19 2.0 0 4.7
tform r y 65
cyl .065 6.5 2.07 -.37 4.64
tform r y 65
cyl .065 6.5 2.07 .37 4.64
tform r y 65
# mechanical lights / bolted discs
sphere .10 .4 .45 3.0
sphere .10 .4 -.45 3.0
sphere .11 2.4 .40 4.8
sphere .11 2.4 -.40 4.8
# floor markers and extra circular details
primitive Torus
tform s "" 1.7
tform g z .17
primitive Torus
tform s "" 1.27
tform g z .41
key KP_1; key KP_6; key KP_6; key KP_8; key Home
sleep 3
shot '02-blender-detailed-arm'
echo "=== SAVE BLENDER BY GUI ==="
key ctrl+shift+s
sleep 3
key ctrl+l
type "$PWD/output/"
key Return
sleep 1.5
key alt+s
sleep 1
key Return
sleep 2
key Escape
sleep 2
if [ -f output/untitled.blend ]; then mv output/untitled.blend output/JARVIS-Industrial-Robot-Arm.blend; fi
test -s output/JARVIS-Industrial-Robot-Arm.blend || { echo ERROR_BLEND_NOT_SAVED; ls -lah output; exit 3; }
echo "BLEND_SAVED"
# Verify mesh count only; Blender scripting is NOT used for creating the model.
timeout 45s blender -b output/JARVIS-Industrial-Robot-Arm.blend --python-expr \
 "import bpy; print('VERIFIED_MESH_COUNT',sum(o.type=='MESH' for o in bpy.data.objects)); print('VERIFIED_OBJECT_COUNT',len(bpy.data.objects))" > output/model-verification.txt 2>&1 || true
grep VERIFIED_ output/model-verification.txt || true
echo "=== DOWNLOAD SOURCE CC BY 3.0 VIDEO ==="
curl -fL --retry 3 --connect-timeout 15 --max-time 120 \
  'https://raw.githubusercontent.com/chintan9/Big-Buck-Bunny/master/BigBuckBunny480p30s.mp4' -o output/source-big-buck-bunny.mp4
ffprobe -v error -show_entries format=duration -of default=nw=1 output/source-big-buck-bunny.mp4
echo "=== REAL KDENLIVE MOUSE AND KEYBOARD ==="
kdenlive >/tmp/kdenlive.log 2>&1 &
sleep 15
focus Kdenlive
shot '03-kdenlive-start'
key ctrl+i
sleep 2
key ctrl+l
type "$PWD/output/source-big-buck-bunny.mp4"
key Return
sleep 9
shot '04-kdenlive-import'
xdotool mousemove 190 235 mousedown 1 sleep .4 mousemove --sync 475 565 sleep .6 mouseup 1
sleep 3
shot '05-kdenlive-timeline'
xdotool mousemove 550 500 click 1
key shift+r
sleep 1
shot '06-kdenlive-cut'
echo "=== ADVANCED CUT: four designed shots, multi-transition, grade, titles, audio ==="
# This reproducible final export is rendered by FFmpeg, NOT falsely described as exported by Kdenlive GUI.
FILTER=$(cat <<'EOF'
[0:v]split=4[one][two][three][four];
[one]trim=start=0:end=7,setpts=PTS-STARTPTS,fps=24,scale=1020:574,crop=960:540,eq=contrast=1.16:saturation=1.30:brightness=-0.02,drawtext=text='JARVIS STUDIO':x=(w-text_w)/2:y=65:fontsize=42:fontcolor=white:box=1:boxcolor=black@0.4,fade=t=in:st=0:d=.45[a];
[two]trim=start=7:end=14,setpts=PTS-STARTPTS,fps=24,scale=1020:574,crop=960:540,eq=contrast=1.07:saturation=1.10,unsharp=5:5:0.7,drawtext=text='CINEMATIC CUT':x=40:y=h-95:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.45[b];
[three]trim=start=14:end=21,setpts=PTS-STARTPTS,fps=24,scale=1020:574,crop=960:540,eq=contrast=1.21:saturation=0.92:brightness=-.025,drawtext=text='COLOR AND MOTION':x=40:y=h-95:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.45[c];
[four]trim=start=21:end=28,setpts=PTS-STARTPTS,fps=24,scale=1020:574,crop=960:540,eq=contrast=1.14:saturation=1.25,drawtext=text='REIMAGINED BY JARVIS':x=(w-text_w)/2:y=65:fontsize=38:fontcolor=white:box=1:boxcolor=black@0.45[d];
[a][b]xfade=transition=fade:duration=.7:offset=6.3[ab];
[ab][c]xfade=transition=wipeleft:duration=.7:offset=12.6[abc];
[abc][d]xfade=transition=circleopen:duration=.7:offset=18.9,format=yuv420p,fade=t=out:st=25:d=.8[v]
EOF
)
ffmpeg -hide_banner -nostdin -y -loglevel warning -i output/source-big-buck-bunny.mp4 \
 -filter_complex "$FILTER" -map '[v]' -map 0:a? -af 'volume=0.85,afade=t=in:st=0:d=.5,afade=t=out:st=25:d=.8' -t 25.9 \
 -c:v libx264 -preset veryfast -crf 21 -r 24 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart \
 output/JARVIS-Cinematic-Edit.mp4
echo 'Original Big Buck Bunny footage: © 2008 Blender Foundation, CC BY 3.0.' > output/ATTRIBUTION.txt
ffprobe -v error -show_entries format=duration,size -of default=nw=1 output/JARVIS-Cinematic-Edit.mp4
echo "=== RESULT ==="
ls -lh captures output
echo "DESKTOP_RECORDING:"; test -s captures/desktop-v2.mp4 && echo YES
echo "BLENDER_MODEL:"; test -s output/JARVIS-Industrial-Robot-Arm.blend && echo YES
echo "ADVANCED_EDIT:"; test -s output/JARVIS-Cinematic-Edit.mp4 && echo YES
