# Linux & Docker Cheatsheet

> reference for Docker, Linux, and Git commands.


## Docker — Containers

| Command | Description |
|---|---|
| `docker compose up -d --build` | Build and start containers in detached mode. Use `--build` only when Dockerfile or dependencies changed. |
| `docker compose up -d` | Start containers in detached mode without rebuilding images. |
| `docker compose down` | Stop and remove containers and networks. Add `--volumes` to also remove named volumes. |
| `docker compose stop` | Pause containers without removing them. Resume with `docker compose start`. |
| `docker compose restart` | Restart all containers in the current project without rebuilding. |
| `docker restart <id>` | Restart a specific container by its ID or name. |
| `docker ps` | List all running containers on the host. Add `-a` to include stopped containers. |
| `docker compose ps` | List containers scoped to the current compose project. |
| `docker stats` | Live stream of CPU, memory, and network usage per container. |
| `docker inspect <id>` | Return low-level JSON details about a container (IP, mounts, env vars, etc.). |
| `docker rm <id>` | Remove a stopped container. Add `-f` to force-remove a running one. |
| `docker system prune` | Remove all stopped containers, unused networks, dangling images, and build cache. |

---

## Docker — Logs & Shell Access

| Command | Description |
|---|---|
| `docker compose logs -f` | Follow live log output for all services in the current project. |
| `docker compose logs -f <service>` | Follow logs for a single named service (e.g. `web`, `db`). |
| `docker logs <id>` | Print log output from a specific container. Add `--tail 100` to limit to last 100 lines. |
| `docker exec -it <id> bash` | Open an interactive bash shell inside a running container. Use `sh` for Alpine-based images. |
| `docker exec <id> <cmd>` | Run a one-off command inside a running container without opening a shell. |

---

## Docker — Images

| Command | Description |
|---|---|
| `docker images` | List all locally available images. |
| `docker pull <image>:<tag>` | Download an image from a registry (default: Docker Hub). |
| `docker build -t <name> .` | Build an image from the Dockerfile in the current directory and tag it. |
| `docker rmi <image>` | Remove a local image by name or ID. |
| `docker image prune` | Delete all dangling (untagged) images to free up disk space. |

---

## Linux — Navigation & Files

| Command | Description |
|---|---|
| `pwd` | Print the current working directory path. |
| `ls -lah` | List files in long format with human-readable sizes, including hidden files. |
| `cd <path>` | Change directory. Use `cd ~` for home, `cd -` to return to previous directory. |
| `cp -r <src> <dest>` | Copy files or directories recursively. |
| `mv <src> <dest>` | Move or rename a file or directory. |
| `rm -rf <path>` | Forcefully remove a file or directory and all its contents. Use with caution. |
| `mkdir -p <path>` | Create a directory and all missing parent directories. |
| `find <dir> -name "*.log"` | Search for files matching a pattern within a directory tree. |
| `cat <file>` | Print the full contents of a file to stdout. |
| `less <file>` | Scroll through a file interactively. Press `q` to quit. |
| `tail -f <file>` | Follow a file in real time — useful for watching log files. |
| `grep -r "pattern" <dir>` | Recursively search for a text pattern across files in a directory. |
| `chmod +x <file>` | Make a file executable. Use `chmod 755` for scripts others can read/execute. |
| `chown user:group <file>` | Change the owner and group of a file or directory. Add `-R` to apply recursively. |
| `ln -s <target> <link>` | Create a symbolic link pointing to a target file or directory. |

---

## Linux — Processes & System

| Command | Description |
|---|---|
| `top` / `htop` | Interactive process viewer. `htop` is more readable (may need installing). |
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

## systemd — Services

| Command | Description |
|---|---|
| `sudo systemctl daemon-reload` | Reload systemd to pick up new or modified unit files. Run after editing any `.service` or `.timer` file. |
| `sudo systemctl enable <unit>` | Enable a service to start automatically at boot. Add `--now` to also start it immediately. |
| `sudo systemctl disable <unit>` | Prevent a service from starting automatically at boot. |
| `sudo systemctl start <unit>` | Start a service immediately without waiting for reboot. |
| `sudo systemctl stop <unit>` | Stop a running service immediately. |
| `sudo systemctl restart <unit>` | Stop then start a service. Use after config changes that require a full restart Or changes to underlying python files?. |
| `sudo systemctl reload <unit>` | Signal the service to reload its config without a full restart (if supported by the service). |
| `systemctl status <unit>` | Show the current state of a service — running, failed, enabled — plus recent log lines. |
| `systemctl is-active <unit>` | Print `active` or `inactive` — useful in scripts to check service state. |
| `systemctl is-enabled <unit>` | Check if a unit is configured to start at boot. |
| `systemctl list-units --type=service` | List all currently loaded service units and their states. |
| `systemctl list-unit-files` | List all installed unit files and whether they are enabled or disabled. |

---

## systemd — Timers

| Command | Description |
|---|---|
| `systemctl list-timers --all` | List all timers with their next and last trigger times. |
| `sudo systemctl enable --now <name>.timer` | Enable and immediately start a timer unit. No need for restart |
| `sudo systemctl disable --now <name>.timer` | Disable a timer so it no longer runs automatically. Needs restart to take effect if don't use --now |
| `systemctl status <name>.timer` | Inspect a timer's state, last activation, and next scheduled run. |
| `sudo systemctl start <name>.timer` | Start a timer immediately (one-off, without enabling at boot). |

---

## systemd — Logs (journalctl)

| Command | Description |
|---|---|
| `journalctl -u <unit>` | Show all journal logs for a specific service or timer unit. Use aarow keys to scroll |
| `journalctl -u <unit> -f` | Follow live log output for a unit — equivalent to `tail -f` for systemd. |
| `journalctl -u <unit> -n 50` | Show the last 50 log lines for a unit. |
| `journalctl -u <unit> --since "1h ago"` | Show logs from the past hour. Also accepts timestamps like `"2024-01-01 12:00"`. |
| `journalctl -p err -b` | Show only error-level (and above) messages from the current boot. |
| `journalctl --disk-usage` | Show how much disk space the journal logs are consuming. |
| `sudo journalctl --vacuum-time=7d` | Delete journal logs older than 7 days to reclaim disk space. |

---

## systemd — Unit File Reference

| Path / Command | Description |
|---|---|
| `/etc/systemd/system/` | Where you place custom `.service` and `.timer` unit files. Takes priority over defaults. |
| `/lib/systemd/system/` | Default unit files installed by packages. Don't edit these — override in `/etc/systemd/system/` instead. |
| `systemctl cat <unit>` | Print the full contents of a unit file and any active override files. |
| `systemctl edit <unit>` | Open an override file for a unit without touching the original. Changes survive package updates. |


 
## Git — Everyday Commands
 
| Command | Description |
|---|---|
| `git status` | Show changed, staged, and untracked files in the working directory. |
| `git log --oneline` | Compact commit history — one line per commit. Add `-10` to limit to last 10. |
| `git diff` | Show unstaged changes. Add `--staged` to see what's already staged for commit. |
| `git add <file>` | Stage a specific file for commit. Use `git add .` to stage all changes. |
| `git commit -m "message"` | Commit staged changes with a message. |
| `git push` | Push committed changes to the remote (GitHub). |
| `git pull` | Fetch and merge changes from the remote into the current branch. |
| `git branch` | List local branches. Add `-r` for remote branches, `-a` for all. |
| `git checkout -b <branch>` | Create and switch to a new branch. |
| `git checkout <branch>` | Switch to an existing branch. |
| `git stash` | Temporarily shelve uncommitted changes. Restore with `git stash pop`. |
| `git fetch origin` | Download latest changes from GitHub without touching your working directory. |
| `git reset --hard origin/main` |      Reset tracked files to exactly match the remote branch, discarding all local changes. Could also be master instead of main |
| `git clean -fd` | Delete untracked **files and directories** that are not in `.gitignore`. Run after `reset --hard` to fully clean up. |
| `git pull --rebase` | Pull and replay your commits on top of the remote — cleaner history than a merge commit. |

---