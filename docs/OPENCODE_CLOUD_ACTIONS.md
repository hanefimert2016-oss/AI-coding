# OpenCode v2 Cloud — GitHub Actions (official web UI)

The host is the **public AI-coding repository**, not FalconOS and not a private Metodbox repo. Only a manually-dispatched Actions job runs the server. The UI is built into **official OpenCode v2**; OpenTunnel is its official remote-access channel.

## First-time setup (Android browser)

1. In this repo, go to **Settings → Secrets and variables → Actions → New repository secret**.
2. Add the secret named `OPENCODE_PASSWORD` with a **unique, random password of 20+ characters**. **Never** enter this as a workflow input or share it in an issue, commit, Actions log, or chat.
3. Go to **Actions → OpenCode Cloud - Official Web UI → Run workflow**, choose **main** and a 30–120-minute session.
4. Open the new Actions job and its **Summary**. The **remote base URL** (not a token-bearing pairing link) is printed there. Open it on your phone and authenticate with your secret as prompted. Username for HTTP basic authentication is `opencode`.
5. OpenCode is running in its own environment on the dedicated `opencode-cloud-workspace-20261109` branch. To keep code changes, ask OpenCode to `git status`, `git add`, `git commit`, and `git push origin HEAD:opencode-cloud-workspace-20261109` **before the workflow run ends**.
6. To end early, cancel the workflow. The run also ends automatically after the selected duration. Starting a new run creates a **new remote URL**.

### If the remote base URL asks you to pair again

OpenCode's one-use `/auth/connect/...` link grants a session and must not be printed in **public** workflow logs. If the base URL cannot authenticate with the password, this setup **will not bypass the pairing security**. Use OpenCode's official private pairing mechanism instead; the workflow will need a private way to deliver the one-use link. Do not make the link public.

## Caveats and security

- GitHub Actions is for development workflows, not a guaranteed persistent host. Standard public GitHub-hosted runners have unlimited free minutes, but an individual job has a time limit and GitHub's acceptable-use rules still apply.
- **The repository and the dedicated branch are PUBLIC.** Do not process private source code or store `.env` files, tokens, passwords, personal data, or API keys there.
- The workflow uses `contents: write` for committing to the dedicated branch. It never auto-commits to protect against inadvertent publishing of secrets. Work not committed before the run ends will be lost.
- Password stays in GitHub Actions Secrets, never in workflow inputs; public logs only display the sanitized remote address. Password is stored in the ephemeral OpenCode server configuration inside the Actions runner.
- OpenCode server listens on localhost; the built-in OpenTunnel mechanism provides encrypted remote access. No Cloudflare Quick Tunnel (which cannot transport Server-Sent Events) is required.
- OpenCode can connect to free or paid AI providers; a free web UI does **not** guarantee a free AI model or unlimited inference.

Official references: https://opencode.ai/docs/cli/web/ · https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
