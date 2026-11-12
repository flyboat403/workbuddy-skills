# -*- coding: utf-8 -*-
r"""回收站精确清除 —— cleanup.py 的配套第二步（真正释放磁盘空间）。

背景
----
若本环境的删除会进入回收站（如 WorkBuddy / CodeBuddy 系的安全删除层；用
``probe_env.py`` 校准本环境），``cleanup.py`` 删除后文件会留在 ``X:\$Recycle.Bin`` 中、
空间不释放。本脚本扫描回收站，把「原始路径匹配目标」的条目（配对 ``$R`` 内容 +
``$I`` 元数据）永久删除，真正释放空间。

用法
----
::

    python purge_recycle.py  <目标路径...>                    # dry-run 盘点（默认）
    python purge_recycle.py --execute <目标路径...>           # 执行清除（一般沙箱内即可；遇权限拦截改授权模式）
    python purge_recycle.py --since 2026-10-24 --execute <目标路径...>
                                                              # 只清该日期(本地)起删除的条目

说明
----
- 匹配规则：回收站条目的「原始完整路径」等于目标、或位于目标之下（大小写不敏感，
  带路径边界校验）；``--since`` 可再按删除日期过滤。
- 安全：默认 dry-run；盘根 / 系统目录 / 用户主目录 直接拒处理。
- 幂等：可重复运行；已清除的条目不会再出现。
"""
import os
import sys
import time
import struct
import ctypes
import datetime

I = 1024 * 1024

def current_user_sid():
    """获取当前用户 SID（$Recycle.Bin 根无法列举时用于兜底直连）。

    通用化（2026-10-28）：不再写死某台机器的 SID；优先 ``whoami /user`` 解析；
    也可用环境变量 SESSION_CLEANUP_FALLBACK_SID 额外追加（多用户/异常环境备用）。
    """
    try:
        import subprocess
        r = subprocess.run(["whoami", "/user"], capture_output=True, text=True,
                           timeout=10, errors="replace")
        for tok in (r.stdout or "").replace("\r", " ").replace("\n", " ").split():
            if tok.startswith("S-1-5-") and tok.count("-") >= 4:
                return tok
    except Exception:
        pass
    return ""


FALLBACK_SIDS = [s for s in (current_user_sid(),
                             os.environ.get("SESSION_CLEANUP_FALLBACK_SID", "").strip())
                 if s]

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
DFW = k32.DeleteFileW
DFW.argtypes = [ctypes.c_wchar_p]
DFW.restype = ctypes.c_int
RDW = k32.RemoveDirectoryW
RDW.argtypes = [ctypes.c_wchar_p]
RDW.restype = ctypes.c_int
SFW = k32.SetFileAttributesW
SFW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
SFW.restype = ctypes.c_int
GAW = k32.GetFileAttributesW
GAW.argtypes = [ctypes.c_wchar_p]
GAW.restype = ctypes.c_uint32


def lp(p):
    """长路径前缀。"""
    p = os.path.abspath(p)
    if p.startswith("\\\\?\\"):
        return p
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p[2:]
    return "\\\\?\\" + p


def free(v):
    f = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p(v), None, None, ctypes.pointer(f))
    return f.value


def del_file(p):
    l = lp(p)
    if DFW(l):
        return True
    if ctypes.get_last_error() == 5:
        SFW(l, 0x80)  # 清只读属性后重试
        if DFW(l):
            return True
    return False


def del_tree(root):
    ok = True
    rw = lp(root)
    for dirpath, dirnames, filenames in os.walk(rw, topdown=False):
        for fn in filenames:
            if not del_file(os.path.join(dirpath, fn)):
                ok = False
        for dn in dirnames:
            d = os.path.join(dirpath, dn)
            if not RDW(lp(d)):
                SFW(lp(d), 0x80)
                if not RDW(lp(d)):
                    ok = False
    if not RDW(rw):
        ok = False
    return ok


def parse_i(path):
    """解析 $I 元数据：返回 (size, datetime(UTC), 原始路径)。"""
    try:
        with open(path, "rb") as f:
            d = f.read()
        if len(d) < 28:
            return None
        size = struct.unpack("<Q", d[8:16])[0]
        ft = struct.unpack("<Q", d[16:24])[0]
        namelen = struct.unpack("<I", d[24:28])[0]
        name = d[28:28 + namelen * 2].decode("utf-16-le", errors="replace").rstrip("\x00")
        try:
            t = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ft // 10)
        except Exception:
            t = None
        return size, t, name
    except Exception:
        return None


def to_local(dt_utc):
    if not dt_utc:
        return None
    try:
        ts = (dt_utc - datetime.datetime(1970, 1, 1)).total_seconds()
        return datetime.datetime.fromtimestamp(ts)
    except Exception:
        return None


def norm_target(raw):
    """归一化目标路径（支持 /e/tmp/x、E:/tmp/x、\\?\\E:\\tmp\\x）。返回小写、去尾斜杠。"""
    p = raw.strip().strip('"')
    if p.startswith("\\\\?\\"):
        p = p[4:]
    if len(p) >= 3 and p[1] == ":" and p[2] in "\\/":
        p = p[0].upper() + ":\\" + p[3:].replace("/", "\\")
    elif p.startswith("/") and len(p) >= 3 and p[2] == "/" and p[1].isalpha():
        p = p[1].upper() + ":\\" + p[3:].replace("/", "\\")
    else:
        p = os.path.abspath(p)
    return os.path.normpath(p).rstrip("\\").lower()


def denied(t):
    """危险目标（盘根/系统/主目录）拒绝处理。

    通用化（2026-10-28）：盘根覆盖全部盘符；系统目录从环境变量动态获取
    （SystemRoot / ProgramFiles / ProgramFiles(x86) / ProgramData），另保留
    C: 标准位置兜底；主目录用 ``expanduser("~")``。
    """
    home = os.path.normpath(os.path.expanduser("~")).lower()
    deny = set()
    for d in "abcdefghijklmnopqrstuvwxyz":
        deny.add(d + ":")
    for v in (os.environ.get("SystemRoot"), os.environ.get("ProgramFiles"),
              os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramData")):
        if v:
            deny.add(os.path.normpath(v).rstrip("\\").lower())
    deny |= {"c:\\windows", "c:\\program files", "c:\\program files (x86)",
             "c:\\programdata"}
    if home:
        deny.add(home)
    return t in deny


def sids_for_drive(drive):
    """列出某盘 $Recycle.Bin 下的 SID；列举失败时兜底。"""
    root = drive + "\\$Recycle.Bin"
    sids = set()
    try:
        for n in os.listdir(root):
            if n.startswith("S-1-5-"):
                sids.add(n)
    except Exception:
        pass
    for s in FALLBACK_SIDS:
        sids.add(s)
    return sorted(sids)


def scan(targets, since_utc=None):
    out = []
    drives = sorted({t[0:2].upper() for t in targets if len(t) >= 2 and t[1] == ":"})
    for drive in drives:
        for sid in sids_for_drive(drive):
            sd = os.path.join(drive + "\\$Recycle.Bin", sid)
            try:
                names = os.listdir(sd)
            except Exception:
                continue
            for nm in names:
                if not nm.startswith("$I"):
                    continue
                ip = os.path.join(sd, nm)
                info = parse_i(ip)
                if not info:
                    continue
                size, t, orig = info
                if since_utc and t and t < since_utc:
                    continue
                low = orig.lower().replace("/", "\\").rstrip("\\")
                for tt in targets:
                    if low == tt or low.startswith(tt + "\\"):
                        out.append({"i": ip, "r": os.path.join(sd, "$R" + nm[2:]),
                                    "size": size, "t": t, "orig": orig, "target": tt})
                        break
    return out


def main(argv=None):
    args = list(argv if argv is not None else sys.argv[1:])
    execute = "--execute" in args
    since_utc = None
    if "--since" in args:
        i = args.index("--since")
        try:
            d = datetime.datetime.strptime(args[i + 1], "%Y-%m-%d")
            offset = -time.timezone  # 本地相对 UTC 的偏移（秒）
            since_utc = d - datetime.timedelta(seconds=offset)
        except Exception:
            print("--since 需要 YYYY-MM-DD 格式"); return 2
        del args[i:i + 2]
    args = [a for a in args if not a.startswith("--")]

    if not args:
        print(__doc__)
        return 2

    raw_targets = args
    targets, refused = [], []
    for r in raw_targets:
        t = norm_target(r)
        if denied(t) or len(t) <= 3:
            refused.append(r)
        else:
            targets.append(t)
    for r in refused:
        print("[拒绝] 危险/过宽目标：%s" % r)
    if not targets:
        return 2

    print("目标 %d 个：%s" % (len(targets), ", ".join(targets)))
    entries = scan(targets, since_utc)
    total = sum(e["size"] for e in entries)
    print("== 回收站候选：%d 条 / %.2f MB ==" % (len(entries), total / I))

    shown = 0
    for e in sorted(entries, key=lambda x: -x["size"]):
        if shown >= 60:
            print("  …… 其余 %d 条略" % (len(entries) - shown))
            break
        lt = to_local(e["t"])
        ts = lt.strftime("%m-%d %H:%M") if lt else "?"
        print("  %11.2f KB  [%s]  %s" % (e["size"] / 1024, ts, e["orig"]))
        shown += 1

    if not entries:
        print("（无匹配条目——可能尚未删除、或已被清除）")
        return 0

    if not execute:
        print("DRY-RUN only. 确认后加 --execute 执行（一般沙箱内即可；如遇权限拦截改用授权模式）。")
        return 0

    print("== EXECUTING ==")
    drives = sorted({t[0:2].upper() for t in targets if len(t) >= 2 and t[1] == ":"})
    fb = {d: free(d + "\\") for d in drives}
    purged, pfail = 0, []
    for e in entries:
        attr = GAW(lp(e["r"]))
        is_dir = attr != 0xFFFFFFFF and bool(attr & 0x10)
        if is_dir:
            del_tree(e["r"])
        elif os.path.lexists(e["r"]):
            del_file(e["r"])
        if os.path.lexists(e["i"]):
            del_file(e["i"])
        if os.path.lexists(e["r"]) or os.path.lexists(e["i"]):
            pfail.append(e["orig"])
        else:
            purged += e["size"]
    time.sleep(2)
    print("== RESULT ==")
    print("purged: %d/%d 条, %.2f MB" % (len(entries) - len(pfail), len(entries), purged / I))
    for d in drives:
        fa = free(d + "\\")
        print("   %s free delta: %+.1f MB" % (d, (fa - fb[d]) / I))
    if pfail:
        print("== failures (%d) ==" % len(pfail))
        for o in pfail[:20]:
            print("   FAIL", o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
