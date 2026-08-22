# General Coding & Computer Cheatsheet


## Docker
#### Basic Docker commands, everything else I can do in Portainer
| Command | Description |
|---|---|
| `docker compose up -d --build` | Build and start containers in detached mode rebuilding the docker images from scratch.
| `docker compose down` | Stop and remove containers and networks. Add `--volumes` to also remove named volumes. |
| `docker images` | List all locally available images. |
| `docker pull <image>:<tag>` | Download an image from a registry. Default is Docker Hub. |
| `docker system df` | See what components of docker are taking up space (images, containers, local volumes, build cache). Add `-v` for more detailed breakdown.  |
| `docker builder prune` | Remove dangling cache. Add `-a` to remove all unused build cache that isn't currently needed. Add `--filter "until=168h"` to remove cache that hasn't been used in a week. |

---

## UV
| Command | Description |
|---|---|
| `uv init <repo name> --bare` | Initialize project with only `.pyproject.toml`. Use `--no-package` to create more traditional UV file setup with also sample main.py, a readme, `.python-version`, and a gitignore file. |
| `uv python install 3.14.6` | Install a specific python version to computer. |
| `uv python upgrade 3.14` | Install the latest minor Python version for a particular major feature . 3.14.6 -> 3.14.7 |
| `uv sync` | Sync the virtual env to all packages in the project |
| `uv lock --upgrade` | Upgrade all packages, respects packages set to specific versions in `pyproject.toml`. Will update dependencies of those packages if constraints permit it. |
| `uv export --format requirements.txt` | Export contents of the lockfile to a requirements.txt file. | 

---

#### Workflows

**Change Python version for a project**

1. Change `requires-python` in `pyproject.toml` to desired python version such as `3.14.6`.
2. Run `uv sync`.

**Set a specific package version for project**

1. Change package version under dependencies in `pyproject.toml`.
2. Ensure package is locked to specific version like `pandas==3.0.5`.
3. Run `uv sync`.
---

## Git — Everyday Commands
 
| Command | Description |
|---|---|
| `git status` | Show changed, staged, and untracked files in the working directory. |
| `git add <file>` | Stage a specific file for commit. Use `git add .` to stage all changes. |
| `git log --oneline` | Compact commit history. Add `-10` to limit to last 10. Use `--pretty=oneline` instead to get full commit ID (SHA). |
| `git branch` | List local branches. Add `-r` for remote branches, `-a` for all. |
| `git checkout <branch>` | Switch to an existing branch. Use `git checkout <SHA>` to inspect a previous commit. |
| `git checkout -b <branch>` | Create a new branch and switch to it. |

---

#### Workflows

**Sync local repo to the latest remote version**

1. Run `git fetch origin` to download the latest commits and refs from GitHub without modifying local files or the current branch.
2. Run `git reset --hard origin/main` to make the current local branch and tracked files exactly match `origin/main`, discarding local commits and uncommitted changes that aren't on the remote. |
3. Replace `main` with `master` if that is the remote's default branch.
4. **Result:** The local repo's tracked files and current branch now match the remote branch. `git reset --hard` does not remove untracked files.
5. To fully clean up and remove untracked files and directories run `git clean -fd`.

---

## systemd — Services, Timers, and Logs

| Command | Description |
|---|---|
| `/etc/systemd/system/` | Where you place custom `.service` and `.timer` unit files. Takes priority over defaults. |
| `sudo systemctl daemon-reload` | Reload systemd to pick up new or modified unit files. Run after editing any `.service` or `.timer` file. |
| `sudo systemctl enable --now <unit>` | Enable a unit at boot and starts it now.|
| `sudo systemctl disable --now <unit>` | Disable a unit from launching at boot and also stop it now. |
| `sudo systemctl start <unit>` | Start a service or timer immediately one-off, without enabling at boot. |
| `sudo systemctl stop <unit>` | Stop a service or timer immediately. If already enabled, will start again at next reboot. |
| `sudo systemctl restart <unit>` | Stop then start a service or timer. |
| `systemctl status <unit>` | Show the current state of a service or timer. Used to see if timer/service is running, failed, or enabled. |
| `systemctl list-timers --all` | List all timers with their next and last trigger times. |
| `journalctl -u <unit>` | Show all journal logs for a specific service or timer unit. Use aarow keys to scroll. Add `-f` to follow live log output. Add `-n 50` to show last 50 log lines. |
| `journalctl --disk-usage` | Show how much disk space the journal logs are consuming. |
| `sudo journalctl --vacuum-time=7d` | Delete journal logs older than 7 days to reclaim disk space. |

---

#### Workflows

**Create and start new systemd workflow**

1. Create `my-script.service` to define what runs.
2. Create `my-script.timer` to defines when new service runs.
3. run `sudo systemctl daemon-reload`refresh systemd with updated .timer and .service files.
4. Enable timer to start running `sudo systemctl enable --now my-script.timer`
5. To fully clean up and remove untracked files and directories run `git clean -fd`.

---

## systemd — Targets / Desktop Environment

| Command | Description |
|---|---|
| `systemctl get-default` | Shows what default graphic manager linux is currently set to, either headless (`multi-user.target`) or a regular GUI (`graphical.target`). |
| `sudo systemctl set-default <unit>` | Set default boot GUI. Use `multi-user.target` for headless or `graphical.target` for xfce GUI. |
| `sudo systemctl isolate graphical.target` | Temporarily switch to xfce GUI. Resets back to default after reboot |

---


## Linux — Navigation & Files

| Command | Description |
|---|---|
| `pwd` | Print the current working directory path. |
| `ls -lah` | List files directory with last modified date + file size. |
| `cd -` | Navigate to previous directory. |
| `cp -r <src> <dest>` | Copy files or directories to new locations. -r (recursive) will include all subdirectories. |
| `mv <src> <dest>` | Move or rename a file or directory. -r not needed here. |
| `rm -rf <path>` | Forcefully remove a file or directory and all its contents. Use with caution. |
| `mkdir -p <path>` | Create a directory. -p fills in all missing parent directories if don't already exist 'mkdir projects/python/app' |
| `cat <file>` | Print the full contents of a file to stdout. |
| `chmod +x <file>` | Makes a file executable, like a bash file for running systemd scripts
| `chown user:group <file>` | Change the owner and group of a file or directory. Add `-R` to apply recursively. |
| `inxi -F`, `inxi -Fxxx`, `inxi -S` | Various commands to see all computer system specs. |

---

## Linux — Processes & System

| Command | Description |
|---|---|
| `htop` | Interactive process viewer. Terminal task manager |
| `ps aux` | Snapshot of all running processes with PID, CPU, and memory usage. |
| `kill <pid>` | Send SIGTERM (graceful stop) to a process. Use `kill -9 <pid>` to force-kill. |
| `df -h` | Show disk usage for all mounted filesystems in human-readable format. |
| `du -sh <dir>` | Show total disk space used by a specific directory. |
| `free -h` | Display total, used, and available RAM and swap in human-readable format. |
| `uname -r` | Print the current Linux kernel version. |
| `uptime` | Show how long the system has been running and current load averages. |
| `history` | List previously run shell commands. Use `!<n>` to re-run command number n. |
| `env` | Print all current environment variables. |
| `export VAR=value` | Set an environment variable for the current session and child processes. |
| `crontab -e` | Edit the current user's cron jobs for scheduled task automation. |

---

## Linux — Networking

| Command | Description |
|---|---|
| `ip a` | Show all network interfaces and their IP addresses. |
| `ss -tulnp` | List all open TCP/UDP ports and the processes listening on them. |
| `ping <host>` | Test basic network connectivity to a host. |
| `curl -I <url>` | Fetch only the HTTP response headers from a URL — useful for quick health checks. |
| `wget <url>` | Download a file from the internet to the current directory. |
| `scp <src> user@host:<dest>` | Securely copy files to or from a remote machine over SSH. |
| `ssh user@host` | Open a secure shell session to a remote machine. |

---

