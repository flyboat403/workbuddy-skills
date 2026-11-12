# -*- coding: utf-8 -*-
r"""probe_env.py —— 环境校准器（session-temp-cleanup 通用化的关键件）。

为什么需要它
------------
本技能的删除/释放行为**因环境、甚至因目标路径而异**，典型例子（WorkBuddy 安全删除层）：
  · 普通路径（工作区/项目目录）：删除会进回收站 → 需「删除 + 回收站清除」两步法才真释放；
  · OS 临时目录（%TEMP% / tempfile.gettempdir()）：被**豁免**——原生永久删除、不进回收站。
因此本脚本在**两处落点**各做一次小规模受控实验（只操作自建测试文件，不碰任何用户文件、
事后自动清理并清除回收站残留），实测回答：
  1. 你关心的工作区落点上，删除是否进回收站（决定是否需要 purge 第二步）；
  2. OS 临时目录下的删除去向（是否有路径豁免）；
  3. purge_recycle.py 在本环境是否可用（能否扫到并清除回收站条目）。

用法
----
::

    python -u probe_env.py                          # 默认工作区落点 = 当前目录（cwd）
    python -u probe_env.py --workdir D:/_tmp_probe  # 指定工作区落点（推荐指向你的实际清理区域）
    python -u probe_env.py --save LOCAL-NOTES.md    # 另存 Markdown 校准记录
    python -u probe_env.py --keep                   # 保留实验文件（默认自动清理）

退出码：0 = 校准完成（无论结论如何）；2 = 参数/环境错误。
"""
import argparse
import ctypes
import os
import platform
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import purge_recycle as pr      # 复用：norm_target / scan / del_file / del_tree / lp / GAW / DFW / SFW / RDW


def w(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def ctypes_delete_file(path):
    """ctypes 原生删除单个文件（与 fast_del_tree.py 同一机制）。"""
    l = pr.lp(path)
    if pr.DFW(l):
        return True
    if ctypes.get_last_error() == 5:
        pr.SFW(l, 0x80)
        return bool(pr.DFW(l))
    return False


def list_drives():
    try:
        return sorted({d.rstrip("\\").upper() for d in os.listdrives()})
    except Exception:
        pass
    try:
        m = ctypes.windll.kernel32.GetLogicalDrives()
        return [chr(65 + i) + ":" for i in range(26) if m & (1 << i)]
    except Exception:
        return []


def run_experiment(location, tag):
    """在 location 下做一轮实验；返回 (entryA_in_bin, entryB_in_bin, errA, errB, dirA, dirB)。"""
    probe = os.path.join(location, "._session_temp_cleanup_probe_%s_%s"
                         % (tag, time.strftime("%Y%m%d_%H%M%S")))
    os.makedirs(probe, exist_ok=True)
    fa = os.path.join(probe, "A_os_remove.txt")
    fb = os.path.join(probe, "B_ctypes.txt")
    w(fa, "probe")
    w(fb, "probe")
    ea = eb = ""
    try:
        os.remove(fa)
    except OSError as e:
        ea = str(e)
    try:
        ctypes_delete_file(fb)
    except Exception as e:
        eb = str(e)

    entries = pr.scan([pr.norm_target(probe)])

    def in_bin(tag2):
        return any(tag2.lower() in (e["orig"] or "").lower() for e in entries)

    return in_bin("A_os_remove"), in_bin("B_ctypes"), ea, eb, probe, entries


def cleanup_dir(path):
    """尽力删除实验目录（空目录）。"""
    try:
        if not os.path.isdir(path):
            return True
        pr.RDW(pr.lp(path))
        return not os.path.isdir(path)
    except Exception:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="session-temp-cleanup 环境校准器（受控小实验，不留痕）")
    ap.add_argument("--workdir", default="", help="工作区落点（默认：当前目录 cwd；建议指向你的实际清理区域）")
    ap.add_argument("--save", default="", help="把校准记录另存为 Markdown 文件")
    ap.add_argument("--keep", action="store_true", help="保留实验文件（默认自动清理）")
    args = ap.parse_args(argv)

    if os.name != "nt":
        print("本技能目前仅支持 Windows（脚本依赖 kernel32 / 回收站机制）。")
        return 2

    tmp_root = tempfile.gettempdir()
    print("== session-temp-cleanup 环境校准 ==")
    print()

    # ---------- [1] 环境信息 ----------
    drives = list_drives()
    print("[1] 环境信息")
    print("   OS      : %s" % platform.platform())
    print("   Python  : %s" % sys.version.split()[0])
    print("   盘符    : %s" % (", ".join(drives) if drives else "（无法枚举）"))
    shim = any(os.environ.get(k) for k in ("CODEBUDDY_SAFE_DELETE_ENABLED",
                                           "CODEBUDDY_SAFE_DELETE_SANDBOX",
                                           "CODEBUDDY_BROKERED_FS_HOOK_ENABLED"))
    print("   安全删除层：%s" % ("检测到（WorkBuddy/CodeBuddy 系）" if shim else "未检测到（可能是原生环境）"))
    for k in ("CODEBUDDY_SAFE_DELETE_ENABLED", "CODEBUDDY_SAFE_DELETE_SANDBOX",
              "CODEBUDDY_BROKERED_FS_HOOK_ENABLED"):
        print("      %s = %s" % (k, os.environ.get(k, "（未设置）")))
    print("   OS 临时目录：%s" % tmp_root)

    # ---------- [2] 双落点实验 ----------
    print()
    print("[2] 删除行为实验（自建测试文件；实验后自动清理并清除回收站残留）")

    results = {}
    # 位置①：工作区落点（用"能否创建实验目录"直接做写权限判断，避免额外残留）
    work_root = args.workdir or os.getcwd()
    try:
        a1, b1, e1a, e1b, probe1, entries1 = run_experiment(work_root, "work")
    except OSError:
        print("   ⚠ 工作区落点不可写：%s —— 回退为 OS 临时目录" % work_root)
        work_root = tmp_root
        a1, b1, e1a, e1b, probe1, entries1 = run_experiment(work_root, "work")
    results["work"] = (work_root, probe1, a1, b1, e1a, e1b, entries1)
    print("   位置① 工作区落点：%s" % probe1)
    print("      A. os.remove（cleanup.py 默认路径） → %s" % state(a1, e1a))
    print("      B. ctypes 原生删除（fast_del_tree 机制） → %s" % state(b1, e1b))

    # 位置②：OS 临时目录
    a2, b2, e2a, e2b, probe2, entries2 = run_experiment(tmp_root, "tmp")
    results["tmp"] = (tmp_root, probe2, a2, b2, e2a, e2b, entries2)
    print("   位置② OS 临时目录：%s" % probe2)
    print("      A. os.remove → %s" % state(a2, e2a))
    print("      B. ctypes 原生删除 → %s" % state(b2, e2b))

    # ---------- [3] 清理实验目录 + purge 残留 ----------
    if not args.keep:
        for key in ("work", "tmp"):
            _root, probe, *_rest = results[key]
            cleanup_dir(probe)
    all_targets = [pr.norm_target(results["work"][1]), pr.norm_target(results["tmp"][1])]
    all_entries = pr.scan(all_targets)
    print()
    print("[3] purge_recycle 可用性（清除两处实验残留）")
    print("   回收站检出实验条目：%d 条" % len(all_entries))
    purged, pfail = 0, []
    for e in all_entries:
        attr = pr.GAW(pr.lp(e["r"]))
        is_dir = attr != 0xFFFFFFFF and bool(attr & 0x10)
        if is_dir:
            pr.del_tree(e["r"])
        elif os.path.lexists(e["r"]):
            pr.del_file(e["r"])
        if os.path.lexists(e["i"]):
            pr.del_file(e["i"])
        if os.path.lexists(e["r"]) or os.path.lexists(e["i"]):
            pfail.append(e["orig"])
        else:
            purged += 1
    if all_entries:
        print("   实测清除：%d/%d 条%s" % (purged, len(all_entries),
              "" if not pfail else "（失败 %d 条，可能是权限/占用）" % len(pfail)))
        for o in pfail[:10]:
            print("     FAIL %s" % o)
    else:
        print("   未检出条目（若实验显示删除未进回收站，属正常）。")

    # ---------- [4] 结论 ----------
    need_purge = a1 or b1
    tmp_exempt = not (a2 or b2)
    print()
    print("[4] 校准结论与推荐工作流")
    if need_purge:
        print("   · 工作区落点的删除【会进入回收站】→ 建议**两步法**：")
        print("     cleanup.py 删除 → purge_recycle.py --execute → 复扫核验")
        print("     （不做第二步，空间不会释放）")
    else:
        print("   · 工作区落点的删除【未进入回收站】（原生直接删除）→ 两步法非必需：")
        print("     cleanup.py 删除即真释放；purge_recycle.py 可保留作保险。")
    if need_purge and tmp_exempt:
        print("   · ⚠ 本环境为**路径相关**策略：OS 临时目录（%TEMP%）下的删除被豁免、")
        print("     为原生永久删除（快、不进回收站、不可恢复）——清理 %TEMP% 无需 purge。")
    elif need_purge and not tmp_exempt:
        print("   · 两处落点行为一致（都进回收站）。")
    if all_entries:
        print("   · purge_recycle 在本环境%s。" % ("可用 ✓（已实测清除）" if purged == len(all_entries)
              else "存在清除失败项，见上"))
    print("   · 提示：把本页结论写入技能目录的 LOCAL-NOTES.md（内附模板），供后续会话直接使用。")

    # ---------- [5] 收尾检查 ----------
    if not args.keep:
        leftovers = []
        for key in ("work", "tmp"):
            _root, probe, *_rest = results[key]
            if os.path.isdir(probe):
                for _r, _ds, fs in os.walk(probe):
                    leftovers += [os.path.join(_r, f) for f in fs]
                leftovers.append(probe + "（目录）")
        print("\n[5] 实验收尾：%s" % ("存在未清残留：%s" % leftovers if leftovers
                                      else "实验目录已清理（回收站残留见 [3]）。"))

    # ---------- 可选：另存 Markdown ----------
    if args.save:
        def yn(x):
            return "进入回收站" if x else "未进入回收站（直接删除）"
        lines = [
            "# 环境校准记录（session-temp-cleanup · probe_env）",
            "",
            "- 校准时间：%s" % time.strftime("%Y-%m-%d %H:%M"),
            "- 环境：%s" % platform.platform(),
            "- 盘符：%s" % (", ".join(drives) or "?"),
            "- 安全删除层：%s" % ("检测到（WorkBuddy/CodeBuddy 系）" if shim else "未检测到"),
            "",
            "## 实测结论（两处落点 × 两种删除方式）",
            "",
            "| 落点 | os.remove | ctypes 原生删除 |",
            "|---|---|---|",
            "| 工作区（%s） | %s | %s |" % (results["work"][0], yn(a1), yn(b1)),
            "| OS 临时目录（%s） | %s | %s |" % (tmp_root, yn(a2), yn(b2)),
            "",
            "## 推荐工作流",
            "",
        ]
        if need_purge:
            lines.append("**两步法**：`cleanup.py` 删除 → `purge_recycle.py --execute` → 复扫核验。")
            if tmp_exempt:
                lines.append("")
                lines.append("> 注：本环境为路径相关策略——OS 临时目录（%TEMP%）下的删除被豁免、"
                             "为原生永久删除，无需 purge。")
        else:
            lines.append("**单步法**：`cleanup.py` 删除即真释放（`purge_recycle.py` 可保留作保险）。")
        lines.append("")
        with open(args.save, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("校准记录已保存：%s" % os.path.abspath(args.save))

    return 0


def state(ok, err):
    if err:
        return "删除失败：%s" % err
    return "进入回收站 ✓" if ok else "未进入回收站（直接删除）"


if __name__ == "__main__":
    sys.exit(main())
