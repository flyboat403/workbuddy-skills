# -*- coding: utf-8 -*-
r"""scan_venvs.py —— Python 虚拟环境只读盘点器（session-temp-cleanup 配套·只读）

用途
----
清理"不再使用的 venv / conda 环境"之前先做全机盘点：列出 大小 / 文件数 / 最后改动 /
Python 版本 / 项目线索，供人工判定哪些环境确实闲置，再交给 cleanup.py（两步法）或
fast_del_tree.py 清理。

⚠️ 本脚本**只读**：不删除、不移动、不修改任何文件，可随时安全运行。

识别标记
--------
- venv / virtualenv：目录含 ``pyvenv.cfg``（静态解析 version / home，不执行环境内解释器）
- conda 环境：目录含 ``conda-meta\`` 子目录（版本自 ``conda-meta\python-*.json`` 文件名读取）

遍历与剪枝规则
--------------
- 不深入：$Recycle.Bin、System Volume Information、node_modules、.git，以及**盘根**的系统
  目录（Windows / Program Files / ProgramData 等）——如需扫其中内容（如
  C:\ProgramData\miniconda3），把该目录作为**显式根**单独扫描即可绕过盘根剪枝
- venv 环境内不再深入（环境里不应再有环境，避免 site-packages 内 pyvenv.cfg 误报）；
  conda 环境仅继续下探其 ``envs\`` 子目录（conda base 的子环境位于 <base>\envs\）
- 遍历 / stat 均加 ``\\?\`` 长路径前缀（与 cleanup.py 同一机制，长路径安全）

闲置判定说明
------------
"最后改动"取环境内**最新文件 mtime**，是闲置判定的**代理信号**——Windows 上 atime 不可靠
（默认关闭最后访问时间更新）。判定闲置请结合备注列的项目线索人工确认。

用法
----
::

    python -u scan_venvs.py                          # 未给根：扫描全部固定盘（全机盘点）
    python -u scan_venvs.py D:/ C:/Users/public      # 只扫指定根（D:/、D:\、Git Bash 风格 /d/ 均接受）
    python -u scan_venvs.py --depth 6 D:/            # 限制深度（默认 0=不限；过深处罕见，限制可加速）
    python -u scan_venvs.py --idle-days 60 --sort age C:/
    python -u scan_venvs.py --save "C:/tmp/venv_report.md"   # 另存 Markdown 报告
    python -u scan_venvs.py --list-drives            # 诊断：仅列出检出的固定盘

说明：全盘扫描可能耗时数分钟，请前台 ``python -u`` 运行（每 5 秒心跳进度）；Ctrl+C 可随时
中断（只读，无副作用）。
"""
import argparse
import ctypes
import datetime
import os
import re
import sys
import time

PREFIX = '\\\\?\\'

PRUNE_ALWAYS = {'$recycle.bin', 'system volume information', 'node_modules', '.git'}
PRUNE_AT_ROOT = {'windows', 'program files', 'program files (x86)', 'programdata',
                 'perflogs', '$windows.~bt', '$windows.~ws'}

PROJECT_MARKERS = ('requirements.txt', 'pyproject.toml', 'poetry.lock',
                   'Pipfile', 'setup.py', 'environment.yml')


def unify(raw):
    r"""把 Git Bash 风格路径转成 Windows 路径；去掉 ``\\?\`` 前缀。"""
    p = str(raw).strip().strip('"')
    if p.startswith(PREFIX):
        p = p[len(PREFIX):]
    m = re.match(r'^/([A-Za-z])(/.*)?$', p)
    if m:
        p = "%s:%s" % (m.group(1).upper(), m.group(2) or '/')
    return p


def lp(p):
    r"""加 ``\\?\`` 长路径前缀（已带前缀则原样返回）。"""
    p = os.path.abspath(unify(p))
    if p.startswith(PREFIX):
        return p
    return PREFIX + p


def strip_prefix(p):
    return p[len(PREFIX):] if p.startswith(PREFIX) else p


def is_drive_root(p):
    return bool(re.fullmatch(r'[a-z]:', p.rstrip('\\').lower()))


def fixed_drives():
    """检出固定盘（DRIVE_FIXED==3）；紫败时回退到全部逻辑盘。"""
    try:
        letters = [d.rstrip('\\') for d in os.listdrives()]
    except Exception:
        letters = []
    if not letters:
        try:
            mask = ctypes.windll.kernel32.GetLogicalDrives()
            letters = [chr(65 + i) for i in range(26) if mask & (1 << i)]
        except Exception:
            letters = []
    try:
        gdt = ctypes.windll.kernel32.GetDriveTypeW
        gdt.argtypes = [ctypes.c_wchar_p]
        gdt.restype = ctypes.c_uint
    except Exception:
        return [d + '\\' for d in letters]
    out = []
    for d in letters:
        try:
            if gdt(d + '\\') == 3:
                out.append(d + '\\')
        except Exception:
            pass
    return out


def find_envs(roots, depth_limit, progress=True):
    """发现虚拟环境根目录。返回 (envs, dirs_seen, skipped_roots, elapsed)。"""
    found = []
    seen = set()
    dirs_seen = 0
    skipped = []
    t0 = time.time()
    last_tick = t0
    for root in roots:
        ap = os.path.abspath(unify(root))
        if not os.path.isdir(lp(ap)):
            skipped.append(ap)
            continue
        base_depth = ap.rstrip('\\').lower().count('\\')
        for dirpath, dirnames, filenames in os.walk(lp(ap), topdown=True):
            dirs_seen += 1
            if progress and time.time() - last_tick > 5:
                last_tick = time.time()
                print("  [扫描中] 目录 %d 个 | 已用 %ds | 已发现环境 %d 个"
                      % (dirs_seen, int(last_tick - t0), len(found)), flush=True)
            plain = strip_prefix(dirpath)
            cur_depth = plain.rstrip('\\').lower().count('\\') - base_depth
            low = plain.lower()
            fl = {f.lower() for f in filenames}
            dl = {d.lower() for d in dirnames}
            if 'pyvenv.cfg' in fl:
                kind = 'venv'
            elif 'conda-meta' in dl:
                kind = 'conda'
            else:
                kind = None
            if kind:
                if low not in seen:
                    seen.add(low)
                    found.append({'path': plain, 'kind': kind})
                # venv 内不再深入；conda 仅下探其 envs\ 子目录（子环境所在）
                dirnames[:] = [d for d in dirnames
                               if kind == 'conda' and d.lower() == 'envs']
                continue
            if depth_limit and cur_depth >= depth_limit:
                dirnames[:] = []
                continue
            root_level = is_drive_root(plain)
            kept = []
            for d in dirnames:
                ld = d.lower()
                if ld in PRUNE_ALWAYS:
                    continue
                if root_level and ld in PRUNE_AT_ROOT:
                    continue
                kept.append(d)
            dirnames[:] = kept
    return found, dirs_seen, skipped, time.time() - t0


def enrich(env, now):
    """补全单个环境：大小 / 文件数 / 最新 mtime / 版本 / 项目线索。"""
    w = lp(env['path'])
    size = 0
    count = 0
    newest = 0.0
    for dirpath, _dirs, filenames in os.walk(w, topdown=True):
        for f in filenames:
            try:
                st = os.stat(os.path.join(dirpath, f))
            except OSError:
                continue
            size += st.st_size
            count += 1
            if st.st_mtime > newest:
                newest = st.st_mtime
    env['size'] = size
    env['files'] = count
    env['mtime'] = newest
    env['age_days'] = (now - newest) / 86400.0 if newest else None

    env['pyver'] = ''
    env['home'] = ''
    if env['kind'] == 'venv':
        try:
            with open(os.path.join(w, 'pyvenv.cfg'), 'r', encoding='utf-8',
                      errors='replace') as fh:
                for line in fh:
                    if '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k in ('version', 'version_info'):
                        v = v.split('.final')[0]
                        env['pyver'] = '.'.join(v.split('.')[:3])
                    elif k == 'home':
                        env['home'] = v
        except OSError:
            pass
    else:
        best = ''
        try:
            for nm in os.listdir(os.path.join(w, 'conda-meta')):
                m = re.match(r'python-(\d+\.\d+(?:\.\d+)?)-.*\.json$', nm, re.I)
                if m and len(m.group(1)) > len(best):
                    best = m.group(1)
        except OSError:
            pass
        env['pyver'] = best

    env['home_ok'] = True
    if env['home']:
        try:
            env['home_ok'] = os.path.exists(lp(env['home']))
        except Exception:
            env['home_ok'] = False

    env['pyexe'] = any(
        os.path.exists(os.path.join(w, *parts))
        for parts in (('python.exe',), ('Scripts', 'python.exe'), ('bin', 'python')))

    parent = os.path.dirname(env['path'])
    hints = [m for m in PROJECT_MARKERS if os.path.exists(os.path.join(lp(parent), m))]
    if os.path.isdir(os.path.join(lp(parent), '.git')):
        hints.append('.git')
    env['hints'] = hints
    env['protected'] = '\\.workbuddy-ai' in env['path'].lower()


def fmt_size(n):
    """人类可读大小（B/KB/MB/GB）。"""
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return ("%d B" % n) if unit == 'B' else ("%.2f %s" % (n, unit))
        n /= 1024


def age_str(env):
    a = env['age_days']
    if a is None:
        return '?'
    if a < 1:
        return '今天'
    if a <= 999:
        return '%d 天前' % int(a)
    return datetime.datetime.fromtimestamp(env['mtime']).strftime('%Y-%m-%d')


def notes_of(env, idle_days):
    out = []
    if not env['pyexe']:
        out.append('缺 python 解释器')
    if env['home'] and not env['home_ok']:
        out.append('home 失效')
    if idle_days and env['age_days'] is not None and env['age_days'] > idle_days:
        out.append('闲置 %d 天' % int(env['age_days']))
    if env['hints']:
        out.append('项目: ' + ', '.join(env['hints']))
    if env['protected']:
        out.append('受保护(.workbuddy-ai)，清理需 --force')
    return out


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    ap = argparse.ArgumentParser(
        description='Python 虚拟环境只读盘点器（venv / conda；不做任何删除）')
    ap.add_argument('roots', nargs='*', help='扫描根目录（可多个）；省略则扫描全部固定盘')
    ap.add_argument('--depth', type=int, default=0, help='最大扫描深度（0=不限，默认）')
    ap.add_argument('--idle-days', type=int, default=90,
                    help='闲置判定阈值天数（默认 90；0=关闭闲置标记）')
    ap.add_argument('--sort', choices=('size', 'age', 'path'), default='size',
                    help='排序：size 体积（默认）/ age 最旧优先 / path 路径')
    ap.add_argument('--save', metavar='FILE.md', help='另存 Markdown 报告到指定文件')
    ap.add_argument('--no-progress', action='store_true', help='关闭扫描心跳输出')
    ap.add_argument('--list-drives', action='store_true', help='诊断：仅列出检出的固定盘后退出')
    args = ap.parse_args(argv)

    if args.list_drives:
        ds = fixed_drives()
        print('固定盘：%s' % (', '.join(ds) if ds else '（未检出）'))
        return 0

    roots = [os.path.abspath(unify(r)) for r in args.roots]
    if not roots:
        roots = fixed_drives()
        if not roots:
            print('未指定根目录，且未检出固定盘。')
            return 2
        print('未指定根目录 → 扫描全部固定盘：%s' % ', '.join(roots))
        print('（只读操作，可 Ctrl+C 随时中断）')
    else:
        print('扫描根：%s' % ', '.join(roots))

    try:
        found, dirs_seen, skipped, elapsed = find_envs(
            roots, args.depth, progress=not args.no_progress)
    except KeyboardInterrupt:
        print('\n[中断] 已取消扫描（只读操作，无任何副作用）。')
        return 130
    for s in skipped:
        print('[跳过] 不存在或不是目录：%s' % s)
    print('扫描完成：目录 %d 个 | 用时 %.1fs | 发现环境 %d 个'
          % (dirs_seen, elapsed, len(found)))
    if not found:
        print('未发现虚拟环境（venv / conda）。')
        return 0

    now = time.time()
    for e in found:
        enrich(e, now)

    if args.sort == 'age':
        found.sort(key=lambda e: -(e['age_days'] or 0))
    elif args.sort == 'path':
        found.sort(key=lambda e: e['path'].lower())
    else:
        found.sort(key=lambda e: -e['size'])

    total = sum(e['size'] for e in found)
    labels = {'size': '体积', 'age': '最旧优先', 'path': '路径'}
    print('\n== 环境清单（%d 个，合计 %s；%s）=='
          % (len(found), fmt_size(total), labels[args.sort]))
    print('   %-10s %-7s %-9s %-5s %-9s %s'
          % ('大小', '文件数', '最后改动', '类型', 'Python', '路径 [备注]'))
    for e in found:
        nts = notes_of(e, args.idle_days)
        tail = ('  [' + '; '.join(nts) + ']') if nts else ''
        print('   %-10s %-7s %-9s %-5s %-9s %s%s'
              % (fmt_size(e['size']), '{:,}'.format(e['files']), age_str(e),
                 e['kind'], e['pyver'] or '?', e['path'], tail))

    print('\n-- 汇总 --')
    for kind in ('venv', 'conda'):
        ks = [e for e in found if e['kind'] == kind]
        if ks:
            print('  · %s：%d 个 / %s'
                  % (kind, len(ks), fmt_size(sum(e['size'] for e in ks))))
    idle = [e for e in found if args.idle_days and e['age_days'] is not None
            and e['age_days'] > args.idle_days]
    if idle:
        print('  · 疑似闲置(>%d 天)：%d 个 / %s —— 逐一确认后再清'
              % (args.idle_days, len(idle), fmt_size(sum(e['size'] for e in idle))))

    print('\n提示（本报告只读，未改动任何文件）：')
    print('  · 清理前先确认无进程占用该环境（其 python.exe 可能正在运行）')
    print('  · 常规两步法（进回收站、可恢复）：')
    print('      python scripts/cleanup.py <路径>  →  python scripts/purge_recycle.py --execute <路径>')
    print('  · 确认可弃且求快：python scripts/fast_del_tree.py <路径>（永久删除；venv 可用 python -m venv 重建）')
    print('  · .workbuddy-ai 下的托管环境（如技能共享 venv）删除会影响依赖它的流程——需 --force 且务必人工确认')

    if args.save:
        save = os.path.abspath(unify(args.save))
        lines = ['# Python 虚拟环境盘点报告', '',
                 '- 生成：%s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 '- 扫描根：%s' % ', '.join(roots),
                 '- 合计：%d 个 / %s' % (len(found), fmt_size(total)), '',
                 '| 大小 | 文件数 | 最后改动 | 类型 | Python | 路径 | 备注 |',
                 '|---|---|---|---|---|---|---|']
        for e in found:
            lines.append('| %s | %s | %s | %s | %s | `%s` | %s |'
                         % (fmt_size(e['size']), '{:,}'.format(e['files']), age_str(e),
                            e['kind'], e['pyver'] or '?', e['path'],
                            '；'.join(notes_of(e, args.idle_days)) or ''))
        lines.append('')
        lines.append('> 由 session-temp-cleanup / scan_venvs.py 生成（只读盘点；'
                     '清理请走 cleanup.py 两步法或 fast_del_tree.py）。')
        try:
            with open(save, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(lines) + '\n')
            print('\n报告已保存：%s' % save)
        except OSError as ex:
            print('\n[警告] 报告保存失败：%s' % ex)
    return 0


if __name__ == '__main__':
    sys.exit(main())
