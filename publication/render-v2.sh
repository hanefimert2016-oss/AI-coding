#!/usr/bin/env bash
set -euo pipefail
mkdir -p output
if [ ! -s output/source-big-buck-bunny.mp4 ]; then
 curl -fL --retry 2 --max-time 120 'https://raw.githubusercontent.com/chintan9/Big-Buck-Bunny/master/BigBuckBunny480p30s.mp4' -o output/source-big-buck-bunny.mp4
fi
echo 'Starting cinematic four-shot edit, source from CC BY Big Buck Bunny'
FILTER=$(cat <<'EOF'
[0:v]split=4[one][two][three][four];
[one]trim=start=0:end=7,setpts=PTS-STARTPTS,fps=24,scale=1020:574,crop=960:540,eq=contrast=1.16:saturation=1.30:brightness=-0.02,drawtext=text='JARVIS STUDIO':x=(w-text_w)/2:y=65:fontsize=42:fontcolor=white:box=1:boxcolor=black@0.4,fade=t=in:st=0:d=0.45[a];
[two]trim=start=7:end=14,setpts=PTS-STARTPTS,fps=24,scale=1020:574,crop=960:540,eq=contrast=1.07:saturation=1.10,unsharp=5:5:0.7,drawtext=text='CINEMATIC CUT':x=40:y=h-95:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.45[b];
[three]trim=start=14:end=21,setpts=PTS-STARTPTS,fps=24,scale=1020:574,crop=960:540,eq=contrast=1.21:saturation=0.92:brightness=-.025,drawtext=text='COLOR AND MOTION':x=40:y=h-95:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.45[c];
[four]trim=start=21:end=28,setpts=PTS-STARTPTS,fps=24,scale=1020:574,crop=960:540,eq=contrast=1.14:saturation=1.25,drawtext=text='REIMAGINED BY JARVIS':x=(w-text_w)/2:y=65:fontsize=38:fontcolor=white:box=1:boxcolor=black@0.45[d];
[a][b]xfade=transition=fade:duration=0.7:offset=6.3[ab];
[ab][c]xfade=transition=wipeleft:duration=0.7:offset=12.6[abc];
[abc][d]xfade=transition=circleopen:duration=0.7:offset=18.9,format=yuv420p,fade=t=out:st=25:d=0.8[v]
EOF
)
ffmpeg -hide_banner -nostdin -y -loglevel warning -i output/source-big-buck-bunny.mp4 \
 -filter_complex "$FILTER" -map '[v]' -map 0:a? -af 'volume=0.85,afade=t=in:st=0:d=0.5,afade=t=out:st=25:d=0.8' -t 25.9 \
 -c:v libx264 -preset medium -crf 19 -r 24 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart \
 output/JARVIS-Cinematic-Edit.mp4

echo 'Original Big Buck Bunny: © 2008 Blender Foundation, CC BY 3.0.' > output/ATTRIBUTION.txt
ffprobe -v error -show_entries format=duration,size -of default=nw=1 output/JARVIS-Cinematic-Edit.mp4
