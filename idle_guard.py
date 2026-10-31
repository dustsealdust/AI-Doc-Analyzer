# -*- coding: utf-8 -*-
"""端口守护进程（由 启动.vbs 以 pythonw 无窗口方式拉起）。

作用：所有浏览器标签都关掉 N 秒后，自动结束 Streamlit 进程，
      避免后台一直挂着 python 占内存。

参数：python watchdog.py <port> <streamlit_pid>
环境：WATCHDOG_GRACE 宽限秒数（默认 60），仅测试时才需要调小
"""
import os
import pathlib
import subprocess
import sys
import time


def client_connections(port: int) -> int:
    """统计有多少条已建立的连接是连到这个端口的（本地端口 == port 即服务端连接）。"""
    try:
        out = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True,
            encoding="gbk", errors="replace",
        ).stdout
    except Exception:
        return -1

    count = 0
    for line in out.splitlines():
        if "ESTABLISHED" not in line or f":{port}" not in line:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[1]
        if local.rsplit(":", 1)[-1] == str(port):
            count += 1
    return count


def process_alive(pid: int) -> bool:
    if not pid:
        return True
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True,
            encoding="gbk", errors="replace",
        ).stdout
    except Exception:
        return True
    return str(pid) in out


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8501
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    grace = float(os.environ.get("WATCHDOG_GRACE", "60"))
    interval = 3.0

    idle_since = None
    seen_client = False
    started_at = time.time()

    while True:
        if not process_alive(target):
            return 0                      # Streamlit 已经没了，守护进程也退出

        count = client_connections(port)

        if count > 0:
            seen_client = True
            idle_since = None
        elif count == 0:
            if seen_client:
                if idle_since is None:
                    idle_since = time.time()
                elif time.time() - idle_since >= grace:
                    break                 # 浏览器全关，宽限期到，收工
            elif time.time() - started_at > 180:
                break                     # 起来就没被访问过，别赖着
        # count == -1（netstat 失败）时什么都不做，下一轮再试

        time.sleep(interval)

    if target:
        subprocess.run(["taskkill", "/PID", str(target), "/T", "/F"],
                       capture_output=True)

    # 顺手把 pid 文件清掉（只清自己那个，别误删新实例的）
    try:
        pid_file = pathlib.Path(".streamlit.pid")
        if pid_file.exists() and pid_file.read_text(encoding="utf-8").strip() == str(target):
            pid_file.unlink()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())