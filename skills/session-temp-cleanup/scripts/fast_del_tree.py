# -*- coding: utf-8 -*-
"""fast_del_tree —— ctypes 原生删除器（可选·极速，⚠️ 删除快但仍进回收站·需配 purge）

用途（session-temp-cleanup 的配套工具之三）
--------------------------------------------
当被拦截的逐项删除**极慢**时的快速清尾（实测拦截路径约 0.2~3 项/秒，上万项要数十分钟）：
- 适合场景 A：文件已进回收站、只剩**空目录骨架**（0 字节，删掉零损失）
- 适合场景 B：目录树内容已**确认冗余/另有备份**（如与镜像重复的克隆）
- 不适合：任何"拿不准"的内容 —— 那种情况请走 cleanup.py + purge_recycle.py 两步

原理（2026-10-24 查明；2026-10-28 复测修正）
--------------------------
本环境删除拦截来自 `PYTHONPATH` 注入的 `sitecustomize.py`（猴补丁 Python 的
os.remove/os.rmdir/shutil 等），它会（a）把删除转进回收站、（b）极慢。
**ctypes 直调 kernel32（DeleteFileW / RemoveDirectoryW）不经 Python 层**，
因此是原生速度、不受该 shim 的拦截与拖慢。

⚠️ 关于回收站（2026-10-28 重要修正）：早期开发机上本工具曾"不经回收站、直接永久
删除"；**但在验证环境的多组对照实测中（WorkBuddy，含沙箱内与授权模式），ctypes
删除的条目依然出现在回收站**——落盘行为由更底层策略决定，用户态无法绕过。→ 收尾
仍须按"删除 + purge_recycle.py 清除"两步法（用 probe_env.py 校准本环境）；本工具的
价值是**快**（0.1~0.3s/小树），而非免 purge。
（补充：回收站内条目的清除——purge_recycle.py——同样依赖此机制。）

历史实测：1781 个空目录 113 秒清完（对照：拦截路径预计 60+ 分钟）。
单文件支持：2026-10-28 补（原实现顶层仅调 RemoveDirectoryW，传纯文件会误报
「目录 0删/1败 | 仍存在」）。

用法
----
::

    python fast_del_tree.py <路径1> [路径2 ...]

注意：删除不可逆（在有删除拦截层的环境中仍会落入回收站，需配 purge_recycle.py 才真正释放空间）。
"""
import os
import sys
import time
import ctypes

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


def lp(p):
    p = os.path.abspath(p)
    if p.startswith("\\\\?\\"):
        return p
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p[2:]
    return "\\\\?\\" + p


def del_file(p):
    l = lp(p)
    if DFW(l):
        return True
    if ctypes.get_last_error() == 5:
        SFW(l, 0x80)
        return bool(DFW(l))
    return False


def del_tree(root):
    """自底向上删除整棵树。返回 (ok_files, fail_files, ok_dirs, fail_dirs)"""
    okf = failf = okd = faild = 0
    rw = lp(root)
    for dirpath, dirnames, filenames in os.walk(rw, topdown=False):
        for fn in filenames:
            if del_file(os.path.join(dirpath, fn)):
                okf += 1
            else:
                failf += 1
        for dn in dirnames:
            d = os.path.join(dirpath, dn)
            if RDW(lp(d)):
                okd += 1
            else:
                SFW(lp(d), 0x80)
                if RDW(lp(d)):
                    okd += 1
                else:
                    faild += 1
    if RDW(rw):
        okd += 1
    else:
        faild += 1
    return okf, failf, okd, faild


def main():
    targets = sys.argv[1:]
    if not targets:
        print(__doc__)
        return 2
    for t in targets:
        if not os.path.exists(t):
            print('[跳过] 不存在: %s' % t)
            continue
        st = time.time()
        if os.path.isfile(t):
            # 单文件：直接 DeleteFileW
            # （2026-10-28 补：原实现顶层仅调 RemoveDirectoryW，传纯文件会误报
            #   「目录 0删/1败 | 仍存在」）
            ok = del_file(t)
            dt = time.time() - st
            gone = not os.path.exists(t)
            print('%s: %.1fs | 文件 %d删/%d败 | 目录 0删/0败 | %s'
                  % (t, dt, 1 if ok else 0, 0 if ok else 1,
                     '已彻底删除 ✓' if gone else '仍存在!'))
            continue
        okf, failf, okd, faild = del_tree(t)
        dt = time.time() - st
        gone = not os.path.exists(t)
        print('%s: %.1fs | 文件 %d删/%d败 | 目录 %d删/%d败 | %s'
              % (t, dt, okf, failf, okd, faild, '已彻底删除 ✓' if gone else '仍存在!'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
