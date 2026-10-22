"""Record compatibility, validation, and pity-aware accounting independent of UI."""
import io
import pandas as pd

COLUMNS = ["时间", "角色名", "是UP?", "抽数"]


def empty_records():
    return pd.DataFrame({"时间": pd.Series(dtype="str"), "角色名": pd.Series(dtype="str"),
                         "是UP?": pd.Series(dtype="str"), "抽数": pd.Series(dtype="float64")})


def normalize_records(df, require_columns=False):
    out = df.copy()
    if "是否UP?" in out:
        if "是UP?" in out:
            out["是UP?"] = out["是UP?"].fillna(out["是否UP?"])
        else:
            out["是UP?"] = out["是否UP?"]
    missing = [c for c in ["角色名", "是UP?", "抽数"] if c not in out]
    if require_columns and missing:
        raise ValueError("缺少列：" + "、".join(missing))
    for c in COLUMNS:
        if c not in out:
            out[c] = None if c == "抽数" else ""
    out = out[COLUMNS].copy()
    for c in ["时间", "角色名", "是UP?"]:
        out[c] = out[c].fillna("").astype(str).str.strip()
    out["抽数"] = pd.to_numeric(out["抽数"], errors="coerce")
    return out.reset_index(drop=True)


def merge_records(old_df, new_df):
    """Multiset union: importing the same file again is safe, repeated real rows survive."""
    old, new = normalize_records(old_df), normalize_records(new_df, require_columns=True)
    if old.empty:
        return new
    # An occurrence index preserves two genuine identical rows without duplicating re-imports.
    keys = COLUMNS
    for frame in [old, new]:
        frame["_occurrence"] = frame.groupby(keys, dropna=False).cumcount()
    merged = pd.concat([old, new], ignore_index=True).drop_duplicates(keys + ["_occurrence"], keep="first")
    return merged[COLUMNS].reset_index(drop=True)


def read_backup(data, filename):
    settings = {}
    if filename.lower().endswith(".csv"):
        try:
            frame = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig")
        except UnicodeDecodeError:
            frame = pd.read_csv(io.BytesIO(data), encoding="gb18030")
    else:
        book = pd.ExcelFile(io.BytesIO(data))
        frame = pd.read_excel(book, sheet_name="抽卡记录" if "抽卡记录" in book.sheet_names else 0)
        if "统计设置" in book.sheet_names:
            meta = pd.read_excel(book, sheet_name="统计设置")
            if {"设置", "值"}.issubset(meta.columns):
                values = dict(zip(meta["设置"], meta["值"]))
                tail = float(values.get("当前垫抽", 0))
                if not tail.is_integer() or not 0 <= tail <= 78:
                    raise ValueError("备份中的当前垫抽应为0–78的整数")
                settings = {"tail_pity": int(tail),
                            "initial_guaranteed": str(values.get("记录起点为大保底", "否")).lower() in ("是", "true", "1")}
    return normalize_records(frame, require_columns=True), settings


def export_backup(df, tail_pity=0, initial_guaranteed=False):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        normalize_records(df).to_excel(writer, index=False, sheet_name="抽卡记录")
        pd.DataFrame({"设置": ["当前垫抽", "记录起点为大保底"],
                      "值": [tail_pity, "是" if initial_guaranteed else "否"]}).to_excel(writer, index=False, sheet_name="统计设置")
    return output.getvalue()


def analyze_records(df, tail_pity=0, initial_guaranteed=False):
    if not isinstance(tail_pity, int) or not 0 <= tail_pity <= 78:
        raise ValueError("当前垫抽须为0–78的整数")
    raw = normalize_records(df)
    valid, issues = [], []
    for i, row in raw.iterrows():
        name = row["角色名"]
        if not name and pd.isna(row["抽数"]) and not row["是UP?"]:
            continue
        try:
            value = float(row["抽数"])
        except (TypeError, ValueError):
            value = float("nan")
        if not name or row["是UP?"] not in ("是", "否") or pd.isna(value) or not 1 <= value <= 80 or not value.is_integer():
            issues.append(f"第{i + 1}行未参与统计：需填写角色名、是/否及1–80的整数抽数。")
            continue
        data = row.to_dict()
        data["抽数"] = int(value)
        valid.append(data)
    clean = pd.DataFrame(valid, columns=COLUMNS)
    pending = total_up_cost = up_count = wins = opportunities = 0
    guaranteed = bool(initial_guaranteed)
    entries = []
    model_issues = list(issues)
    for i, row in enumerate(valid):
        pulls, is_up = row["抽数"], row["是UP?"] == "是"
        if pulls > 79:
            model_issues.append(f"第{i + 1}条金记录为80抽，与79抽模型不符；原记录已保留。")
        pending += pulls
        if guaranteed and not is_up:
            model_issues.append(f"第{i + 1}条金在大保底状态下仍标为非UP，请核对顺序或卡池。")
        if not guaranteed:
            opportunities += 1
            wins += int(is_up)
        current_cost = pending if is_up else None
        pity_type = ("强娶 (大保底)" if guaranteed else "运气 (小保底)") if is_up else "歪了"
        if is_up:
            total_up_cost += pending
            up_count += 1
            pending = 0
        guaranteed = not is_up
        entries.append({**row, "保底类型": pity_type, "实际花费": current_cost})
    gold_count = len(valid)
    logged_pulls = int(clean["抽数"].sum()) if gold_count else 0
    total_pulls = logged_pulls + tail_pity
    stats = {
        "总出金": gold_count, "UP数": up_count, "不歪率": wins / opportunities if opportunities else None,
        "小保底次数": opportunities, "小保底赢": wins, "记录抽数": logged_pulls, "总投入": total_pulls,
        "平均出金": logged_pulls / gold_count if gold_count else None,
        "UP平均花费": total_up_cost / up_count if up_count else None,
        "预算每UP": total_pulls / up_count if up_count else None,
        "未完成UP投入": pending + tail_pity, "当前垫抽": tail_pity,
        "下次大保底": guaranteed, "起始大保底": bool(initial_guaranteed),
        "可对比": not model_issues and total_pulls > 0 and total_pulls <= 100000,
        "问题": model_issues,
    }
    return pd.DataFrame(entries, columns=COLUMNS + ["保底类型", "实际花费"]), stats
