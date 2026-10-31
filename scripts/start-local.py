#!/usr/bin/env python3
"""Start the project locally, safely reusing its existing listeners."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / '.local' / 'logs'


def output(args):
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


def listener(port):
    ids = output(['/usr/sbin/lsof', '-t', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN'])
    return sorted(set(int(pid) for pid in ids.split()))


def owned(pid, directory, marker):
    cwd = output(['/usr/sbin/lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'])
    command = output(['/bin/ps', '-p', str(pid), '-o', 'command='])
    return f'n{directory}' in cwd.splitlines() and marker in command


def healthy(url, backend=False):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read()
            return response.status == 200 and (not backend or json.loads(body).get('status') == 'ok')
    except Exception:
        return False


def ensure(name, port, directory, marker, command, url, backend=False):
    pids = listener(port)
    if pids:
        if not all(owned(pid, directory, marker) for pid in pids):
            raise RuntimeError(f'端口 {port} 被其他程序占用（PID {pids}）。请先处理端口冲突，再启动。')
        if not healthy(url, backend):
            raise RuntimeError(f'{name} 已运行但健康检查失败（PID {pids}）。请检查服务和日志。')
        print(f'{name}：复用 PID {", ".join(map(str, pids))}', flush=True)
        return
    logfile = LOGS / f'{name}.log'
    with logfile.open('ab') as stream:
        proc = subprocess.Popen(command, cwd=directory, stdin=subprocess.DEVNULL,
                                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(120):
        if proc.poll() is not None:
            raise RuntimeError(f'{name} 启动退出，请查看 {logfile}')
        if healthy(url, backend):
            print(f'{name}：启动成功，PID {proc.pid}', flush=True)
            return
        time.sleep(0.25)
    raise RuntimeError(f'{name} 30 秒内未就绪，请查看 {logfile}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-open', action='store_true', help='只启动，不打开浏览器')
    args = parser.parse_args()
    LOGS.mkdir(parents=True, exist_ok=True)
    # Serialize double clicks so they cannot create duplicate services.
    with (LOGS.parent / 'startup.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        node = shutil.which('node')
        if not node:
            candidates = sorted((Path.home() / '.nvm/versions/node').glob('*/bin/node'),
                                key=lambda p: p.stat().st_mtime, reverse=True)
            node = str(candidates[0]) if candidates else None
        python = ROOT / 'backend/.venv/bin/python'
        vite = ROOT / 'web/node_modules/vite/bin/vite.js'
        if not node or not python.exists() or not vite.exists():
            raise RuntimeError('缺少 Node.js 或项目依赖，请按 backend/README.md 与 web/README.md 完成首次安装。')
        ensure('backend', 8011, ROOT / 'backend', 'uvicorn',
               [str(python), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8011'],
               'http://127.0.0.1:8011/health', True)
        ensure('web', 4173, ROOT / 'web', 'vite',
               [node, str(vite), '--host', '127.0.0.1', '--port', '4173', '--strictPort'],
               'http://127.0.0.1:4173/')
        if not healthy('http://127.0.0.1:4173/health', True):
            raise RuntimeError('前端代理健康检查失败，请检查 web/vite.config.js。')
        print(f'网站：http://127.0.0.1:4173/\n健康检查：通过\n启动日志目录：{LOGS}', flush=True)
        if not args.no_open:
            subprocess.run(['/usr/bin/open', 'http://127.0.0.1:4173/'], check=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'启动失败：{exc}', file=sys.stderr)
        sys.exit(1)
