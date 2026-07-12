import streamlit as st
import pandas as pd
import numpy as np
import re

# ==========================================
# 1. 画面の基本設定（顔）
# ==========================================
st.set_page_config(page_title="大将軍の要塞 V2", layout="wide")
st.title("🏯 大将軍の要塞 V2 (期待値スキャナー搭載)")
st.write("競馬場適性・騎手成績・枠順の隠しパラメーターを搭載した最新エンジンです。")

# ==========================================
# 2. V2エンジン（脳ミソ：スコア計算）
# ==========================================
def calc_ai_score_v2(row):
    score = 70.0

    # ① 全成績
    try:
        perf = str(row.get("全成績", ""))
        match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', perf)
        if match:
            w1, w2, w3, l = map(int, match.groups())
            total = w1 + w2 + w3 + l
            if total > 0: score += ((w1 + w2 + w3) / total) * 15.0
    except: pass

    # ② 当競馬場成績（ご当地専用機ボーナス）
    try:
        track_perf = str(row.get("当競馬場成績", ""))
        match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', track_perf)
        if match:
            w1, w2, w3, l = map(int, match.groups())
            total = w1 + w2 + w3 + l
            if total > 0: score += ((w1 + w2 + w3) / total) * 10.0
    except: pass

    # ③ 騎手成績（神ジョッキー特大ボーナス）
    try:
        jockey_perf = str(row.get("騎手成績", ""))
        match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', jockey_perf)
        if match:
            w1, w2, w3, l = map(int, match.groups())
            total = w1 + w2 + w3 + l
            if total > 0: score += ((w1 + w2 + w3) / total) * 10.0
    except: pass

    # ④ 枠番補正（戦場ごとの有利不利）
    try:
        track = str(row.get("競馬場", ""))
        wakuban = int(row.get("枠番", 4))
        if track == "金沢" and wakuban <= 3: score += 2.0
        elif track == "盛岡" and wakuban >= 6: score += 2.0
    except: pass

    # ⑤ 人気エフェクト
    try:
        pop_val = row.get("人気", 5)
        if pd.notna(pop_val) and str(pop_val) != "nan":
            score -= (float(pop_val) * 0.5)
    except: pass

    if np.isnan(score) or np.isinf(score): return 70
    return max(35, min(99, int(score)))

# ==========================================
# 3. 画面の操作とデータ表示（顔）
# ==========================================
# ファイルアップロード
horse_file = st.file_uploader("出馬表データ (horselist.csv) をアップロードしてください", type=["csv"])

if horse_file is not None:
    # データの読み込み
    df = pd.read_csv(horse_file)
    
    # 新エンジンでスコア計算！
    df["AIスコア_V2"] = df.apply(calc_ai_score_v2, axis=1)
    
    # 画面に表示する列を絞り込む
    display_cols = ["競馬場", "レース番号", "枠番", "馬番", "馬名", "騎手名", "人気", "AIスコア_V2"]
    # CSVに存在している列だけを選択（エラー防止）
    display_cols = [c for c in display_cols if c in df.columns]
    
    st.subheader("📊 解析結果 (V2エンジン)")
    st.dataframe(
        df[display_cols].sort_values(by=["競馬場", "レース番号", "AIスコア_V2"], ascending=[True, True, False]),
        use_container_width=True,
        height=600
    )
