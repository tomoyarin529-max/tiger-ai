import streamlit as st
import pandas as pd
import numpy as np
import re
import zipfile
import io

# ==========================================
# 1. 画面の基本設定
# ==========================================
st.set_page_config(page_title="大将軍の要塞・三戦場特化型", layout="wide")
st.title("🏯 大将軍の要塞 ・ 三戦場特化型絶対防衛スキャナー")
st.write("過去1.5年のデータが証明した聖地『金沢・高知・佐賀』のみを監視し、馬体重の地雷馬を自動排除する最終形態です。")

# 📂 サイドバー・作戦指令部
st.sidebar.header("⚔️ 聖地防衛指令本部")

# 過去データで最も優秀だった3場のみを厳選ロック
target_tracks = ["金沢", "高知", "佐賀"]
st.sidebar.success(f"監視対象：{', '.join(target_tracks)}競馬場（限定解放中）")

min_score_filter = st.sidebar.slider(
    "🔥 最低AIスコアの足切りライン", 
    min_value=50, 
    max_value=99, 
    value=85,
    help="このラインを下回る『自信のない馬』は画面から完全消去されます。"
)

st.sidebar.markdown("---")
st.sidebar.info("🎒 **軍師ジェミの進言**\n\nこの要塞はベース回収率が極めて高い3場しか表示しません。画面に獲物が点灯したら、直前オッズを確認し**【 1.8倍以上 】**の歪みがある時だけ冷徹にスナイプしてください！")

# ==========================================
# 🧠 魂のV3エンジン（馬体重デトックス機能付き）
# ==========================================
def calc_ai_score_v3(row):
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
    except: pass
    try:
        pop_val = row.get("人気", 5)
        if pd.notna(pop_val) and str(pop_val) != "nan":
            score -= (float(pop_val) * 0.5)
    except: pass
    
    base_score = max(35, min(99, int(score)))
    
    # 💥 馬体重増減による危険察知デトックス
    try:
        zongen_str = str(row.get("馬体重増減", "")).replace(' ', '')
        match = re.search(r'([+-]?\d+)', zongen_str)
        if match:
            val = int(match.group(1))
            if val >= 10:
                base_score -= 15  # 激太りエリートは-15点の大減点！
            elif val <= -10:
                base_score -= 8   # 激ヤセ馬は-8点の減点！
    except: pass
    
    return max(35, min(99, int(base_score)))

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
                            try: df_list.append(pd.read_csv(f, encoding="shift_jis"))
                            except: f.seek(0); df_list.append(pd.read_csv(f, encoding="utf-8"))
        elif target_keyword in file.name and file.name.endswith('.csv'):
            try: df_list.append(pd.read_csv(file, encoding="shift_jis"))
            except: file.seek(0); df_list.append(pd.read_csv(file, encoding="utf-8"))
    if df_list: return pd.concat(df_list, ignore_index=True)
    return None

# ==========================================
# 4. メインロジック
# ==========================================
uploaded_files = st.file_uploader(
    "📂 当日の 【race.zip】 または 【horselist.csv】 を突撃させてください！", 
    type=["zip", "csv"], 
    accept_multiple_files=True
)

if uploaded_files:
    df_horse = load_csv_from_upload(uploaded_files, "horselist")
    
    if df_horse is not None:
        # V3エンジン適用
        df_horse["AIスコア_V3"] = df_horse.apply(calc_ai_score_v3, axis=1)
        st.success("✅ 三戦場特化型・地雷除去フィルターのリアルタイム展開に成功しました！")
        
        target_buys = []
        grouped = df_horse.groupby(["競馬場", "レース番号"])
        
        for (track, race_num), group in grouped:
            # 🎯 【鉄の掟】金沢・高知・佐賀 以外のレースは最初から完全無視！
            if track not in target_tracks:
                continue
            
            if len(group) < 3: continue
            
            # 最高得点馬を抽出
            top_horse = group.sort_values(by="AIスコア_V3", ascending=False).iloc[0]
            max_score = top_horse["AIスコア_V3"]
            horse_num = int(top_horse["馬番"])
            horse_name = top_horse.get("馬name", top_horse.get("馬名", "不明"))
            jockey_name = top_horse.get("騎手名", "不明")
            weight_change = top_horse.get("馬体重増減", "不明")
            actual_pop = top_horse.get("人気", "不明")
            
            # 足切りライン判定
            if max_score < min_score_filter:
                continue
                
            # 推定生存率の設定
            if max_score >= 95: est_rate = "69.5%"
            elif max_score >= 90: est_rate = "60.0%"
            else: est_rate = "52.0%"
            
            # 1番人気に対する警告表示用の文言
            pop_alert = "⚠️ 過剰人気の可能性アリ" if str(actual_pop) in ["1", "1.0", "1番人気"] else "🟢 歪み発生の期待大"
            
            target_buys.append({
                "戦場 (競馬場)": track,
                "レース": f"{race_num}R",
                "最終AIスコア": max_score,
                "精鋭馬番": f"{horse_num}番 ({horse_name})",
                "当日の体重増減": weight_change,
                "事前人気": f"{actual_pop}番人気",
                "オッズ判定": pop_alert,
                "🎯 推定複勝率": est_rate,
                "🔥 絶対防衛境界線": "直前複勝オッズ【 1.8倍 】以上なら撃て！"
            })
        
        # 指示書の出力
        if target_buys:
            df_buys = pd.DataFrame(target_buys)
            st.subheader("🎯 三戦場厳選・期待値確定スナイプ指示書")
            st.write(f"現在、金沢・高知・佐賀の中から地雷をすり抜けた精鋭が全 {len(df_buys)} 頭捕捉されています。")
            
            # 表を綺麗に変飾
            st.dataframe(df_buys, use_container_width=True, height=400)
        else:
            st.warning(f"現在、三戦場の中にAIスコア {min_score_filter}点 以上の条件を満たす精鋭はいません。")
