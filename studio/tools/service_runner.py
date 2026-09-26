# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Keep preview running across transient failures; honor explicit stop requests."""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'team-preview'


def should_restart(exit_code, stop_requested):
    return exit_code != 0 and not stop_requested


def main():
    DATA.mkdir(exist_ok=True)
    stop = DATA / 'stop.request'
    stop.unlink(missing_ok=True)
    with (DATA / 'supervisor.log').open('ab', buffering=0) as log:
        while True:
            log.write((time.strftime('%Y-%m-%d %H:%M:%S') + ' Starting preview\n').encode())
            result = subprocess.run(
                [sys.executable, '-X', 'utf8', str(ROOT / 'tools/team_preview.py')],
                cwd=ROOT, stdout=log, stderr=log,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if not should_restart(result.returncode, stop.exists()):
                return result.returncode if not stop.exists() else 0
            log.write(('Preview exited ' + str(result.returncode) + '; retry in 10 seconds\n').encode())
            for _ in range(20):
                if stop.exists():
                    return 0
                time.sleep(.5)


if __name__ == '__main__':
    raise SystemExit(main())
