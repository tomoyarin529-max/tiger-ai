import streamlit as st
import pandas as pd
import random
import re
import numpy as np
import requests
import json
import os
import zipfile

# ==========================================
# ⚙️ 画面設定＆【超高コントラスト・白背景デザイン】
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
    h1 { color: #1b5e20 !important; font-weight: 900 !important; text-align: center !important; font-size: 32px !important; }
    h3 { color: #2e7d32 !important; border-left: 6px solid #2e7d32; padding-left: 10px; font-weight: bold !important; }
    .stTable table { color: #000000 !important; background-color: #ffffff !important; font-size: 15px !important; }
    .stTable th { background-color: #1b5e20 !important; color: #ffffff !important; font-weight: bold !important; text-align: center !important; font-size: 16px !important;}
    .stTable td { font-size: 16px !important; text-align: center !important; font-weight: bold !important; border-bottom: 1px solid #dddddd !important; color: #000000 !important; }
    p, span, label { color: #111111 !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏇 AI 競馬『永久無敵・全自動索敵』機")

# ==========================================
# 🔑 セキュリティ ＆ LINE送信
# ==========================================
USER_ID = "U62ba9127329ab567039bd2a03cd7ac9b"
TOKEN = "鍵ファイルが見つかりません"

if "TOKEN" in st.secrets: TOKEN = st.secrets["TOKEN"]
else:
    KEY_FILE = "line_key.txt"
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f: TOKEN = f.read().strip()

def send_horse_line(msg):
    if TOKEN == "鍵ファイルが見つかりません": return
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}
        data = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
        requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
    except: pass

# ==========================================
# 🧠 AI勝率スコア計算エンジン
# ==========================================
def calc_true_ai_score(row):
    perf = str(row.get("全成績", "1-1-1-5"))
    match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', perf)
    if match:
        w1, w2, w3, L = map(int, match.groups())
        total = w1 + w2 + w3 + L
        place_rate = (w1 + w2 + w3) / total if total > 0 else 0.15
    else: place_rate = 0.15
    blood_bonus = 5 if any(x in str(row.get("馬名", "")) for x in ["カナロア", "ヘニー", "パイロ", "ブラック", "ダイヤ", "オペラ", "インパクト", "サトノ", "ハギノ"]) else 0
    weight = 54.0
    try:
        weight_str = re.sub(r'[^\d.]', '', str(row.get("負担重量", 54)))
        if weight_str: weight = float(weight_str)
    except: pass
    weight_penalty = (weight - 54.0) * 1.5
    odds_val = 5.0
    try:
        if "リアルタイム単勝オッズ" in row.index and float(row.get("リアルタイム単勝オッズ", 5.0)) > 0: 
            odds_val = float(row.get("リアルタイム単勝オッズ", 5.0))
    except: pass
    odds_effect = - (odds_val * 0.2)
    random.seed(str(row.get("馬名", "")) + str(row.get("競馬場", "")))
    return max(35, min(99, int(76 + (place_rate * 20) + blood_bonus - weight_penalty + odds_effect + random.randint(-1, 4))))

# ==========================================
# ⚙️ 作戦司令パネル
# ==========================================
st.sidebar.markdown("### ⚙️ 作戦司令パネル")
mode = st.sidebar.radio("🔥 モードを選択せよ！", ["地方競馬（実戦・当日ZIP丸投げ）", "中央競馬（JRAコピペ）", "📊 過去データ一括検証・勝因分析"])
st.sidebar.markdown("---")
target_win_rate = st.sidebar.slider("🚨 購入を発動する最低AI推奨度（％）", min_value=55, max_value=95, value=74, step=1)

# オッズ抽出用関数
def get_wide_odds_float(odds_df, track, race, horse_a, horse_b, date=None):
    try:
        b1 = min(int(float(horse_a)), int(float(horse_b)))
        b2 = max(int(float(horse_a)), int(float(horse_b)))
        cond = (odds_df["競馬場"] == track) & (odds_df["レース番号"] == int(float(race))) & (odds_df["賭式"] == "ワイド") & (odds_df["番号1"] == b1) & (odds_df["番号2"] == b2)
        if date is not None and "競走年月日" in odds_df.columns:
            cond = cond & (odds_df["競走年月日"] == date)
        df_w = odds_df[cond]
        if not df_w.empty: return float(df_w.iloc[0]["オッズ"])
    except: pass
    return 0.0

# ==========================================
# 📊 モードA ＆ B：当日の実戦モード
# ==========================================
if mode in ["地方競馬（実戦・当日ZIP丸投げ）", "中央競馬（JRAコピペ）"]:
    st.write("⚙️ 一括丸投げ仕分け ＆ 全レースワイド3点 リアルタイムオッズ完全連動・資金配分カスタムモデル")
    
    st.markdown("### 📊 本日の投資・資金配分戦略")
    st.markdown('<div class="gold-box">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: bet_strategy = st.radio("選択してください", ["ガミり防止・傾斜配分モード（推奨）", "1点一律ベタ買いモード"])
    with col2: total_budget_per_race = st.number_input("💵 1レースあたりの総投資予算（円）", min_value=300, value=1000, step=100)
    st.markdown('</div>', unsafe_allow_html=True)

    if "df_horse_raw" not in st.session_state: st.session_state.df_horse_raw = None
    if "df_race_raw" not in st.session_state: st.session_state.df_race_raw = None
    if "df_odds_raw" not in st.session_state: st.session_state.df_odds_raw = None

    uploaded_files = st.file_uploader("📋 CSVまたはZIPファイルをまとめてここにドロップ！", type=["csv", "zip"], accept_multiple_files=True)

    if uploaded_files:
        for f in uploaded_files:
            try:
                f_name_lower = f.name.lower()
                if f_name_lower.endswith('.zip'):
                    with zipfile.ZipFile(f) as z:
                        for filename in z.namelist():
                            filename_lower = filename.lower()
                            with z.open(filename) as f_in:
                                df_temp = pd.read_csv(f_in)
                                if "horselist" in filename_lower: st.session_state.df_horse_raw = df_temp
                                elif "racelist" in filename_lower: st.session_state.df_race_raw = df_temp
                                elif "odds" in filename_lower: st.session_state.df_odds_raw = df_temp
                elif f_name_lower.endswith('.csv'):
                    df_temp = pd.read_csv(f)
                    if "horselist" in f_name_lower: st.session_state.df_horse_raw = df_temp
                    elif "racelist" in f_name_lower: st.session_state.df_race_raw = df_temp
                    elif "odds" in f_name_lower: st.session_state.df_odds_raw = df_temp
            except Exception as e: st.error(f"❌ エラー: {e}")

    df_horse_raw = st.session_state.df_horse_raw
    df_race_raw = st.session_state.df_race_raw
    df_odds_raw = st.session_state.df_odds_raw

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"{'🟢 馬データ読込済' if df_horse_raw is not None else '⚪ 馬データ未読'}")
    with c2: st.markdown(f"{'🟢 レース一覧読込済' if df_race_raw is not None else '⚪ レース一覧未読'}")
    with c3: st.markdown(f"{'🟢 オッズ連動済' if df_odds_raw is not None else '⚪ オッズ未読'}")

    if df_horse_raw is not None and df_race_raw is not None:
        df_horse_raw = df_horse_raw.copy()
        df_race_raw = df_race_raw.copy()
        
        if df_odds_raw is not None:
            df_odds_raw = df_odds_raw.copy()
            if "賭式" in df_odds_raw.columns:
                df_win_odds = df_odds_raw[df_odds_raw["賭式"] == "単勝"][["競馬場", "レース番号", "馬番", "オッズ"]].rename(columns={"オッズ": "リアルタイム単勝オッズ"})
                df_horse_raw = pd.merge(df_horse_raw, df_win_odds, on=["競馬場", "レース番号", "馬番"], how="left")
                
        df_horse_raw["AI勝率スコア"] = df_horse_raw.apply(calc_true_ai_score, axis=1)
        all_wide_matches = []
        tracks = df_horse_raw["競馬場"].unique()
        
        for track in tracks:
            df_track_only = df_horse_raw[df_horse_raw["競馬場"] == track]
            r_list = sorted(df_track_only["レース番号"].dropna().unique())
            for r in r_list:
                df_r = df_track_only[df_track_only["レース番号"] == int(float(r))]
                if len(df_r) >= 3:
                    sorted_horses = df_r.sort_values(by="AI勝率スコア", ascending=False).reset_index(drop=True)
                    top3 = sorted_horses.head(3)
                    n1, n2, n3 = top3.loc[0, '馬番'], top3.loc[1, '馬番'], top3.loc[2, '馬番']
                    avg_score = int((top3.loc[0, "AI勝率スコア"] + top3.loc[1, "AI勝率スコア"] + top3.loc[2, "AI勝率スコア"]) / 3)
                    
                    random.seed(int(avg_score))
                    win_rate = max(55, min(97, int(avg_score * 0.78 + random.randint(-1, 2))))
                    
                    race_time_str = "時刻不明"
                    if df_race_raw is not None and not df_race_raw.empty:
                        df_time_search = df_race_raw[(df_race_raw["競馬場"] == track) & (df_race_raw["レース番号"] == int(float(r)))]
                        if not df_time_search.empty:
                            race_time_str = str(df_time_search.iloc[0]["発走時刻"]) if "発走時刻" in df_time_search.columns else str(df_time_search.iloc[0]["発走予定時刻"])

                    odds12 = get_wide_odds_float(df_odds_raw, track, r, n1, n2)
                    odds13 = get_wide_odds_float(df_odds_raw, track, r, n1, n3)
                    odds23 = get_wide_odds_float(df_odds_raw, track, r, n2, n3)
                    
                    amt12, amt23, amt13 = 100, 100, 100
                    if bet_strategy == "ガミり防止・傾斜配分モード（推奨）" and odds12 > 0 and odds13 > 0 and odds23 > 0:
                        try:
                            sum_inv = (1.0 / odds12) + (1.0 / odds13) + (1.0 / odds23)
                            amt12 = max(100, int(round((total_budget_per_race / odds12) / sum_inv / 100) * 100))
                            amt13 = max(100, int(round((total_budget_per_race / odds13) / sum_inv / 100) * 100))
                            amt23 = max(100, int(round((total_budget_per_race / odds23) / sum_inv / 100) * 100))
                        except: pass

                    str12 = f"① {int(float(n1))}-{int(float(n2))} [{odds12}倍] ➡️ 【{amt12}円購入】" if odds12 > 0 else f"① {int(float(n1))}-{int(float(n2))} ➡️ 【100円購入】"
                    str13 = f"② {int(float(n1))}-{int(float(n3))} [{odds13}倍] ➡️ 【{amt13}円購入】" if odds13 > 0 else f"② {int(float(n1))}-{int(float(n3))} ➡️ 【100円購入】"
                    str23 = f"③ {int(float(n2))}-{int(float(n3))} [{odds23}倍] ➡️ 【{amt23}円購入】" if odds23 > 0 else f"③ {int(float(n2))}-{int(float(n3))} ➡️ 【100円購入】"
                    wide_combos_rich = f"{str12}\n{str13}\n{str23}"
                    
                    win_odds_val = top3.loc[0, 'リアルタイム単勝オッズ'] if 'リアルタイム単勝オッズ' in top3.columns else 0.0
                    win_odds_str = f" [{win_odds_val}倍]" if float(win_odds_val) > 0 else ""
                    
                    # 🛠️ 【防衛線】オッズデータが欠損・無い場合でもKeyErrorを絶対に起こさない安全コードに完全置換！
                    if "リアルタイム単勝オッズ" in df_r.columns:
                        df_ana_candidates = df_r[df_r["リアルタイム単勝オッズ"].fillna(0) >= 10.0]
                        ana_horse_row = df_ana_candidates.sort_values(by="AI勝率スコア", ascending=False).iloc[0] if not df_ana_candidates.empty else (sorted_horses.loc[3] if len(sorted_horses) >= 4 else None)
                    else:
                        ana_horse_row = sorted_horses.loc[3] if len(sorted_horses) >= 4 else None
                    
                    if ana_horse_row is not None:
                        ana_odds = ana_horse_row.get('リアルタイム単勝オッズ', 0.0)
                        ana_odds_str = f" [{ana_odds}倍]" if pd.notna(ana_odds) and float(ana_odds) > 0 else ""
                        ana_signal = f"🔥 LOCKON!! 【 {int(float(ana_horse_row['馬番']))}番 】 ({ana_horse_row['馬名']}){ana_odds_str}"
                    else:
                        ana_signal = "ーー（安全第一・見送り）"
                    
                    if win_rate >= target_win_rate:
                        all_wide_matches.append({
                            "対象レース": f"{track} {int(float(r))}R",
                            "発走時刻": race_time_str,
                            "ワイド 3点買い目（オッズ＆推奨購入額）": wide_combos_rich,
                            "大本命馬": f"{int(float(n1))}番 ({top3.loc[0, '馬名']}){win_odds_str}",
                            "AI推奨度": f"{win_rate} ％",
                            "🔥 大穴単勝 (100円)": ana_signal
                        })                    

        if all_wide_matches:
            st.table(pd.DataFrame(all_wide_matches)[["対象レース", "発走時刻", "ワイド 3点買い目（オッズ＆推奨購入額）", "大本命馬", "AI推奨度", "🔥 大穴単勝 (100円)"]])
            
            line_msg = "🏇【AI・クラウド要塞報告】🏇\n"
            for match in all_wide_matches:
                line_msg += f"\n■ {match['対象レース']} (🕒発走: {match['発走時刻']}) \n"
                line_msg += f"👉AI推奨度: {match['AI推奨度']}\n"
                line_msg += f"{match['ワイド 3点買い目（オッズ＆推奨購入額）']}\n"
                line_msg += f"★大本命: {match['大本命馬']}\n"
                line_msg += f"🔥大穴単勝: {match['🔥 大穴単勝 (100円)']}\n"
                line_msg += "----------------------------------\n"
            
            if df_odds_raw is not None: 
                send_horse_line(line_msg)

# ==========================================
# 📊 モードC：【大将軍専用】過去データ一括検証・勝因分析モード
# ==========================================
elif mode == "📊 過去データ一括検証・勝因分析":
    st.markdown("### 🏯 過去ビッグデータ一括格納・自動検証エンジン")
    st.write("過去のレースデータやオッズのZIPファイルを何ヶ月分でもここにまとめてドロップしてください。AIが自動で全結合し、トータル収支を逆算します。")
    
    archive_files = st.file_uploader("📋 過去のZIP/CSVアーカイブをここに一括ドロップ（1年分でもOK！）", type=["zip", "csv"], accept_multiple_files=True, key="archive_uploader")
    
    if archive_files:
        list_horse = []
        list_race = []
        list_payback = []
        list_odds = []
        
        with st.spinner("⏳ 膨大なデータを解凍・全自動結合中...（大将軍、じっとお待ちくだされ！）"):
            for f in archive_files:
                f_name_lower = f.name.lower()
                if f_name_lower.endswith('.zip'):
                    with zipfile.ZipFile(f) as z:
                        for filename in z.namelist():
                            filename_lower = filename.lower()
                            with z.open(filename) as f_in:
                                try:
                                    df_temp = pd.read_csv(f_in)
                                    if "horselist" in filename_lower: list_horse.append(df_temp)
                                    elif "racelist" in filename_lower: list_race.append(df_temp)
                                    elif "payback" in filename_lower: list_payback.append(df_temp)
                                    elif "odds" in filename_lower: list_odds.append(df_temp)
                                except: pass
                elif f_name_lower.endswith('.csv'):
                    try:
                        df_temp = pd.read_csv(f)
                        if "horselist" in f_name_lower: list_horse.append(df_temp)
                        elif "racelist" in f_name_lower: list_race.append(df_temp)
                        elif "payback" in f_name_lower: list_payback.append(df_temp)
                        elif "odds" in f_name_lower: list_odds.append(df_temp)
                    except: pass
            
            df_master_horse = pd.concat(list_horse, ignore_index=True) if list_horse else None
            df_master_race = pd.concat(list_race, ignore_index=True) if list_race else None
            df_master_payback = pd.concat(list_payback, ignore_index=True) if list_payback else None
            df_master_odds = pd.concat(list_odds, ignore_index=True) if list_odds else None

        # 🛠️ 【過去オッズ無し問題・大改善】オッズデータが無くても、馬データと払戻金データがあれば完全検証できるように仕様を大幅強化！
        if df_master_horse is not None and df_master_payback is not None:
            st.success(f"🟢 索敵成功！馬データ {len(df_master_horse)}行 / 払戻データ {len(df_master_payback)}行 を完全統合しました！")
            if df_master_odds is not None:
                st.info(f"📊 オッズデータ {len(df_master_odds)}行 も連動（傾斜配分シミュレーション有効）")
            else:
                st.warning("⚠️ 過去オッズデータが未検出（または無いレース）のため、一律ベタ買い（1点100円・計300円）としてシミュレーションを行います！")
            
            if st.button("⚔️ 過去データ検証作戦（バックテスト）を開始せよ！"):
                backtest_results = []
                
                with st.spinner("🧠 AIが過去の全レースを脳内シミュレーション中..."):
                    # 単勝オッズをマージ (オッズデータがある場合のみ)
                    if df_master_odds is not None and "賭式" in df_master_odds.columns:
                        df_win_odds = df_master_odds[df_master_odds["賭式"] == "単勝"][["競馬場", "競走年月日", "レース番号", "馬番", "オッズ"]].rename(columns={"オッズ": "リアルタイム単勝オッズ"})
                        df_master_horse = pd.merge(df_master_horse, df_win_odds, on=["競馬場", "競走年月日", "レース番号", "馬番"], how="left")
                    
                    df_master_horse["AI勝率スコア"] = df_master_horse.apply(calc_true_ai_score, axis=1)
                    grouped = df_master_horse.groupby(["競馬場", "競走年月日", "レース番号"])
                    
                    for (track, date, r), df_r in grouped:
                        if len(df_r) >= 3:
                            sorted_horses = df_r.sort_values(by="AI勝率スコア", ascending=False).reset_index(drop=True)
                            top3 = sorted_horses.head(3)
                            n1, n2, n3 = top3.loc[0, '馬番'], top3.loc[1, '馬番'], top3.loc[2, '馬番']
                            avg_score = int((top3.loc[0, "AI勝率スコア"] + top3.loc[1, "AI勝率スコア"] + top3.loc[2, "AI勝率スコア"]) / 3)
                            
                            random.seed(int(avg_score))
                            win_rate = max(55, min(97, int(avg_score * 0.78 + random.randint(-1, 2))))
                            
                            if win_rate >= target_win_rate:
                                total_budget = 1000
                                amt12, amt13, amt23 = 100, 100, 100
                                
                                # 過去オッズデータが存在する場合のみ傾斜配分を行う
                                if df_master_odds is not None:
                                    odds12 = get_wide_odds_float(df_master_odds, track, r, n1, n2, date)
                                    odds13 = get_wide_odds_float(df_master_odds, track, r, n1, n3, date)
                                    odds23 = get_wide_odds_float(df_master_odds, track, r, n2, n3, date)
                                    
                                    if odds12 > 0 and odds13 > 0 and odds23 > 0:
                                        try:
                                            sum_inv = (1.0 / odds12) + (1.0 / odds13) + (1.0 / odds23)
                                            amt12 = max(100, int(round((total_budget / odds12) / sum_inv / 100) * 100))
                                            amt13 = max(100, int(round((total_budget / odds13) / sum_inv / 100) * 100))
                                            amt23 = max(100, int(round((total_budget / odds23) / sum_inv / 100) * 100))
                                        except: pass
                                
                                actual_bet = amt12 + amt13 + amt23
                                
                                # 実際の払戻と照合
                                df_pb = df_master_payback[(df_master_payback["競馬場"] == track) & (df_master_pay
