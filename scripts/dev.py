#!/usr/bin/env python3
"""Start, stop, build and check every cmb-lab service, on any platform.

    python scripts/dev.py setup      create the venv and install every package
    python scripts/dev.py toolchain  fetch the Go toolchain for this OS/arch
    python scripts/dev.py build      build the gateway binary and the frontend
    python scripts/dev.py up         start all Python services + the Go gateway
    python scripts/dev.py down       stop everything
    python scripts/dev.py status     health-check every service
    python scripts/dev.py logs       follow all service logs

This replaces the old bash-only script. Process control uses PID files, sockets and
taskkill/SIGTERM rather than pkill and lsof, so it behaves the same on Windows,
macOS and Linux.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent.parent
WINDOWS = os.name == "nt"
EXE = ".exe" if WINDOWS else ""

VENV = ROOT / ".venv"
VENV_BIN = VENV / ("Scripts" if WINDOWS else "bin")
LOGS = ROOT / "data" / "logs"
RUN = ROOT / "data" / "run"

TOOLCHAIN = ROOT / ".toolchain"
GO = TOOLCHAIN / "go" / "bin" / f"go{EXE}"
GATEWAY_BIN = ROOT / "services" / "gateway" / "bin" / f"gateway{EXE}"

SERVICES = {
    "catalog": 8001,
    "spectrum": 8003,
    "cosmology": 8004,
    "anomaly": 8005,
    "skymap": 8007,
    "tutor": 8008,
    "chat": 8009,
    "playground": 8010,
}
GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8080"))

PY_PACKAGES = [
    "catalog",
    "ingest",
    "spectrum",
    "cosmology",
    "anomaly",
    "skymap",
    "tutor",
    "chat",
    "playground",
]


# --------------------------------------------------------------------------- output


def _supports_colour() -> bool:
    if not sys.stdout.isatty():
        return False
    if not WINDOWS:
        return True
    # Windows 10+ can do ANSI, but the console needs virtual terminal mode switched on.
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        return bool(kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7))
    except Exception:
        return False


COLOUR = _supports_colour()
GREEN = "\033[32m" if COLOUR else ""
RED = "\033[31m" if COLOUR else ""
DIM = "\033[2m" if COLOUR else ""
RESET = "\033[0m" if COLOUR else ""


def info(msg: str) -> None:
    print(f"  {msg}")


def die(msg: str) -> NoReturn:
    print(f"{RED}error{RESET}: {msg}", file=sys.stderr)
    raise SystemExit(1)


# --------------------------------------------------------------------------- env


def load_env() -> dict[str, str]:
    """Read .env into a dict, so keys like GEMINI_API_KEY reach the service processes."""
    env = dict(os.environ)
    dotenv = ROOT / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text(encoding="utf8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip("'\"")
    env["DATA_DIR"] = str(ROOT / "data")  # always absolute, whatever .env says
    return env


# --------------------------------------------------------------------------- process


def _pidfile(name: str) -> Path:
    return RUN / f"{name}.pid"


def _alive(pid: int) -> bool:
    if WINDOWS:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
        ).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _terminate(pid: int) -> None:
    if WINDOWS:
        # /T kills the child tree too; uvicorn's reloader spawns one.
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return
    for _ in range(40):
        if not _alive(pid):
            return
        time.sleep(0.25)
    with contextlib.suppress(OSError, ProcessLookupError):
        os.kill(pid, signal.SIGKILL)


def _spawn(cmd: list[str], log: Path, env: dict[str, str]) -> int:
    """Launch a detached background process writing to log, and return its pid."""
    log.parent.mkdir(parents=True, exist_ok=True)
    handle = log.open("ab")
    kwargs: dict[str, object] = {"stdout": handle, "stderr": subprocess.STDOUT, "cwd": ROOT}
    if WINDOWS:
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, env=env, **kwargs)  # type: ignore[arg-type]
    return proc.pid


def _port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _healthy(port: int, path: str = "/health") -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=4) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError, ValueError):
        return False


# --------------------------------------------------------------------------- commands


def cmd_up(_args: argparse.Namespace) -> int:
    if not VENV_BIN.exists():
        die(f"no virtualenv at {VENV} — run: python scripts/dev.py setup")

    cmd_down(_args, quiet=True)
    env = load_env()
    LOGS.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)

    uvicorn = VENV_BIN / f"uvicorn{EXE}"
    if not uvicorn.exists():
        die(f"uvicorn missing at {uvicorn} — run: python scripts/dev.py setup")

    for name, port in SERVICES.items():
        pid = _spawn(
            [
                str(uvicorn),
                f"cmblab_{name}.main:app",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            LOGS / f"{name}.log",
            env,
        )
        _pidfile(name).write_text(str(pid), encoding="utf8")
        info(f"started {name} on :{port}")

    if GATEWAY_BIN.exists():
        pid = _spawn([str(GATEWAY_BIN)], LOGS / "gateway.log", env)
        _pidfile("gateway").write_text(str(pid), encoding="utf8")
        info(f"started gateway on :{GATEWAY_PORT}")
    else:
        info("gateway binary missing — run: python scripts/dev.py build")

    print("waiting for services to come up...")
    deadline = time.time() + 30
    while time.time() < deadline:
        if all(_healthy(p) for p in SERVICES.values()):
            break
        time.sleep(1)
    return cmd_status(_args)


def cmd_down(_args: argparse.Namespace, quiet: bool = False) -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    for name in [*SERVICES, "gateway"]:
        pidfile = _pidfile(name)
        if not pidfile.is_file():
            continue
        try:
            pid = int(pidfile.read_text(encoding="utf8").strip())
        except ValueError:
            pidfile.unlink(missing_ok=True)
            continue
        if _alive(pid):
            _terminate(pid)
            if not quiet:
                info(f"stopped {name}")
        pidfile.unlink(missing_ok=True)

    # Signalling only asks; the kernel releases the listening socket a moment later.
    # Without waiting, `restart` can relaunch into "address already in use".
    for port in [*SERVICES.values(), GATEWAY_PORT]:
        for _ in range(40):
            if not _port_busy(port):
                break
            time.sleep(0.25)
        else:
            if not quiet:
                info(f"{DIM}port {port} still held by a stray process{RESET}")
    return 0


def cmd_restart(args: argparse.Namespace) -> int:
    cmd_down(args)
    return cmd_up(args)


def cmd_status(_args: argparse.Namespace) -> int:
    print(f"{'SERVICE':<12} {'PORT':<6} STATUS")
    down = 0
    for name, port in SERVICES.items():
        if _healthy(port):
            print(f"{name:<12} {port:<6} {GREEN}ok{RESET}")
        else:
            down += 1
            print(f"{name:<12} {port:<6} {RED}down{RESET}  (see {LOGS / f'{name}.log'})")

    if _healthy(GATEWAY_PORT, "/api/v1/health"):
        print(f"{'gateway':<12} {GATEWAY_PORT:<6} {GREEN}ok{RESET}")
    else:
        down += 1
        print(f"{'gateway':<12} {GATEWAY_PORT:<6} {RED}down{RESET}")
    return 1 if down else 0


def cmd_logs(args: argparse.Namespace) -> int:
    names = [args.service] if args.service else [*SERVICES, "gateway"]
    files = [LOGS / f"{n}.log" for n in names]
    files = [f for f in files if f.is_file()]
    if not files:
        die(f"no logs in {LOGS} — start something first")

    handles = {}
    for f in files:
        handle = f.open("r", encoding="utf8", errors="replace")
        # Show the tail, then follow.
        lines = handle.readlines()
        for line in lines[-30 // len(files) or -1 :]:
            print(f"{DIM}{f.stem}{RESET} | {line}", end="")
        handles[f.stem] = handle

    try:
        while True:
            quiet = True
            for stem, handle in handles.items():
                for line in handle.readlines():
                    print(f"{DIM}{stem}{RESET} | {line}", end="")
                    quiet = False
            if quiet:
                time.sleep(0.4)
    except KeyboardInterrupt:
        return 0
    finally:
        for handle in handles.values():
            handle.close()


# --------------------------------------------------------------------------- setup


def _find_python312() -> str:
    """Locate a 3.12 interpreter. healpy and camb have no 3.13/3.14 wheels yet."""
    if sys.version_info[:2] == (3, 12):
        return sys.executable
    candidates = ["python3.12", "python3", "python"]
    if WINDOWS:
        candidates = ["py", "python3.12", "python"]
    for name in candidates:
        exe = shutil.which(name)
        if not exe:
            continue
        cmd = [exe, "-3.12", "-c", "import sys;print(sys.executable)"] if name == "py" else [
            exe,
            "-c",
            "import sys;print(sys.executable)",
        ]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            continue
        if out.returncode != 0:
            continue
        found = out.stdout.strip()
        ver = subprocess.run(
            [found, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        if ver == "3.12":
            return found
    die(
        "Python 3.12 not found. healpy and camb do not ship wheels for 3.13+.\n"
        "  Windows: winget install Python.Python.3.12\n"
        "  macOS:   brew install python@3.12\n"
        "  Linux:   sudo apt install python3.12 python3.12-venv"
    )


def cmd_setup(_args: argparse.Namespace) -> int:
    env_example = ROOT / ".env.example"
    dotenv = ROOT / ".env"
    if env_example.is_file() and not dotenv.is_file():
        shutil.copyfile(env_example, dotenv)
        info("created .env")

    if not VENV_BIN.exists():
        python = _find_python312()
        info(f"creating virtualenv with {python}")
        subprocess.run([python, "-m", "venv", str(VENV)], check=True)

    pip = [str(VENV_BIN / f"python{EXE}"), "-m", "pip"]
    subprocess.run([*pip, "install", "--upgrade", "pip", "wheel"], check=True)
    subprocess.run([*pip, "install", "-e", "libs/cmblab-core[dev]"], cwd=ROOT, check=True)

    for name in PY_PACKAGES:
        pkg = ROOT / "services" / name
        if (pkg / "pyproject.toml").is_file():
            info(f"installing services/{name}")
            subprocess.run([*pip, "install", "-e", str(pkg)], cwd=ROOT, check=True)

    print("done. next: python scripts/dev.py toolchain && python scripts/dev.py build")
    return 0


# --------------------------------------------------------------------------- toolchain


def _go_archive_name() -> tuple[str, str]:
    """Return (goos, goarch) using Go's naming, derived from this machine."""
    system = platform.system().lower()
    goos = {"darwin": "darwin", "linux": "linux", "windows": "windows"}.get(system)
    if goos is None:
        die(f"unsupported OS for the vendored Go toolchain: {platform.system()}")

    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        goarch = "arm64"
    elif machine in ("x86_64", "amd64"):
        goarch = "amd64"
    else:
        die(f"unsupported CPU architecture: {platform.machine()}")
    return goos, goarch


def cmd_toolchain(_args: argparse.Namespace) -> int:
    if GO.exists():
        subprocess.run([str(GO), "version"], check=False)
        return 0

    goos, goarch = _go_archive_name()
    with urllib.request.urlopen("https://go.dev/VERSION?m=text", timeout=30) as resp:
        version = resp.read().decode().splitlines()[0].strip()

    suffix = "zip" if goos == "windows" else "tar.gz"
    url = f"https://go.dev/dl/{version}.{goos}-{goarch}.{suffix}"
    info(f"downloading {version} for {goos}/{goarch}")

    TOOLCHAIN.mkdir(parents=True, exist_ok=True)
    archive = TOOLCHAIN / f"go.{suffix}"
    with urllib.request.urlopen(url, timeout=600) as resp, archive.open("wb") as out:
        shutil.copyfileobj(resp, out)

    if suffix == "zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(TOOLCHAIN)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(TOOLCHAIN, filter="data")  # refuse absolute/traversing paths
    archive.unlink(missing_ok=True)

    if not WINDOWS:
        GO.chmod(0o755)
    subprocess.run([str(GO), "version"], check=True)
    return 0


# --------------------------------------------------------------------------- build


def cmd_build(args: argparse.Namespace) -> int:
    only = args.target
    if only in (None, "gateway"):
        if not GO.exists():
            die("Go toolchain missing — run: python scripts/dev.py toolchain")
        env = dict(os.environ)
        env.update(
            GOTOOLCHAIN="local",
            GOPATH=str(TOOLCHAIN / "gopath"),
            CGO_ENABLED="0",
        )
        GATEWAY_BIN.parent.mkdir(parents=True, exist_ok=True)
        info("building gateway")
        subprocess.run(
            [str(GO), "build", "-o", str(GATEWAY_BIN), "./cmd/gateway"],
            cwd=ROOT / "services" / "gateway",
            env=env,
            check=True,
        )

    if only in (None, "web"):
        npm = shutil.which("npm")
        if not npm:
            die("npm not found — install Node 20+ from https://nodejs.org")
        web = ROOT / "web"
        if not (web / "node_modules").is_dir():
            info("installing frontend dependencies")
            subprocess.run([npm, "install"], cwd=web, check=True)
        info("building frontend")
        subprocess.run([npm, "run", "build"], cwd=web, check=True)

    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    """Report whether every prerequisite for this platform is present."""
    print(
        f"platform     {platform.system()} {platform.machine()} "
        f"(python {platform.python_version()})"
    )
    rows: list[tuple[str, bool, str]] = []

    py312 = sys.version_info[:2] == (3, 12) or shutil.which("python3.12") is not None
    rows.append(("Python 3.12", py312, "healpy/camb have no 3.13+ wheels"))
    rows.append(("virtualenv", VENV_BIN.exists(), str(VENV)))
    rows.append(("Go toolchain", GO.exists(), str(GO)))
    rows.append(("gateway binary", GATEWAY_BIN.exists(), str(GATEWAY_BIN)))
    rows.append(("Node/npm", shutil.which("npm") is not None, "needed for the frontend"))
    rows.append(("frontend build", (ROOT / "web" / "dist").is_dir(), "web/dist"))
    rows.append(("data downloaded", (ROOT / "data" / "clean").is_dir(), "data/clean"))

    say = shutil.which("say") and shutil.which("afconvert")
    rows.append((
        "audio narration",
        bool(say),
        "optional — macOS only; elsewhere the browser speaks",
    ))

    print()
    for label, ok, note in rows:
        mark = f"{GREEN}yes{RESET}" if ok else f"{RED}no {RESET}"
        print(f"  {mark}  {label:<18} {DIM}{note}{RESET}")

    if WINDOWS:
        print(
            f"\n{RED}Native Windows will not work.{RESET} healpy ships no Windows build, and\n"
            "spectrum, anomaly, skymap and tutor all need it. Use WSL2 (wsl --install -d Ubuntu)\n"
            "or Docker (docker build -t cmb-lab . && docker run -p 7860:7860 cmb-lab)."
        )
    return 0


# --------------------------------------------------------------------------- cli


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="dev.py", description="Run cmb-lab on macOS, Linux or Windows."
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="create the venv and install every package")
    sub.add_parser("toolchain", help="download the Go toolchain for this OS/arch")
    build = sub.add_parser("build", help="build the gateway binary and the frontend")
    build.add_argument("target", nargs="?", choices=["gateway", "web"])
    sub.add_parser("up", help="start every service")
    sub.add_parser("down", help="stop every service")
    sub.add_parser("restart", help="stop then start")
    sub.add_parser("status", help="health-check every service")
    logs = sub.add_parser("logs", help="follow service logs")
    logs.add_argument("service", nargs="?", choices=[*SERVICES, "gateway"])
    sub.add_parser("doctor", help="check this machine has what it needs")

    args = parser.parse_args()
    handlers = {
        "setup": cmd_setup,
        "toolchain": cmd_toolchain,
        "build": cmd_build,
        "up": cmd_up,
        "down": cmd_down,
        "restart": cmd_restart,
        "status": cmd_status,
        "logs": cmd_logs,
        "doctor": cmd_doctor,
    }
    handler = handlers.get(args.command or "status")
    try:
        return handler(args) or 0  # type: ignore[misc]
    except subprocess.CalledProcessError as exc:
        die(f"command failed with exit code {exc.returncode}: {' '.join(map(str, exc.cmd))}")
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
