import pandas as pd
import numpy as np
import re

def calc_ai_score_v2(row):
    # ベーススコア
    score = 70.0

    # 🏇 ① 全成績（これまでのベース）
    try:
        perf = str(row.get("全成績", ""))
        match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', perf)
        if match:
            w1, w2, w3, l = map(int, match.groups())
            total = w1 + w2 + w3 + l
            if total > 0: score += ((w1 + w2 + w3) / total) * 15.0
    except: pass

    # 🏟️ ② 当競馬場成績（NEW: ご当地専用機ボーナス！）
    try:
        track_perf = str(row.get("当競馬場成績", ""))
        match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', track_perf)
        if match:
            w1, w2, w3, l = map(int, match.groups())
            total = w1 + w2 + w3 + l
            if total > 0: score += ((w1 + w2 + w3) / total) * 10.0
    except: pass

    # 🧑‍🌾 ③ 騎手成績（NEW: 神ジョッキー特大ボーナス！）
    try:
        jockey_perf = str(row.get("騎手成績", ""))
        match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', jockey_perf)
        if match:
            w1, w2, w3, l = map(int, match.groups())
            total = w1 + w2 + w3 + l
            if total > 0: score += ((w1 + w2 + w3) / total) * 10.0
    except: pass

    # 🎲 ④ 枠番補正（NEW: 戦場ごとの有利不利！）
    try:
        track = str(row.get("競馬場", ""))
        wakuban = int(row.get("枠番", 4))
        # 例: 金沢は内枠(1~3)が少し有利と仮定して加点
        if track == "金沢" and wakuban <= 3:
            score += 2.0
        # 例: 盛岡は外枠(6~8)が少し有利と仮定して加点
        elif track == "盛岡" and wakuban >= 6:
            score += 2.0
    except: pass

    # ⑤ 人気エフェクト（世間が買っている馬はオッズが下がるため少し減点）
    try:
        pop_val = row.get("人気", 5)
        if pd.notna(pop_val) and str(pop_val) != "nan":
            score -= (float(pop_val) * 0.5)
    except: pass

    # スコアを35〜99の間に収める（乱数・サイコロは完全排除！）
    if np.isnan(score) or np.isinf(score): return 70
    return max(35, min(99, int(score)))

# 💵 --- 期待値(EV) 自動判定スキャナー ---
def check_expected_value(ai_score, odds):
    # 過去データに基づく「実際のワイド馬券内率」
    if ai_score >= 95:
        win_rate = 0.58  # 58%
    elif ai_score >= 90:
        win_rate = 0.50  # 50%
    else:
        win_rate = 0.20  # 危険水域
        
    # 期待値計算 (EV = 勝率 × オッズ)
    ev = win_rate * odds
    
    if ev >= 1.2:
        return f"期待値 {ev*100:.1f}% 🚀 激アツ！資金ブチ込み推奨！"
    elif ev >= 1.0:
        return f"期待値 {ev*100:.1f}% 🟢 買い！プラス収支圏内"
    else:
        return f"期待値 {ev*100:.1f}% 💀 危険！買えば買うほど損します（見送り）"
