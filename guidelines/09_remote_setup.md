# 09 — Working from another laptop on the remote machine

Written 2026-11-05 for the user. Situation: the stronger machine can only be reached from a second laptop. Plan:
VS Code on that laptop, connected by SSH to the machine, with Claude Code working **on the machine** (where the code,
data and runs live). Machine details (cluster or server, scheduler) are still unknown; steps marked ⟳ depend on them.

## The idea in one picture
```
second laptop (VS Code window only)  ──SSH──►  remote machine
                                                ├─ project folder (git clone)
                                                ├─ .venv, data/ (downloaded there), runs
                                                └─ Claude Code runs here, with your Claude login
```
The laptop holds nothing important; everything is on the machine and in a private GitHub repository.

## Step 1 — on THIS laptop, before you switch (Claude can do it with your OK)
1. **Put the project in a private GitHub repository.** Nothing is committed yet. The tracked part is small
   (~17 MB: code, guidelines, reports, results figures); `data/`, `.venv/`, `model/runs/` and credentials are excluded
   by `.gitignore`. Commands (Claude runs them on request):
   ```bash
   git checkout -b main          # the repository is on 'master' with no commits yet
   git add -A && git commit -m "Green Patch 2026: state on 2026-11-05"
   # the GitHub CLI (gh) is not installed here: (done 2026-11-05: private repository yairsuari/greenpatch, first commit pushed)
   # (no README), then:
   git remote add origin https://github.com/yairsuari/greenpatch.git
   git push -u origin main       # a browser window asks you to sign in to GitHub the first time
   ```
2. **Data does not travel.** Raw satellite and model files are re-downloaded on the machine from Copernicus Marine
   (faster there, and `data/raw` is reproducible). Exception, if wanted: `data/raw/model/` (~50 MB, Q2) can be copied.
3. **Claude's memory does not travel with the folder.** What it needs is in the project: `CLAUDE.md` and
   `guidelines/handoff.md` (read first in every session). Copy your personal `C:\Users\Yair\.claude\CLAUDE.md`
   (the venv rules) to the machine as `~/.claude/CLAUDE.md`.

## Step 2 — on the second laptop
1. Install **VS Code** and **Git**.
2. In VS Code install the extensions **Remote - SSH** (Microsoft) and **Claude Code** (Anthropic).
3. Create an SSH key (PowerShell or terminal): `ssh-keygen -t ed25519`, then give the public key
   (`~/.ssh/id_ed25519.pub`) to the machine's administrator, or add it yourself to `~/.ssh/authorized_keys` on the
   machine. ⟳ Some institutes require a VPN or a jump host first.
4. Add the machine to `~/.ssh/config` on the laptop (names are examples):
   ```
   Host greenpatch
       HostName <machine address>
       User <your user name>
       IdentityFile ~/.ssh/id_ed25519
       # ProxyJump <gateway>     # only if there is a jump host
   ```
5. Test from a terminal: `ssh greenpatch`.

## Step 3 — connect VS Code to the machine
1. VS Code: `Ctrl+Shift+P` → **Remote-SSH: Connect to Host** → `greenpatch`. VS Code installs its server part on the
   machine (first time only).
2. In the remote window, install the **Claude Code** extension when VS Code offers it "in SSH: greenpatch" (extensions
   run on the remote side), and sign in with your Claude account. Alternative: install the Claude Code CLI on the
   machine and run `claude` in the VS Code terminal. [VERIFY on the day: the exact sign-in flow on a remote host.]

## Step 4 — set up the project on the machine (Claude can do this once connected)
```bash
git clone https://github.com/yairsuari/greenpatch.git greenpatch2026 && cd greenpatch2026
python3 -m venv --system-site-packages .venv          # CLAUDE.md rule
.venv/bin/python -c "import xarray, cartopy"           # check what exists before installing
.venv/bin/pip install -r env/requirements.txt          # only what is missing
.venv/bin/copernicusmarine login                      # your Copernicus Marine account
```
**Data folder (user 2026-11-08: the home disk on the machine is very limited).** Decide on the first login where the
data go: ask the administrator for a large project/scratch/work disk. Size: raw full domain ~139 GB (dry run
2026-10-26) + SST + `interim`/`processed` (estimate from the pilot ratio on the day [VERIFY]) + Q3 model runs; ask for
≥ 300 GB. Check whether that disk is backed up or purged after N days (scratch disks often are), since a purge
would delete `data/interim`, `data/processed` and the runs. Keep the git clone (code, guidelines, results figures; small) in
home, and put only the heavy folders on the big disk via symlinks. No code change is needed: all paths go through
`config.ROOT / "data"`.
```bash
BIG=/path/to/big/disk/greenpatch          # ⟳ the path the administrator gives
mkdir -p $BIG/data $BIG/model_runs $BIG/cache
ln -s $BIG/data data                      # inside the clone, before any download
mkdir -p model && ln -s $BIG/model_runs model/runs
export PIP_CACHE_DIR=$BIG/cache/pip TMPDIR=$BIG/cache/tmp   # add to ~/.bashrc; keeps caches off home
mkdir -p $TMPDIR && df -h ~ $BIG                           # check free space on both
```
If symlinks are not allowed on that file system, add an environment variable `GREENPATCH_DATA` to `config.py`
(Claude, small change). Also check where the venv lives; with `--system-site-packages` it is small, but move it to
`$BIG` if home is very tight.

⟳ On a cluster, load modules first (Python, NetCDF/HDF5, later compilers and MPI for NEMO/OGSTM-BFM).
Paths in the code are relative to the project root; on Linux use `.venv/bin/python` instead of
`.venv\Scripts\python`.

## Step 5 — running long jobs
- Long runs must survive closing the laptop: use **`tmux`** (`tmux new -s gp`, detach with `Ctrl+B D`, return with
  `tmux attach -t gp`), or ⟳ the scheduler (Slurm/PBS: one job per tile, see `06_local_pilot.md`).
- Full-domain order: `06_local_pilot.md`, "Running on the external machine".

## Step 6 — getting results back
- Code, guidelines, figures and the manuscript go through git (commit and push on the machine, pull elsewhere).
- To open a single file locally (a figure, `reports/ms_draft.docx` in Word): right-click it in the VS Code explorer →
  **Download**. Edit in Word, then upload back (drag into the explorer) or commit from the laptop. Manuscript rule
  unchanged: Claude's edits are tracked changes with a backup in `reports/versions/`.

## What can go wrong
- **Two copies drifting apart** (this laptop, second laptop, machine): treat the machine's clone + GitHub as the only
  working copy from now on; do not edit this folder in parallel.
- **Credentials:** never commit `.netrc`, `.env`, `.copernicusmarine/` (already in `.gitignore`).
- **Firewall:** the machine must reach `*.marine.copernicus.eu` and `github.com`; check before the 139 GB download.
