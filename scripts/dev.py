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
import json
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
NODE_DIR = TOOLCHAIN / "node"
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


def _arch() -> str:
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    if machine in ("x86_64", "amd64"):
        return "amd64"
    die(f"unsupported CPU architecture: {platform.machine()}")


def _go_archive_name() -> tuple[str, str]:
    """Return (goos, goarch) using Go's naming, derived from this machine."""
    system = platform.system().lower()
    goos = {"darwin": "darwin", "linux": "linux", "windows": "windows"}.get(system)
    if goos is None:
        die(f"unsupported OS for the vendored Go toolchain: {platform.system()}")
    return goos, _arch()


def _download(url: str, target: Path) -> None:
    with urllib.request.urlopen(url, timeout=900) as resp, target.open("wb") as out:
        shutil.copyfileobj(resp, out)


def _extract(archive: Path, into: Path) -> None:
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(into)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(into, filter="data")  # refuse absolute/traversing paths


def cmd_toolchain(_args: argparse.Namespace) -> int:
    if GO.exists():
        subprocess.run([str(GO), "version"], check=False)
        return 0

    goos, goarch = _go_archive_name()
    with urllib.request.urlopen("https://go.dev/VERSION?m=text", timeout=60) as resp:
        version = resp.read().decode().splitlines()[0].strip()

    suffix = "zip" if goos == "windows" else "tar.gz"
    info(f"downloading Go {version} for {goos}/{goarch}")

    TOOLCHAIN.mkdir(parents=True, exist_ok=True)
    archive = TOOLCHAIN / f"go.{suffix}"
    _download(f"https://go.dev/dl/{version}.{goos}-{goarch}.{suffix}", archive)
    _extract(archive, TOOLCHAIN)
    archive.unlink(missing_ok=True)

    if not WINDOWS:
        GO.chmod(0o755)
    subprocess.run([str(GO), "version"], check=True)
    return 0


# ------------------------------------------------------------------ node toolchain


def _vendored_npm() -> Path:
    # Windows puts npm at the root of the archive; every other platform uses bin/.
    return NODE_DIR / ("npm.cmd" if WINDOWS else "bin/npm")


def _npm() -> str | None:
    vendored = _vendored_npm()
    if vendored.exists():
        return str(vendored)
    return shutil.which("npm")


def cmd_node(_args: argparse.Namespace) -> int:
    """Vendor Node into .toolchain, so the frontend needs no system install."""
    if _vendored_npm().exists():
        info(f"node already vendored at {NODE_DIR}")
        return 0

    with urllib.request.urlopen("https://nodejs.org/dist/index.json", timeout=60) as resp:
        index = json.load(resp)
    release = next((e for e in index if e.get("lts")), None)
    if release is None:
        die("could not find a Node LTS release")
    version = release["version"]

    system = platform.system().lower()
    arch = "arm64" if _arch() == "arm64" else "x64"  # Node says x64, Go says amd64
    if system == "darwin":
        name, suffix = f"node-{version}-darwin-{arch}", "tar.gz"
    elif system == "linux":
        name, suffix = f"node-{version}-linux-{arch}", "tar.xz"
    elif system == "windows":
        name, suffix = f"node-{version}-win-{arch}", "zip"
    else:
        die(f"unsupported OS for the vendored Node toolchain: {platform.system()}")

    info(f"downloading Node {version} for {system}/{arch}")
    TOOLCHAIN.mkdir(parents=True, exist_ok=True)
    archive = TOOLCHAIN / f"node.{suffix}"
    _download(f"https://nodejs.org/dist/{version}/{name}.{suffix}", archive)
    _extract(archive, TOOLCHAIN)
    archive.unlink(missing_ok=True)

    extracted = TOOLCHAIN / name
    if NODE_DIR.exists():
        shutil.rmtree(NODE_DIR)
    extracted.rename(NODE_DIR)

    subprocess.run([str(_vendored_npm()), "--version"], check=True)
    return 0


# --------------------------------------------------------------------------- build


def cmd_build(args: argparse.Namespace) -> int:
    only = getattr(args, "target", None)  # bootstrap calls this without a target
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
        npm = _npm()
        if not npm:
            die("Node missing — run: python scripts/dev.py node")
        web = ROOT / "web"
        if not (web / "node_modules").is_dir():
            info("installing frontend dependencies")
            subprocess.run([npm, "install"], cwd=web, check=True)
        info("building frontend")
        subprocess.run([npm, "run", "build"], cwd=web, check=True)

    return 0


# --------------------------------------------------------------------------- bootstrap


def _ask(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        return False
    return input(f"  {question} [y/N] ").strip().lower() in ("y", "yes")


def _install_python312(assume_yes: bool) -> str | None:
    """Offer to install Python 3.12 with the platform's package manager."""
    system = platform.system().lower()
    if system == "darwin" and shutil.which("brew"):
        cmd, label = ["brew", "install", "python@3.12"], "Homebrew"
    elif system == "linux" and shutil.which("apt-get"):
        cmd = ["sudo", "apt-get", "install", "-y", "python3.12", "python3.12-venv"]
        label = "apt"
    elif system == "windows" and shutil.which("winget"):
        cmd = ["winget", "install", "-e", "--id", "Python.Python.3.12"]
        label = "winget"
    else:
        return None

    print("  Python 3.12 is required (healpy and camb have no 3.13+ wheels).")
    print(f"  Proposed: {' '.join(cmd)}")
    if not _ask(f"Install it with {label}?", assume_yes):
        return None
    subprocess.run(cmd, check=True)
    return shutil.which("python3.12")


def cmd_data(_args: argparse.Namespace) -> int:
    """Download and clean the minimum working dataset (~170 MB)."""
    ingest = VENV_BIN / f"cmblab-ingest{EXE}"
    if not ingest.exists():
        die("run `python scripts/dev.py setup` first")
    if (ROOT / "data" / "clean").is_dir() and any((ROOT / "data" / "clean").iterdir()):
        info("archive data already present")
        return 0
    info("downloading ~170 MB from NASA LAMBDA and ESA (no account needed)")
    subprocess.run([str(ingest), "bootstrap"], cwd=ROOT, check=False)
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    """Everything, from a bare machine to a running site, in one command."""
    print(f"cmb-lab bootstrap \u2014 {platform.system()} {platform.machine()}\n")

    backend = _choose_backend(args.backend, "up")
    if backend != "native":
        # Docker and WSL both provide their own Python, Node and Go.
        info(f"using the {backend} backend; it provides its own toolchain")
        if backend == "wsl":
            return _wsl_dispatch("bootstrap", args)
        return docker_up(args)

    if sys.version_info[:2] != (3, 12) and not shutil.which("python3.12"):
        if not _install_python312(getattr(args, "yes", False)):
            die(
                "Python 3.12 is required and could not be installed automatically.\n"
                "  macOS:   brew install python@3.12\n"
                "  Ubuntu:  sudo apt install python3.12 python3.12-venv\n"
                "  Windows: winget install -e --id Python.Python.3.12"
            )

    steps = (
        ("Python packages", cmd_setup),
        ("Go toolchain", cmd_toolchain),
        ("Node toolchain", cmd_node),
        ("gateway + frontend", cmd_build),
        ("archive data", cmd_data),
    )
    for n, (label, step) in enumerate(steps, 1):
        print(f"\n[{n}/{len(steps) + 1}] {label}")
        step(args)

    print(f"\n[{len(steps) + 1}/{len(steps) + 1}] starting services")
    rc = cmd_up(args)
    if rc == 0:
        print(f"\n  {GREEN}ready{RESET} -> http://localhost:5174")
        print(f"  {DIM}frontend dev server: make web{RESET}")
    return rc


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
    rows.append(("Go toolchain", GO.exists(), "auto-downloaded into .toolchain"))
    rows.append(("gateway binary", GATEWAY_BIN.exists(), str(GATEWAY_BIN)))
    node_note = "vendored" if _vendored_npm().exists() else "system"
    rows.append(("Node/npm", _npm() is not None, node_note))
    rows.append(("frontend build", (ROOT / "web" / "dist").is_dir(), "web/dist"))
    rows.append(("archive data", (ROOT / "data" / "clean").is_dir(), "data/clean"))

    say = shutil.which("say") and shutil.which("afconvert")
    rows.append((
        "audio narration",
        bool(say),
        "optional — macOS only; elsewhere the browser speaks",
    ))

    if WINDOWS:
        rows.append(("Docker", _docker_ready(), "default backend on Windows"))
        rows.append(("WSL", _wsl_distro() is not None, f"distro: {_wsl_distro() or 'none'}"))

    print()
    for label, ok, note in rows:
        mark = f"{GREEN}yes{RESET}" if ok else f"{RED}no {RESET}"
        print(f"  {mark}  {label:<18} {DIM}{note}{RESET}")

    if WINDOWS:
        print(
            f"\n{DIM}healpy has no Windows build, so spectrum, anomaly, skymap and tutor\n"
            f"cannot run natively. This script runs them in Docker or WSL instead.{RESET}"
        )
        try:
            print(f"  backend that would be used: {_choose_backend(None, 'status')}")
        except SystemExit:
            print(f"  {RED}no usable backend{RESET} — install Docker Desktop or run: wsl --install")
    return 0


# --------------------------------------------------------------------------- backends

IMAGE = "cmb-lab:latest"
CONTAINER = "cmb-lab"
CONTAINER_PORT = 7860
DATA_VOLUME = "cmb-lab-data"


def _docker() -> str | None:
    return shutil.which("docker")


def _docker_ready() -> bool:
    """Docker installed *and* the daemon actually up — Desktop is often not running."""
    exe = _docker()
    if not exe:
        return False
    return subprocess.run([exe, "info"], capture_output=True).returncode == 0


def _wsl_distro() -> str | None:
    """Name of the default WSL distribution, if any is installed."""
    if not WINDOWS or not shutil.which("wsl"):
        return None
    out = subprocess.run(
        ["wsl", "-l", "-q"], capture_output=True
    ).stdout.decode("utf-16-le", errors="ignore")
    for line in out.splitlines():
        name = line.strip().strip("\x00")
        if name:
            return name
    return None


def _choose_backend(explicit: str | None, command: str) -> str:
    choice = explicit or os.environ.get("CMBLAB_BACKEND") or "auto"

    if choice == "auto":
        if not WINDOWS:
            return "native"
        # healpy has no Windows build, so native is not an option here.
        if _docker_ready():
            return "docker"
        if _wsl_distro():
            return "wsl"
        die(
            "Windows needs either Docker or WSL, and neither was found.\n"
            "  Docker (simplest): https://docs.docker.com/desktop/install/windows-install/\n"
            "  WSL (fastest):     wsl --install -d Ubuntu\n"
            "Then re-run this command."
        )

    if choice == "native" and WINDOWS:
        die(
            "--backend native cannot work on Windows: healpy ships no Windows build and\n"
            "spectrum, anomaly, skymap and tutor all require it. Use --backend docker or wsl."
        )
    if choice not in ("native", "docker", "wsl"):
        die(f"unknown backend {choice!r} (expected native, docker or wsl)")
    if choice == "docker" and command in ("up", "build", "status", "logs") and not _docker_ready():
        die(
            "Docker is installed but the daemon is not responding.\n"
            "Start Docker Desktop (or `colima start`) and try again."
        )
    return choice


# ----------------------------------------------------------------- docker backend


def _container_state() -> str:
    """One of running, stopped, absent."""
    out = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name=^{CONTAINER}$", "--format", "{{.State}}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    return out or "absent"


def _image_exists() -> bool:
    # Must be an exact reference: `docker images -q cmb-lab` also matches cmb-lab:test,
    # which would skip the build and then fail to run cmb-lab:latest.
    return (
        subprocess.run(
            ["docker", "image", "inspect", IMAGE], capture_output=True
        ).returncode
        == 0
    )


def docker_build(_args: argparse.Namespace) -> int:
    info(f"building the {IMAGE} image (first run takes a while — CAMB compiles Fortran)")
    subprocess.run(["docker", "build", "-t", IMAGE, "."], cwd=ROOT, check=True)
    return 0


def docker_up(args: argparse.Namespace) -> int:
    if not _image_exists() or getattr(args, "rebuild", False):
        docker_build(args)

    if _container_state() != "absent":
        subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)

    cmd = [
        "docker", "run", "-d",
        "--name", CONTAINER,
        "-p", f"{CONTAINER_PORT}:{CONTAINER_PORT}",
        # Keeps the ~170 MB archive download across restarts.
        "-v", f"{DATA_VOLUME}:/app/data",
    ]
    key = load_env().get("GEMINI_API_KEY")
    if key:
        cmd += ["-e", f"GEMINI_API_KEY={key}"]
    cmd.append(IMAGE)

    subprocess.run(cmd, check=True, capture_output=True)
    info(f"container started, serving :{CONTAINER_PORT}")

    print("waiting for services (first run also downloads ~170 MB of archive data)...")
    deadline = time.time() + 1500
    while time.time() < deadline:
        if _container_state() == "exited":
            subprocess.run(["docker", "logs", "--tail", "30", CONTAINER])
            die("the container exited — see the log above")
        if _healthy(CONTAINER_PORT, "/api/v1/health"):
            print(f"\n  {GREEN}ready{RESET} -> http://localhost:{CONTAINER_PORT}")
            return 0
        time.sleep(5)
    info(f"{RED}still not healthy{RESET} — check: docker logs {CONTAINER}")
    return 1


def docker_down(_args: argparse.Namespace) -> int:
    if _container_state() == "absent":
        info("nothing running")
        return 0
    subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True, check=False)
    info("container stopped")
    return 0


def docker_status(_args: argparse.Namespace) -> int:
    state = _container_state()
    healthy = state == "running" and _healthy(CONTAINER_PORT, "/api/v1/health")
    mark = f"{GREEN}ok{RESET}" if healthy else f"{RED}{state}{RESET}"
    print(f"{'BACKEND':<12} {'PORT':<6} STATUS")
    print(f"{'docker':<12} {CONTAINER_PORT:<6} {mark}")
    if healthy:
        print(f"\n  http://localhost:{CONTAINER_PORT}")
    return 0 if healthy else 1


def docker_logs(_args: argparse.Namespace) -> int:
    if _container_state() == "absent":
        die(f"no {CONTAINER} container — run: python scripts/dev.py up")
    subprocess.run(["docker", "logs", "-f", "--tail", "50", CONTAINER], check=False)
    return 0


DOCKER_COMMANDS = {
    "up": docker_up,
    "bootstrap": docker_up,
    "down": docker_down,
    "restart": lambda a: (docker_down(a), docker_up(a))[1],
    "status": docker_status,
    "logs": docker_logs,
    "build": docker_build,
    "data": lambda _a: (info("the container downloads its own data on first start"), 0)[1],
    "setup": lambda _a: (info("nothing to set up — the image contains everything"), 0)[1],
    "toolchain": lambda _a: (info("not needed: Go is built inside the image"), 0)[1],
    "node": lambda _a: (info("not needed: Node is built inside the image"), 0)[1],
}


# -------------------------------------------------------------------- wsl backend


def _wsl_dispatch(command: str, args: argparse.Namespace) -> int:
    """Re-run this same script inside WSL, so Linux runs the one implementation."""
    distro = _wsl_distro()
    if not distro:
        die("no WSL distribution installed. Run: wsl --install -d Ubuntu")

    path = subprocess.run(
        ["wsl", "-d", distro, "wslpath", "-a", str(ROOT)],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not path:
        die("could not translate the repo path into WSL")

    extra = ""
    if command == "logs" and getattr(args, "service", None):
        extra = f" {args.service}"
    elif command == "build" and getattr(args, "target", None):
        extra = f" {args.target}"

    inner = f"cd {path} && python3 scripts/dev.py {command}{extra}"
    info(f"running in WSL ({distro})")
    return subprocess.run(["wsl", "-d", distro, "--", "bash", "-lc", inner]).returncode


# --------------------------------------------------------------------------- cli


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="dev.py", description="Run cmb-lab on macOS, Linux, or Windows via Docker/WSL."
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "native", "docker", "wsl"],
        help="where to run. Default: native on macOS/Linux, docker on Windows.",
    )
    sub = parser.add_subparsers(dest="command")

    boot = sub.add_parser("bootstrap", help="one command: install everything, then start")
    boot.add_argument("--yes", action="store_true", help="do not prompt before installing")
    sub.add_parser("setup", help="create the venv and install every package")
    sub.add_parser("toolchain", help="download the Go toolchain for this OS/arch")
    sub.add_parser("node", help="download the Node toolchain for this OS/arch")
    sub.add_parser("data", help="download the archive data (~170 MB)")
    build = sub.add_parser("build", help="build the gateway binary and the frontend")
    build.add_argument("target", nargs="?", choices=["gateway", "web"])
    up = sub.add_parser("up", help="start every service")
    up.add_argument("--rebuild", action="store_true", help="docker: rebuild the image first")
    sub.add_parser("down", help="stop every service")
    sub.add_parser("restart", help="stop then start")
    sub.add_parser("status", help="health-check every service")
    logs = sub.add_parser("logs", help="follow service logs")
    logs.add_argument("service", nargs="?", choices=[*SERVICES, "gateway"])
    sub.add_parser("doctor", help="check this machine has what it needs")

    args = parser.parse_args()
    command = args.command or "status"

    # doctor always reports on the machine you typed the command on.
    if command == "doctor":
        return cmd_doctor(args)

    backend = _choose_backend(args.backend, command)
    try:
        if backend == "wsl":
            return _wsl_dispatch(command, args)
        if backend == "docker":
            handler = DOCKER_COMMANDS.get(command)
            if handler is None:
                die(f"'{command}' is not available with the docker backend")
            return handler(args) or 0

        handlers = {
            "bootstrap": cmd_bootstrap,
            "setup": cmd_setup,
            "toolchain": cmd_toolchain,
            "node": cmd_node,
            "data": cmd_data,
            "build": cmd_build,
            "up": cmd_up,
            "down": cmd_down,
            "restart": cmd_restart,
            "status": cmd_status,
            "logs": cmd_logs,
        }
        return handlers[command](args) or 0
    except subprocess.CalledProcessError as exc:
        die(f"command failed with exit code {exc.returncode}: {' '.join(map(str, exc.cmd))}")
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
