# -*- coding: utf-8 -*-
"""会话临时文件清理器 —— 两步法第一步：删除。

删除行为**因环境而异**（有删除拦截层的环境会进入回收站；原生 Windows 直接删除）：
先跑一次 ``probe_env.py`` 校准本环境，再决定是否需要第二步 purge（若删除进回收站，
须配合 ``purge_recycle.py`` 按路径精确清除对应条目才真正释放空间）。

用法（先 dry-run 盘点，再执行删除）::

    python cleanup.py --dry-run  "<目标>"                          # 只盘点：文件数/大小/明细
    python cleanup.py            "<目标>"                          # 删除
    python cleanup.py --recycle  "<某文件 带空格.txt>"              # 尽力走回收站（用于个人文件）
    python cleanup.py --exclude "*.keep" --exclude "重要*"  "<目标>"   # 排除模式（可多次）
    python cleanup.py --files-only  "<目标>"                       # 只删文件，保留目录骨架

（路径示例：Windows 下 ``C:/tmp/_my_work``、``D:\\scratch`` 或 Git Bash 风格 ``/c/tmp/_my_work`` 均可。）

特性与安全设计：
  - 目录自底向上删除；**遍历与删除均加 \\\\?\\ 长路径前缀**
    （长路径安全：不加前缀时 os.walk 在 ~260 字符处会**静默截断**、漏掉深层文件）
  - 受保护路径（盘根、用户主目录、系统目录、.workbuddy-ai 等）自动拒删（可用 --force 强制，慎用）
  - 被占用/锁定文件跳过并报告；整个脚本**幂等**，可重复运行直至清理干净
  - 文件数较多时提示"批量删除确认"注意事项（阈值因环境而异，务必前台运行）
"""
import argparse
import fnmatch
import os
import re
import sys

PREFIX = '\\\\?\\'

# 受保护路径集合（归一化：小写、反斜杠、无尾分隔符）
# 通用化（2026-10-28）：系统目录从环境变量动态获取（SystemRoot / ProgramFiles /
# ProgramFiles(x86) / ProgramData / 用户目录父级），不再写死盘符；另保留 C: 标准
# 位置兜底。盘根（如 "e:"）由 is_protected() 的长度判断单独覆盖（全盘符通用）。
def _protected_set():
    s = set()
    for _v in (os.environ.get('SystemRoot'), os.environ.get('ProgramFiles'),
               os.environ.get('ProgramFiles(x86)'), os.environ.get('ProgramData')):
        if _v:
            s.add(os.path.normpath(_v).rstrip('\\').lower())
    _pub = os.environ.get('PUBLIC')        # C:\Users\Public → 取父级 C:\Users
    if _pub:
        s.add(os.path.normpath(os.path.dirname(_pub)).rstrip('\\').lower())
    s |= {'c:\\windows', 'c:\\program files', 'c:\\program files (x86)',
          'c:\\programdata', 'c:\\users'}  # 标准位置兜底
    return s


PROTECTED_EXACT = _protected_set()
# 包含这些路径片段则保护（可按需增删；默认保护 WorkBuddy 系技能/项目记忆目录）
PROTECTED_PARTS = (
    '\\.workbuddy-ai',
)


def unify(raw):
    r"""把 Git Bash 风格路径转成 Windows 路径；去掉 ``\\?\`` 前缀。

    ``/e/tmp/x`` -> ``E:\tmp\x``；``\\?\E:\tmp\x`` -> ``E:\tmp\x``；其余原样返回。
    这样在 Git Bash 里两种写法都能直接用。
    """
    p = str(raw)
    if p.startswith(PREFIX):
        p = p[len(PREFIX):]
    m = re.match(r'^/([A-Za-z])(/.*)?$', p)
    if m:
        p = f"{m.group(1).upper()}:{m.group(2) or '/'}"
    return p


def norm(p):
    return os.path.abspath(unify(p)).replace('/', '\\').rstrip('\\').lower()


def lp(p):
    r"""加 ``\\?\`` 长路径前缀（已带前缀则原样返回）。"""
    p = os.path.abspath(unify(p))
    if p.startswith(PREFIX):
        return p
    return PREFIX + p


def is_protected(raw):
    r"""返回 (是否受保护, 原因)。raw 为原始输入路径。"""
    n = norm(raw)
    if len(n) <= 3 and n.endswith(':'):  # 形如 e: 的盘根
        return True, '盘符根目录'
    if n in PROTECTED_EXACT:
        return True, '系统/关键目录'
    home = norm(os.path.expanduser('~'))
    if n == home:
        return True, '用户主目录'
    for part in PROTECTED_PARTS:
        if part in n:
            return True, f'受保护目录（含 {part}）'
    return False, ''


def collect(targets, excludes):
    """展开为 (files, dirs)。目录按自底向上顺序收集。

    遍历用 \\\\?\\ 前缀（长路径安全）；存入清单时**剥掉前缀**，
    删除时再统一加前缀，避免双重前缀。
    """
    files, dirs = [], []
    missing = []
    for t in targets:
        ap = os.path.abspath(unify(t))
        wap = lp(ap)
        if os.path.isfile(wap):
            name = os.path.basename(ap)
            if any(fnmatch.fnmatch(name, pat) for pat in excludes):
                continue
            files.append(ap)
        elif os.path.isdir(wap):
            for root, ds, fs in os.walk(wap, topdown=False):
                for f in fs:
                    p = os.path.join(root, f)
                    if p.startswith(PREFIX):
                        p = p[len(PREFIX):]
                    if any(fnmatch.fnmatch(os.path.basename(p), pat) for pat in excludes):
                        continue
                    files.append(p)
                for d in ds:
                    q = os.path.join(root, d)
                    if q.startswith(PREFIX):
                        q = q[len(PREFIX):]
                    dirs.append(q)
            dirs.append(ap)
        else:
            missing.append(t)
    return files, dirs, missing


def size_of(paths):
    total = 0
    for p in paths:
        try:
            total += os.path.getsize(lp(p))
        except OSError:
            pass
    return total


def fmt_size(n):
    """人类可读的大小（B/KB/MB/GB）。"""
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f"{n} B" if unit == 'B' else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} GB"


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    ap = argparse.ArgumentParser(
        description='会话临时文件清理器（删除 / dry-run 盘点；真释放需第二步 purge_recycle.py）',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('targets', nargs='+', help='要清理的文件或目录（可多个）')
    ap.add_argument('--dry-run', action='store_true', help='只盘点，不删除')
    ap.add_argument('--recycle', action='store_true',
                    help='尽力走回收站（用于个人文件）；是否真正进入回收站取决于本环境的删除策略（用 probe_env.py 校准）')
    ap.add_argument('--exclude', action='append', default=[],
                    help='排除的文件名模式（fnmatch，可重复），仅作用于文件')
    ap.add_argument('--files-only', action='store_true', help='只删文件，保留目录骨架')
    ap.add_argument('--force', action='store_true', help='允许清理受保护路径（慎用！）')
    args = ap.parse_args(argv)

    # 保护检查
    blocked = []
    work = []
    for t in args.targets:
        prot, why = is_protected(t)
        if prot and not args.force:
            blocked.append((t, why))
        else:
            work.append(t)

    for t, why in blocked:
        print(f"[拒绝] 受保护目标（{why}）：{os.path.abspath(unify(t))}   —— 如确需清理，请人工确认后加 --force")
    if not work:
        print('无可执行目标。')
        return 2 if blocked else 0

    files, dirs, missing = collect(work, args.exclude)
    total = size_of(files)

    print(f"目标：{len(work)} 个；文件 {len(files)} 个；目录 {len(dirs)} 个；合计约 {fmt_size(total)}")
    for t in missing:
        print(f"  [跳过] 不存在：{os.path.abspath(unify(t))}")

    if args.dry_run:
        print('\n--- 明细（最多显示 80 条）---')
        for p in files[:80]:
            try:
                s = os.path.getsize(lp(p))
            except OSError:
                s = 0
            print(f"  {fmt_size(s):>10}  {p}")
        if len(files) > 80:
            print(f"  …… 其余 {len(files)-80} 个文件略")
        print('\n[dry-run] 未执行任何删除。确认无误后去掉 --dry-run 重跑。')
        return 0

    if len(files) > 50:
        print(f"⚠ 本次将删除 {len(files)} 个文件：部分环境设有「批量删除确认」（阈值因环境而异，曾见 50），"
              f"请在**前台**运行并等待批准后继续；若中途中断，直接重跑本脚本即可（幂等）。")

    ok_f, fail_f = 0, []
    for p in files:
        try:
            if args.recycle:
                os.remove(p)
            else:
                os.remove(PREFIX + p)
            ok_f += 1
        except FileNotFoundError:
            ok_f += 1
        except OSError as e:
            fail_f.append((p, str(e)))

    ok_d, fail_d = 0, []
    if not args.files_only:
        for d in dirs:
            try:
                if args.recycle:
                    os.rmdir(d)
                else:
                    os.rmdir(PREFIX + d)
                ok_d += 1
            except FileNotFoundError:
                ok_d += 1
            except OSError as e:
                fail_d.append((d, str(e)))

    print(f"\n完成：文件 {ok_f}/{len(files)}；目录 {ok_d}/{len(dirs)}"
          + (f"；已处理约 {fmt_size(total)}（若本环境删除进回收站，需运行 purge_recycle.py 后真正释放）"
             if not args.recycle else "（已尽力走回收站；空间是否释放取决于本环境的删除策略）"))
    for p, e in fail_f[:20]:
        print(f"  [文件失败] {p} -> {e}")
    for p, e in fail_d[:20]:
        print(f"  [目录失败] {p} -> {e}")
    if fail_f or fail_d:
        nonempty = sum(1 for _, e in fail_d if '145' in e or '不是空' in e)
        if nonempty and nonempty == len(fail_d) and not fail_f:
            print("提示：目录非空失败——多为 --exclude 保留了文件所致；确认无需保留后去掉排除重跑即可。")
        else:
            print("提示：失败项多为文件被占用（关闭相关编辑器/进程后重跑本脚本即可）；"
                  "若为“目录不是空的”，则是 --exclude 保留了文件。")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
