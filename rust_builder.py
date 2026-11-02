"""Rust-Projekte komplett bauen: Abhaengigkeiten laden, kompilieren, testen, als ZIP abliefern (Werkzeug rust_project).

Ablauf je Aufruf:
  1. Das Cargo-Projekt (Ordner mit Cargo.toml) wird nach .rust/<name>/crate kopiert (ohne Dotdateien, target/ und
     rust-toolchain*, damit keine fremde Cargo-Konfiguration und keine andere Toolchain greift).
  2. `cargo fetch` laedt die Abhaengigkeiten (mit Internet, fuehrt aber keinen Code aus) nach .rust/cargo-home.
  3. build/test/run laufen mit --offline. Unter Linux in bubblewrap (kein Netz, nur /usr, Toolchain und der
     Bauordner sichtbar, keine .env), ohne bubblewrap nur mit PCL_CARGO_UNSAFE=1 direkt (z. B. Windows).
  4. package = test + release-Build + output/<name>.zip (Quelltext, Programm, Testbericht, LIESMICH.txt).
"""
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path

import agent_tools as T

IS_WIN = sys.platform.startswith("win")
CARGO_TIMEOUT = int(T._env("PCL_CARGO_TIMEOUT", "900"))
CARGO_MEM_MB = int(T._env("PCL_CARGO_MEM_MB", "3072"))
CARGO_JOBS = T._env("PCL_CARGO_JOBS", "2")
COPY_MAX_FILES = 2000
COPY_MAX_BYTES = 50 * 1024 * 1024
OPS = ("test", "build", "run", "package")
SKIP_NAMES = {"target", "rust-toolchain", "rust-toolchain.toml"}
_lock = threading.Lock()  # immer nur ein Rust-Bau gleichzeitig (RAM auf Pi/Laptop)
_NOISE = re.compile(r"^\s*(Compiling|Downloaded|Downloading|Fresh|Locking|Adding|Updating|Blocking|Checking|Packaging)\b")


def cargo_path():
    """cargo suchen: PCL_CARGO_PATH, PATH, sonst ~/.cargo/bin (Dienste haben ~/.cargo/bin oft nicht im PATH)."""
    p = T._env("PCL_CARGO_PATH")
    if p:
        return p if Path(p).is_file() else None
    found = shutil.which("cargo")
    if found:
        return found
    home = Path(os.environ.get("CARGO_HOME") or Path.home() / ".cargo") / "bin" / ("cargo.exe" if IS_WIN else "cargo")
    return str(home) if home.is_file() else None


def sandbox_mode():
    """'bwrap' (abgeschottet), 'unsafe' (direkt, nur mit PCL_CARGO_UNSAFE=1) oder '' (aus)."""
    if T._env("PCL_ALLOW_RUN", "1") == "0" or T._env("PCL_CARGO", "1") == "0" or not cargo_path():
        return ""
    if not IS_WIN and shutil.which("bwrap"):
        return "bwrap"
    return "unsafe" if T._env("PCL_CARGO_UNSAFE", "0") == "1" else ""


def cargo_enabled():
    return bool(sandbox_mode())


def _toolchain():
    """(cargo, rustc, sysroot) der Standard-Toolchain. Direkt die Programme der Toolchain statt der rustup-Huelle,
    damit im Projekt keine andere Toolchain angefordert werden kann und die Sandbox nur diesen Ordner braucht."""
    cargo = cargo_path()
    rustc = str(Path(cargo).with_name("rustc.exe" if IS_WIN else "rustc"))
    if not Path(rustc).is_file():
        rustc = shutil.which("rustc") or "rustc"
    try:
        r = subprocess.run([rustc, "--print", "sysroot"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, env=_base_env(), cwd=str(Path.home()))
        sysroot = Path(r.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        sysroot = None
    if sysroot and (sysroot / "bin" / Path(cargo).name).is_file():
        return str(sysroot / "bin" / Path(cargo).name), str(sysroot / "bin" / Path(rustc).name), sysroot
    return cargo, rustc, sysroot


def _base_env():
    """Minimale Umgebung ohne API-Keys. Proxy-Variablen bleiben, damit cargo fetch hinter einem Proxy laedt."""
    keep = ["PATH", "HOME", "LANG", "RUSTUP_HOME", "RUSTUP_TOOLCHAIN", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
            "https_proxy", "http_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "CARGO_HTTP_CAINFO"]
    if IS_WIN:
        keep += ["SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
                 "PROGRAMFILES", "ProgramFiles", "PROGRAMFILES(X86)", "ProgramFiles(x86)", "PROGRAMDATA", "ProgramData",
                 "COMSPEC", "PATHEXT", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "OS", "HOMEDRIVE", "HOMEPATH"]
    return {k: os.environ[k] for k in keep if k in os.environ}


def _slug(name):
    s = re.sub(r"[^a-z0-9_-]+", "-", str(name or "").lower()).strip("-")
    return s[:60] or "programm"


def _crate_files(src):
    """Quelldateien des Projekts: ohne Dotdateien/-ordner, target/, rust-toolchain*, Symlinks."""
    files, size = [], 0
    for f in sorted(src.rglob("*")):
        rel = f.relative_to(src)
        if f.is_symlink() or not f.is_file() or any(x.startswith(".") for x in rel.parts) or rel.parts[0] in SKIP_NAMES:
            continue
        size += f.stat().st_size
        files.append(rel)
        if len(files) > COPY_MAX_FILES or size > COPY_MAX_BYTES:
            raise T.ToolError(f"Projekt zu gross (max. {COPY_MAX_FILES} Dateien / {COPY_MAX_BYTES // 1048576} MB, ohne target/)")
    return files


def _sync(src, dst, files):
    """Kopie im Bauordner neu anlegen; copy2 behaelt die Zeitstempel, damit cargo nur Geaendertes neu baut."""
    if dst.exists():
        shutil.rmtree(dst)
    for rel in files:
        t = dst / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, t)


def _limits():
    import resource
    mem = CARGO_MEM_MB * 1024 * 1024
    for lim, val in ((resource.RLIMIT_AS, mem), (resource.RLIMIT_CPU, CARGO_TIMEOUT + 30), (resource.RLIMIT_CORE, 0)):
        try:
            resource.setrlimit(lim, (val, val))
        except (ValueError, OSError):
            pass


def _sandbox(build, home, sysroot):
    """bubblewrap: Bauordner beschreibbar unter /arbeit, Cargo-Cache unter /cargo, Toolchain nur lesbar, kein Netz."""
    cmd = T._sandbox_cmd(build / "crate", build)[:-1]  # ohne das abschliessende "--"
    i = cmd.index("--chdir")
    del cmd[i:i + 2]  # Arbeitsordner kommt unten (/arbeit/crate)
    if sysroot and not str(sysroot).startswith("/usr"):
        cmd += ["--ro-bind", str(sysroot), str(sysroot)]
    path = ":".join(x for x in (f"{sysroot}/bin" if sysroot else "", "/usr/local/bin:/usr/bin:/bin") if x)
    cmd += ["--bind", str(home), "/cargo", "--chdir", "/arbeit/crate", "--setenv", "CARGO_HOME", "/cargo",
            "--setenv", "CARGO_TARGET_DIR", "/arbeit/target", "--setenv", "PATH", path,
            "--setenv", "CARGO_BUILD_JOBS", CARGO_JOBS, "--setenv", "CARGO_TERM_COLOR", "never", "--"]
    return cmd


def _run(argv, cwd, env, stdin=None, timeout=CARGO_TIMEOUT, sandboxed=False):
    """Startet einen Befehl mit Zeitlimit; bei Ueberschreitung wird der ganze Prozessbaum beendet."""
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if IS_WIN else {"start_new_session": True}
    if sandboxed:
        kw["preexec_fn"] = _limits
    t0 = time.time()
    p = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, **kw)
    try:
        out, _ = p.communicate(input=str(stdin or "").encode()[:1_000_000], timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        if IS_WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            import signal
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
        out, _ = p.communicate()
        timed_out = True
    return p.returncode, (out or b"").decode("utf-8", "replace"), timed_out, time.time() - t0


def _tidy(text, build):
    """Fortschrittszeilen weg, Pfade des Bauordners kuerzen, damit Fehler gut lesbar bleiben."""
    for p in (str(build / "crate") + os.sep, str(build / "crate"), "/arbeit/crate/", "/arbeit/"):
        text = text.replace(p, "")
    lines = [ln for ln in text.splitlines() if not _NOISE.match(ln)]
    return "\n".join(lines).strip()


def _binaries(target, cargo_exe):
    rel = target / "release"
    if not rel.is_dir():
        return []
    out = []
    for f in sorted(rel.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        if IS_WIN and f.suffix.lower() == ".exe":
            out.append(f)
        elif not IS_WIN and not f.suffix and os.access(f, os.X_OK):
            out.append(f)
    return out


def rust_project(root, call):
    mode = sandbox_mode()
    if not mode:
        raise T.ToolError("Rust bauen ist auf diesem Server nicht eingerichtet (cargo fehlt, unter Linux bubblewrap fehlt, "
                          "unter Windows PCL_CARGO_UNSAFE=1 noetig, oder PCL_ALLOW_RUN=0/PCL_CARGO=0)")
    root = Path(root).resolve()
    op = str(call.get("op") or "test").lower().strip()
    if op not in OPS:
        raise T.ToolError("op: " + " | ".join(OPS))
    rel = str(call.get("dir") or call.get("path") or "").strip().strip("/") or "."
    try:
        src = T._inside(root, rel)
    except ValueError:
        raise T.ToolError("Pfad liegt ausserhalb des Projektordners")
    if src.is_file():
        src = src.parent
    if any(x.startswith(".") for x in src.relative_to(root).parts):
        raise T.ToolError("Versteckte Ordner sind nicht erlaubt")
    if not (src / "Cargo.toml").is_file():
        raise T.ToolError(f"In '{rel}' fehlt Cargo.toml. Erst mit write_code anlegen: {rel}/Cargo.toml und {rel}/src/main.rs")
    name = _slug(call.get("name") or (src.name if src != root else "programm"))
    files = _crate_files(src)
    base = root / ".rust"
    build, home = base / name, base / "cargo-home"
    build.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    cargo, rustc, sysroot = _toolchain()
    cargo_bin_dir = str(Path(cargo_path()).parent)
    args = [str(x)[:500] for x in (call.get("args") if isinstance(call.get("args"), list) else [])][:20]

    with _lock:
        _sync(src, build / "crate", files)
        crate = build / "crate"
        env = _base_env()
        env.update({"CARGO_HOME": str(home), "CARGO_TARGET_DIR": str(build / "target"), "CARGO_TERM_COLOR": "never",
                    "CARGO_BUILD_JOBS": CARGO_JOBS})
        env["PATH"] = os.pathsep.join(x for x in (str(sysroot / "bin") if sysroot else "", cargo_bin_dir, env.get("PATH", "")) if x)
        report = [f"Rust ({'abgeschottet' if mode == 'bwrap' else 'OHNE Sandbox, PCL_CARGO_UNSAFE=1'}), Projekt {rel}"]
        # 1. Abhaengigkeiten laden (Netz, kein Code wird ausgefuehrt)
        code, out, to, secs = _run([cargo, "fetch"], crate, env, timeout=min(CARGO_TIMEOUT, 600))
        if code != 0:
            return "\n".join(report + [f"FEHLER beim Laden der Abhaengigkeiten (cargo fetch, Exit {code}"
                                       f"{', Zeitlimit' if to else ''}):", T._clip(_tidy(out, build), 5000)])

        def cargo_step(sub, extra=(), stdin=None):
            argv = [cargo, *sub, "--release", "--offline", *extra]
            if mode == "bwrap":
                argv = _sandbox(build, home, sysroot) + [cargo, *sub, "--release", "--offline", *extra]
                return _run(argv, crate, _base_env(), stdin=stdin, sandboxed=True)
            return _run(argv, crate, env, stdin=stdin)

        def step_text(label, res):
            code, out, to, secs = res
            head = f"{label}: " + (f"ABGEBROCHEN nach {CARGO_TIMEOUT} s (Zeitlimit)" if to else
                                   ("OK" if code == 0 else f"FEHLER (Exit {code})")) + f", {secs:.0f} s"
            if code in (-9, 137) and not to:
                head += " (vermutlich RAM-Limit PCL_CARGO_MEM_MB erreicht)"
            return head + "\n" + (T._clip(_tidy(out, build), 6000) or "(keine Ausgabe)")

        if op == "build":
            res = cargo_step(["build"])
            report.append(step_text("cargo build --release", res))
            if res[0] == 0:
                bins = _binaries(build / "target", cargo)
                report.append("Programm(e) gebaut: " + (", ".join(b.name for b in bins) or "(nur Bibliothek)") +
                              ". Fertiges Paket mit op=package.")
        elif op == "run":
            res = cargo_step(["run"], ["--", *args] if args else (), call.get("stdin"))
            report.append(step_text("cargo run --release", res))
        else:  # test / package
            res = cargo_step(["test"])
            out = res[1]
            report.append(step_text("cargo test --release", res))
            counts = [int(n) for n in re.findall(r"running (\d+) tests?", out)]
            no_tests = res[0] == 0 and sum(counts) == 0
            if no_tests:
                report.append("WARNUNG: Es gibt keine Tests. Schreibe #[test]-Funktionen (z. B. in src/main.rs unter "
                              "#[cfg(test)] mod tests) und teste erneut.")
            if op == "package":
                if res[0] != 0:
                    report.append("KEIN PAKET: Erst die Fehler beheben, dann erneut op=package.")
                else:
                    b = cargo_step(["build"])
                    report.append(step_text("cargo build --release", b))
                    if b[0] == 0:
                        report.append(_package(root, src, crate, build, files, name, rel, out, no_tests, rustc))
        if (crate / "Cargo.lock").is_file() and not (src / "Cargo.lock").exists():
            shutil.copy2(crate / "Cargo.lock", src / "Cargo.lock")  # feste Versionen fuers naechste Mal und fuer den Besitzer
    return "\n".join(report)


def _package(root, src, crate, build, files, name, rel, test_out, no_tests, rustc):
    bins = _binaries(build / "target", None)
    try:
        host = subprocess.run([rustc, "-vV"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=60, env=_base_env()).stdout
        host = next((ln.split(":", 1)[1].strip() for ln in host.splitlines() if ln.startswith("host:")), "unbekannt")
    except (OSError, subprocess.TimeoutExpired):
        host = "unbekannt"
    exe = ", ".join(b.name for b in bins) or "(keins, nur Bibliothek)"
    liesmich = (f"{name}\n{'=' * len(name)}\n\n"
                f"Gebaut und getestet von PaperclipLite am {time.strftime('%d.%m.%Y %H:%M')}.\n"
                f"Programm in programm/: {exe}\nFuer System: {host}\n"
                + ("Tests: keine vorhanden.\n" if no_tests else "Tests: alle bestanden (siehe TESTBERICHT.txt).\n") +
                "\nStarten: das Programm in programm/ ausfuehren (Windows: Doppelklick bzw. in PowerShell .\\programm\\name.exe).\n"
                "Laeuft es auf deinem Rechner nicht (anderes System), selbst bauen: im Ordner quelle/\n"
                "  cargo build --release   -> target/release/\n  cargo test             -> Tests\n"
                "Rust installieren: https://rustup.rs\n")
    out_dir = root / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{name}.zip"
    lock = crate / "Cargo.lock"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{name}/LIESMICH.txt", liesmich)
        z.writestr(f"{name}/TESTBERICHT.txt", _tidy(test_out, build) or "(keine Ausgabe)")
        for f in files:
            z.write(src / f, f"{name}/quelle/{f.as_posix()}")
        if lock.is_file() and Path("Cargo.lock") not in files:
            z.write(lock, f"{name}/quelle/Cargo.lock")
        for b in bins:
            zi = zipfile.ZipInfo(f"{name}/programm/{b.name}", time.localtime(b.stat().st_mtime)[:6])
            zi.external_attr = 0o755 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, b.read_bytes())
    size = target.stat().st_size
    return (f"PAKET FERTIG: output/{name}.zip ({size // 1024 or 1} KB) mit Quelltext, Programm ({exe}, fuer {host}), "
            f"TESTBERICHT.txt und LIESMICH.txt.")
