#!/usr/bin/env bash
set -uo pipefail
mkdir -p unity-output
export DISPLAY=:98 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe MESA_GL_VERSION_OVERRIDE=4.5
echo "=== DISK / SYSTEM ==="
df -h /
echo "=== OFFICIAL UNITY HUB ==="
sudo install -d /etc/apt/keyrings
if curl -fsSL --max-time 25 https://hub.unity3d.com/linux/keys/public | sudo gpg --dearmor -o /etc/apt/keyrings/unityhub.gpg; then
 echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/unityhub.gpg] https://hub.unity3d.com/linux/repos/deb stable main' | sudo tee /etc/apt/sources.list.d/unityhub.list
 sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y unityhub || true
fi
Xvfb :98 -screen 0 1280x720x24 -ac -nolisten tcp +extension GLX >/tmp/xvfb.log 2>&1 &
sleep 3
(openbox --replace >/tmp/wm.log 2>&1) &
sleep 2
if command -v unityhub >/dev/null; then
 echo UNITY_HUB_INSTALLED
 timeout 8s unityhub --version >unity-output/hub-version.txt 2>&1 || true
 unityhub --no-sandbox >/tmp/hub.log 2>&1 &
 sleep 15
 scrot unity-output/01-unity-hub.png || true
 xdotool search --onlyvisible --name Unity | xargs -r -n1 -I{} xdotool getwindowname {} || true
else
 echo UNITY_HUB_NOT_AVAILABLE
fi
echo "=== OFFICIAL UNITY EDITOR 6000.3.24f1 FILE CHECK ==="
URL="https://download.unity3d.com/download_unity/4e7b9b5b6244/LinuxEditorInstaller/Unity-6000.3.24f1.tar.xz"
curl -fL --retry 1 --connect-timeout 20 --max-time 75 -I "$URL" >unity-output/editor-download-head.txt 2>&1
HAS_INSTALLER=$?
cat unity-output/editor-download-head.txt | grep -Ei 'HTTP/|content-length|content-type|location' | tail -14 || true
if [ "$HAS_INSTALLER" -ne 0 ]; then echo UNITY_EDITOR_INSTALLER_NOT_REACHABLE; exit 0; fi
echo "=== ATTEMPT STREAMED EDITOR INSTALL ==="
sudo rm -rf /usr/local/lib/android /usr/share/dotnet /opt/hostedtoolcache/CodeQL /usr/local/share/powershell || true
df -h /
sudo mkdir -p /opt/unity-editor
# Stream the publisher's archive without storing a second 4GB copy.
set -o pipefail
timeout 660s bash -c 'curl -fL --retry 2 --connect-timeout 30 --max-time 635 "$1" | sudo tar -xJ -C /opt/unity-editor' _ "$URL"
STATUS=$?
echo "STREAM_EXTRACT_STATUS=$STATUS"
df -h /
EDITOR=$(find /opt/unity-editor -type f -name Unity -perm -111 -print -quit 2>/dev/null)
echo "UNITY_EDITOR_BINARY=$EDITOR"
if [ -z "$EDITOR" ]; then echo UNITY_EDITOR_NOT_INSTALLED; exit 0; fi
timeout 25s "$EDITOR" -version >unity-output/unity-version.txt 2>&1 || true
cat unity-output/unity-version.txt | tail -30
echo "=== UNITY EDITOR GUI LAUNCH ==="
mkdir -p unity-project/Assets unity-project/Packages unity-project/ProjectSettings
cat >unity-project/ProjectSettings/ProjectVersion.txt <<'EOF'
m_EditorVersion: 6000.3.24f1
m_EditorVersionWithRevision: 6000.3.24f1 (4e7b9b5b6244)
EOF
cat >unity-project/Packages/manifest.json <<'EOF'
{
 "dependencies": {
  "com.unity.collab-proxy": "2.5.2",
  "com.coplaydev.unity-mcp": "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main"
 }
}
EOF
timeout 80s "$EDITOR" -projectPath "$PWD/unity-project" -logFile "$PWD/unity-output/editor.log" >/tmp/unity-stdout.log 2>&1 &
UNPID=$!
sleep 27
scrot unity-output/02-unity-editor.png || true
xdotool search --onlyvisible --name Unity | xargs -r -n1 -I{} xdotool getwindowname {} || true
echo "=== LICENSE STATE / RESULTS ==="
grep -iE 'license|activation|project|package|error' unity-output/editor.log 2>/dev/null|tail -40 || true
ps -ef|grep -E 'Unity$|Unity -projectPath'|grep -v grep || true
wait "$UNPID" || true
echo "UNITY_EDITOR_ATTEMPTED"
