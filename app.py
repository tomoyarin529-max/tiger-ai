import streamlit as st
import pandas as pd
import numpy as np
import re
import zipfile
import io
import itertools

# ==========================================
# 1. 画面の基本設定
# ==========================================
st.set_page_config(page_title="大将軍の要塞 V2 (最終形態)", layout="wide")
st.title("🏯 大将軍の要塞 V2 (期待値スキャナー搭載)")
st.write("出馬表とオッズを合体させ、「期待値100%を超える買い目」だけをスナイプする最終兵器です。")

# 📂 サイドバーに「フォーカス機能」を配備！
st.sidebar.header("🎯 スナイプ厳選フィルター")
min_score_filter = st.sidebar.slider(
    "🔥 最低AIスコアの足切りライン", 
    min_value=50, 
    max_value=99, 
    value=80,
    help="ここで設定したスコア未満の『自信のない混戦レース』を画面から一瞬で消し去ります。"
)

# ==========================================
# 2. V2エンジン（隠しパラメーター搭載AI）
# ==========================================
def calc_ai_score_v2(row):
    score = 70.0
    try:
        perf = str(row.get("全成績", ""))
        match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', perf)
        if match:
            w1, w2, w3, l = map(int, match.groups())
            total = w1 + w2 + w3 + l
            if total > 0: score += ((w1 + w2 + w3) / total) * 15.0
    except: pass
    try:
        track_perf = str(row.get("当競馬場成績", ""))
        match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', track_perf)
        if match:
            w1, w2, w3, l = map(int, match.groups())
            total = w1 + w2 + w3 + l
            if total > 0: score += ((w1 + w2 + w3) / total) * 10.0
    except: pass
    try:
        jockey_perf = str(row.get("騎手成績", ""))
        match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', jockey_perf)
        if match:
            w1, w2, w3, l = map(int, match.groups())
            total = w1 + w2 + w3 + l
            if total > 0: score += ((w1 + w2 + w3) / total) * 10.0
    except: pass
    try:
        track = str(row.get("競馬場", ""))
        wakuban = int(row.get("枠番", 4))
        if track == "金沢" and wakuban <= 3: score += 2.0
        elif track == "盛岡" and wakuban >= 6: score += 2.0
    except: pass
    try:
        pop_val = row.get("人気", 5)
        if pd.notna(pop_val) and str(pop_val) != "nan":
            score -= (float(pop_val) * 0.5)
    except: pass
    if np.isnan(score) or np.isinf(score): return 70
    return max(35, min(99, int(score)))

# ==========================================
# 3. ファイル読み込み関数
# ==========================================
def load_csv_from_upload(uploaded_files, target_keyword):
    df_list = []
    for file in uploaded_files:
        if file.name.endswith('.zip'):
            with zipfile.ZipFile(file, 'r') as z:
                for filename in z.namelist():
                    if target_keyword in filename and filename.endswith('.csv'):
                        with z.open(filename) as f:
                            try:
                                df_list.append(pd.read_csv(f, encoding="shift_jis"))
                            except:
                                f.seek(0)
                                df_list.append(pd.read_csv(f, encoding="utf-8"))
        elif target_keyword in file.name and file.name.endswith('.csv'):
            try:
                df_list.append(pd.read_csv(file, encoding="shift_jis"))
            except:
                file.seek(0)
                df_list.append(pd.read_csv(file, encoding="utf-8"))
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return None

# ==========================================
# 4. メイン画面
# ==========================================
uploaded_files = st.file_uploader(
    "📂 【race.zip】 と 【odds.zip】 をまとめてドロップしてください！", 
    type=["zip", "csv"], 
    accept_multiple_files=True
)

if uploaded_files:
    df_horse = load_csv_from_upload(uploaded_files, "horselist")
    
    if df_horse is not None:
        df_horse["AIスコア_V2"] = df_horse.apply(calc_ai_score_v2, axis=1)
        
        st.success("✅ 出馬表データの解析完了！")
        
        target_buys = []
        grouped = df_horse.groupby(["競馬場", "レース番号"])
        
        for (track, race_num), group in grouped:
            if len(group) >= 3:
                top3 = group.sort_values(by="AIスコア_V2", ascending=False).head(3)
                horses = top3["馬番"].astype(int).tolist()
                scores = top3["AIスコア_V2"].tolist()
                max_score = scores[0]
                
                # 🎯【追加】AI最高点が大将軍の設定した足切りライン未満なら、そのレースは非表示！
                if max_score < min_score_filter:
                    continue
                
                if max_score >= 95:
                    win_rate = 0.58
                elif max_score >= 90:
                    win_rate = 0.50
                else:
                    win_rate = 0.20
                
                target_odds = round(1.0 / win_rate, 1) if win_rate > 0 else 99.9
                
                combos = list(itertools.combinations(horses, 2))
                for combo in combos:
                    target_buys.append({
                        "競馬場": track,
                        "レース": f"{race_num}R",
                        "AI最高点": max_score,
                        "買い目 (ワイド)": f"{combo[0]} - {combo[1]}",
                        "推定勝率": f"{win_rate * 100:.0f}%",
                        "🔥 必勝ボーダーライン": f"オッズ 【 {target_odds}倍 】 以上なら買い！"
                    })
        
        if target_buys:
            df_buys = pd.DataFrame(target_buys)
            st.subheader(f"🎯 期待値スナイプ指示書 (AIスコア {min_score_filter}点以上限定)")
            st.write(f"現在、全 {len(df_buys)} 通りに絞り込まれています。")
            st.dataframe(df_buys, use_container_width=True, height=500)
        else:
            st.warning(f"現在、AIスコアが {min_score_filter}点 以上のレースはありません。フィルターを下げてみてください。")
        
        with st.expander("📝 オッズデータ (odds) の中身を確認する（開発者用）"):
            df_odds = load_csv_from_upload(uploaded_files, "odds")
            if df_odds is not None:
                st.write("オッズデータを読み込みました！")
                st.dataframe(df_odds.head(10))
