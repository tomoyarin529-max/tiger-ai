import streamlit as st
import pandas as pd
import random
import re
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
    .stTable th { background-color: #1b5e20 !important; color: #ffffff !important; font-weight: bold !important; text-align: center !important; }
    .stTable td { text-align: center !important; font-weight: bold !important; color: #000000 !important; }
    p, span, label { color: #111111 !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏇 AI競馬『勝因分析 ＆ 的中率向上』機")

# ==========================================
# 🧠 2. AI予測ロジック（ここをチューニングして未来を支配する）
# ==========================================
def calc_ai_score(row):
    # 過去の戦績から複勝率を計算
    perf = str(row.get("全成績", "0-0-0-0"))
    match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', perf)
    if match:
        w1, w2, w3, L = map(int, match.groups())
        total = w1 + w2 + w3 + L
        place_rate = (w1 + w2 + w3) / total if total > 0 else 0.15
    else:
        place_rate = 0.15

    # 血統ボーナス
    names = ["カナロア", "ヘニー", "パイロ", "ブラック", "ダイヤ", "オペラ", "インパクト", "サトノ", "ハギノ"]
    blood_bonus = 5 if any(x in str(row.get("馬名", "")) for x in names) else 0

    # 斤量ペナルティ
    weight = 54.0
    try:
        w_str = re.sub(r'[^\d.]', '', str(row.get("負担重量", 54)))
        if w_str:
            weight = float(w_str)
    except:
        pass
    weight_penalty = (weight - 54.0) * 1.5

    # 人気要素（過去データにある確定人気、未来データにある事前人気を統合評価）
    pop = 5.0
    try:
        pop = float(row.get("人気", 5))
    except:
        pass
    pop_effect = - (pop * 0.5)

    random.seed(str(row.get("馬名", "")) + str(row.get("競馬場", "")))
    return max(35, min(99, int(75 + (place_rate * 25) + blood_bonus - weight_penalty + pop_effect + random.randint(-1, 3))))

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
# ⚙️ 4. モード選択パネル
# ==========================================
st.sidebar.markdown("### ⚙️ 作戦司令パネル")
mode = st.sidebar.radio("🔥 モードを選択せよ！", ["📊 過去レース勝因分析（オッズ不要）", "🔮 未来レース一発予想"])

uploaded_files = st.file_uploader("📋 horselistのZIPまたはCSVファイルをここにドロップ！", type=["csv", "zip"], accept_multiple_files=True)

# ==========================================
# 📊 5. メインルーチン
# ==========================================
if uploaded_files:
    df_master = load_horselist_files(uploaded_files)
    if df_master is not None:
        st.success(f"🟢 索敵成功！ 合計 {len(df_master)} 行の馬データを統合しました。")
        
        # すべての馬のAIスコアを計算
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
                    
                    # レースごとにグループ化して、AI上位3頭の「実際の着順」をチェック
                    grouped = df_valid.groupby(["競馬場", "競走年月日", "レース番号"])
                    for (track, date, r), group in grouped:
                        if len(group) >= 3:
                            total_races += 1
                            top3_ai = group.sort_values(by="AIスコア", ascending=False).head(3)
                            actual_ranks = top3_ai["着順_num"].values
                            
                            # 3着以内に入った頭数をカウント
                            inside_3 = sum(1 for rank in actual_ranks if rank <= 3)
                            if inside_3 > 0:
                                hit_races += 1
                            if inside_3 == 3:
                                triple_races += 1
                    
                    st.markdown('<div class="gold-box">', unsafe_allow_html=True)
                    st.write(f"📈 **検証対象レース数:** {total_races} レース")
                    if total_races > 0:
                        st.write(f"🎯 **AI上位3頭のうち、1頭以上が3着以内に入った確率 (ワイド的中率):** {hit_races / total_races * 100:.1f} %")
                        st.write(f"🔥 **AI上位3頭が1, 2, 3着を完全独占した確率 (トリプル総取り):** {triple_races / total_races * 100:.1f} %")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # 統計的な影響度分析
                    st.write("💡 **どの要素が「実際の着順」に強く好影響を与えているか（相関係数）**")
                    st.write("※マイナスに数値が大きいほど、「その数値が高いほど1着に近い」という強力な勝因因子であることを示します。")
                    corrs = df_valid[["着順_num", "AIスコア", "人気", "負担重量"]].corr()["着順_num"]
                    st.table(corrs)
                else:
                    st.warning("⚠️ 読み込んだデータに、レース結果（着順）が含まれていません。過去レースのデータを投入してください。")
            else:
                st.warning("⚠️ データに「着順」カラムがありません。")

        # ------------------------------------------
        # 【B】未来レース一発予想モード
        # ------------------------------------------
        elif mode == "🔮 未来レース一発予想":
            st.subheader("🔮 次回開催レースのAI自動索敵・本命3頭")
            
            predict_results = []
            grouped = df_master.groupby(["競馬場", "レース番号"])
            for (track, r), group in grouped:
                if len(group) >= 3:
                    top3 = group.sort_values(by="AIスコア", ascending=False).head(3)
                    h_list = []
                    for _, row in top3.iterrows():
                        try:
                            b_num = int(float(row.get("馬番", 0)))
                        except:
                            b_num = row.get("馬番", 0)
                        h_list.append(f"{b_num}番({row.get('馬名', '')})")
                    horses_str = " , ".join(h_list)
                    predict_results.append({"競馬場": track, "レース": f"{r}R", "AI推奨馬上位3頭": horses_str})
                    
            if predict_results:
                st.table(pd.DataFrame(predict_results))
            else:
                st.info("⚪ レースの形式が正しくありません（1レースに3頭以上出走しているデータが必要です）。")
    else:
        st.info("⚪ ファイルを読み込めませんでした。ファイル名に 'horselist' が含まれているか確認してください。")
else:
    st.info("⚪ 準備完了。過去または未来の `horselist` ファイル（ZIPのままでOK！）を上にドロップしてください。")
