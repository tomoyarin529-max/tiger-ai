import streamlit as st
import pandas as pd
import random
import re
import numpy as np
import zipfile

# ==========================================
# ⚙️ 1. 画面設定 ＆ 超高コントラストデザイン
# ==========================================
st.set_page_config(page_title="AI永久無敵ハンター", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #f7f9f8 !important; color: #111111 !important; }
    .gold-box {
        background-color: #ffffff !important; border: 3px solid #1b5e20 !important;
        padding: 20px !important; border-radius: 12px !important; margin-bottom: 20px !important;
        color: #111111 !important;
    }
    h1 { color: #1b5e20 !important; font-weight: 900 !important; text-align: center !important; }
    h3 { color: #2e7d32 !important; border-left: 6px solid #2e7d32; padding-left: 10px; font-weight: bold !important; }
    .stTable table { color: #000000 !important; background-color: #ffffff !important; }
    .stTable th { background-color: #1b5e20 !important; color: #ffffff !important; text-align: center !important; }
    .stTable td { text-align: center !important; font-weight: bold !important; color: #000000 !important; }
    p, span, label { color: #111111 !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏇 AI競馬『勝因分析 ＆ 的中率向上』機")

# ==========================================
# 🧠 2. AI予測ロジック
# ==========================================
def calc_ai_score(row):
    place_rate = 0.15
    try:
        perf = str(row.get("全成績", "0-0-0-0"))
        if pd.notna(perf) and perf != "nan":
            match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', perf)
            if match:
                w1, w2, w3, L = map(int, match.groups())
                total = w1 + w2 + w3 + L
                if total > 0:
                    place_rate = (w1 + w2 + w3) / total
    except:
        place_rate = 0.15

    blood_bonus = 0
    try:
        u_name = str(row.get("馬名", ""))
        if pd.notna(u_name) and u_name != "nan":
            names = ["カナロア", "ヘニー", "パイロ", "ブラック", "ダイヤ", "オペラ", "インパクト", "サトノ", "ハギノ"]
            if any(x in u_name for x in names):
                blood_bonus = 5
    except:
        blood_bonus = 0

    weight_penalty = 0.0
    try:
        w_val = row.get("負担重量", 54)
        if pd.notna(w_val) and str(w_val) != "nan":
            w_str = re.sub(r'[^\d.]', '', str(w_val))
            if w_str:
                weight = float(w_str)
                weight_penalty = (weight - 54.0) * 1.5
    except:
        weight_penalty = 0.0

    pop_effect = -2.5
    try:
        pop_val = row.get("人気", 5)
        if pd.notna(pop_val) and str(pop_val) != "nan":
            pop = float(pop_val)
            if not np.isnan(pop):
                pop_effect = - (pop * 0.5)
    except:
        pop_effect = -2.5

    rand_val = random.randint(-1, 3)

    try:
        total_score = 76.0 + (place_rate * 20.0) + float(blood_bonus) - float(weight_penalty) + float(pop_effect) + float(rand_val)
        if np.isnan(total_score) or np.isinf(total_score):
            return 70
        return max(35, min(99, int(total_score)))
    except:
        return 70

# ==========================================
# 📂 3. ZIP/CSV一括全自動読み込み関数
# ==========================================
def load_horselist_files(uploaded_files):
    dfs = []
    for f in uploaded_files:
        if f.name.lower().endswith('.zip'):
            with zipfile.ZipFile(f) as z:
                for name in z.namelist():
                    if "horselist" in name.lower():
                        dfs.append(pd.read_csv(z.open(name)))
        elif "horselist" in f.name.lower():
            dfs.append(pd.read_csv(f))
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return None

# ==========================================
# ⚙️ 4. 作戦司令パネル（サイドバー）
# ==========================================
st.sidebar.markdown("### ⚙️ 作戦司令パネル")
mode = st.sidebar.radio("🔥 モードを選択せよ！", ["📊 過去レース勝因分析（オッズ不要）", "🔮 未来レース一発予想"])

st.sidebar.markdown("---")
# 🚨 大将軍の戦略：AIの自信度でレース自体を厳選し、勝率90%を狙うスライダー
min_ai_score = st.sidebar.slider("🚨 AI自信度でレースを厳選（勝率90%超へ）", min_value=70, max_value=95, value=80, step=1)

uploaded_files = st.file_uploader("📋 horselistのZIPまたはCSVファイルをここにドロップ！", type=["csv", "zip"], accept_multiple_files=True)

# ==========================================
# 📊 5. メインルーチン
# ==========================================
if uploaded_files:
    df_master = load_horselist_files(uploaded_files)
    if df_master is not None:
        st.success("🟢 索敵成功！馬データを読み込みました。")
        
        df_master["AIスコア"] = df_master.apply(calc_ai_score, axis=1)

        # ------------------------------------------
        # 【A】過去レース勝因分析モード
        # ------------------------------------------
        if mode == "📊 過去レース勝因分析（オッズ不要）":
            st.subheader("📊 過去データに対するAI予測精度の答え合わせ")
            
            if "着順" in df_master.columns:
                df_master["着順_num"] = pd.to_numeric(df_master["着順"], errors='coerce')
                df_valid = df_master[df_master["着順_num"].notna()].copy()
                
                if not df_valid.empty:
                    total_races = 0
                    hit_races = 0
                    triple_races = 0
                    
                    grouped = df_valid.groupby(["競馬場", "競走年月日", "レース番号"])
                    for (track, date, r), group in grouped:
                        if len(group) >= 3:
                            top3_ai = group.sort_values(by="AIスコア", ascending=False).head(3)
                            
                            # 🚨 厳選フィルターの適用（過去検証）
                            if top3_ai.iloc[0]["AIスコア"] < min_ai_score:
                                continue
                                
                            total_races += 1
                            actual_ranks = top3_ai["着順_num"].values
                            
                            inside_3 = sum(1 for rank in actual_ranks if rank <= 3)
                            if inside_3 > 0:
                                hit_races += 1
                            if inside_3 == 3:
                                triple_races += 1
                    
                    st.markdown('<div class="gold-box">', unsafe_allow_html=True)
                    st.write(f"📈 **厳選された対象レース数:** {total_races} レース")
                    if total_races > 0:
                        any_hit_rate = (hit_races / total_races) * 100
                        triple_hit_rate = (triple_races / total_races) * 100
                        st.write(f"🎯 **AI上位3頭のうち、1頭以上が3着以内に入った確率 (ワイド的中率):** {any_hit_rate:.1f} %")
                        st.write(f"🔥 **AI上位3頭が1, 2, 3着を完全独占した確率 (トリプル総取り):** {triple_hit_rate:.1f} %")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning("⚠️ 読み込んだデータに、レース結果（着順）が含まれていません。")
            else:
                st.warning("⚠️ データに「着順」カラムがありません。")

        # ------------------------------------------
        # 【B】未来レース一発予想モード
        # ------------------------------------------
        elif mode == "🔮 未来レース一発予想":
            st.subheader("🔮 次回開催レースのAI自動索敵・本命3頭")
            
            predict_results = []
            group_cols = ["競馬場", "レース番号"]
            if "競走年月日" in df_master.columns:
                group_cols = ["競馬場", "競走年月日", "レース番号"]
                
            grouped = df_master.groupby(group_cols)
            for keys, group in grouped:
                # 自動終了判定
                if "着順" in group.columns:
                    has_result = pd.to_numeric(group["着順"], errors='coerce').notna().any()
                    if has_result:
                        continue

                if len(group) >= 3:
                    top3 = group.sort_values(by="AIスコア", ascending=False).head(3)
                    
                    # 🚨 大将軍の戦略：大本命馬のスコアが基準未満ならレースごと非表示！
                    if top3.iloc[0]["AIスコア"] < min_ai_score:
                        continue

                    h_list = []
                    for _, row in top3.iterrows():
                        try:
                            b_num = int(float(row.get("馬番", 0)))
                        except:
                            b_num = row.get("馬番", 0)
                        h_list.append(f"{b_num}番({row.get('馬名', '')})")
                    horses_str = " , ".join(h_list)
                    
                    if len(group_cols) == 3:
                        track_val, date_val, r_val = keys
                        race_name = f"{date_val} {track_val} {r_val}R"
                    else:
                        track_val, r_val = keys
                        race_name = f"{track_val} {r_val}R"
                        
                    # 画面表示用に1番手のスコアをちょっと添える
                    b_score = top3.iloc[0]["AIスコア"]
                    predict_results.append({
                        "対象レース": race_name, 
                        "AI推奨馬上位3頭": horses_str,
                        "大本命の自信度": f"{b_score}点"
                    })
                    
            if predict_results:
                st.table(pd.DataFrame(predict_results))
            else:
                st.info("🔮 条件を満たす厳選レースがありません。スライダーの数値を少し下げてみてください。")
else:
    st.info("⚪ 準備完了。`horselist` ファイルを上にドロップしてください。")
