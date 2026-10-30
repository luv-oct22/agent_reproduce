#!/usr/bin/env python3
"""Back up, validate and install Docker daemon proxy settings. Run via rlaunch.sh."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def configure(proxy, bypass, path=Path("/etc/docker/daemon.json")):
    parsed = urlparse(proxy)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("A valid HTTP/HTTPS proxy URL is required; configuration unchanged.")
    config = json.loads(path.read_text()) if path.exists() else {}
    config.setdefault("proxies", {}).update({
        "http-proxy": proxy,
        "https-proxy": proxy,
        "no-proxy": bypass,
    })
    if "registry-mirrors" in config:
        config["registry-mirrors"] = [
            url for url in config["registry-mirrors"]
            if urlparse(url).hostname != "docker.1ms.run"
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".daemon-proxy-", suffix=".json", dir=path.parent)
    candidate = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(config, stream, indent=2)
            stream.write("\n")
        subprocess.run(["dockerd", "--validate", "--config-file=" + str(candidate)], check=True)
        if path.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup = path.with_name("daemon.json.bak." + stamp)
            shutil.copy2(path, backup)
            backup.chmod(0o600)
            print("Backup:", backup)
        os.replace(candidate, path)
    finally:
        candidate.unlink(missing_ok=True)
    print("Docker proxy configuration saved and validated.")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: docker_proxy_setup.py PROXY_URL NO_PROXY")
    try:
        configure(sys.argv[1], sys.argv[2])
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
