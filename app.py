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
# 🔑 2. セキュリティ ＆ LINE送信
# ==========================================
USER_ID = "U62ba9127329ab567039bd2a03cd7ac9b"
TOKEN = "鍵ファイルが見つかりません"

if "TOKEN" in st.secrets:
    TOKEN = st.secrets["TOKEN"]
else:
    if os.path.exists("line_key.txt"):
        with open("line_key.txt", "r", encoding="utf-8") as f:
            TOKEN = f.read().strip()

def send_horse_line(msg):
    if TOKEN == "鍵ファイルが見つかりません":
        return
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}
        data = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
        requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
    except:
        pass

# ==========================================
# 🧠 3. AI勝率スコア計算エンジン
# ==========================================
def calc_true_ai_score(row):
    perf = str(row.get("全成績", "1-1-1-5"))
    match = re.match(r'(\d+)-(\d+)-(\d+)-(\d+)', perf)
    if match:
        w1, w2, w3, L = map(int, match.groups())
        total = w1 + w2 + w3 + L
        place_rate = (w1 + w2 + w3) / total if total > 0 else 0.15
    else:
        place_rate = 0.15
    
    names = ["カナロア", "ヘニー", "パイロ", "ブラック", "ダイヤ", "オペラ", "インパクト", "サトノ", "ハギノ"]
    blood_bonus = 5 if any(x in str(row.get("馬名", "")) for x in names) else 0
    
    weight = 54.0
    try:
        weight_str = re.sub(r'[^\d.]', '', str(row.get("負担重量", 54)))
        if weight_str:
            weight = float(weight_str)
    except:
        pass
    weight_penalty = (weight - 54.0) * 1.5
    
    odds_val = 5.0
    try:
        if float(row.get("リアルタイム単勝オッズ", 5.0)) > 0:
            odds_val = float(row.get("リアルタイム単勝オッズ", 5.0))
    except:
        pass
    odds_effect = - (odds_val * 0.2)
    
    random.seed(str(row.get("馬名", "")) + str(row.get("競馬場", "")))
    return max(35, min(99, int(76 + (place_rate * 20) + blood_bonus - weight_penalty + odds_effect + random.randint(-1, 4))))

# ==========================================
# 🔍 4. オッズ抽出用関数
# ==========================================
def get_wide_odds_float(odds_df, track, race, horse_a, horse_b, date=None):
    try:
        b1 = min(int(float(horse_a)), int(float(horse_b)))
        b2 = max(int(float(horse_a)), int(float(horse_b)))
        cond = (odds_df["競馬場"] == track) & \
               (odds_df["レース番号"] == int(float(race))) & \
               (odds_df["賭式"] == "ワイド") & \
               (odds_df["番号1"] == b1) & \
               (odds_df["番号2"] == b2)
               
        if date is not None and "競走年月日" in odds_df.columns:
            cond = cond & (odds_df["競走年月日"] == date)
        df_w = odds_df[cond]
        if not df_w.empty:
            return float(df_w.iloc[0]["オッズ"])
    except:
        pass
    return 0.0

# ==========================================
# 📂 5. 当日ファイル全自動仕分け関数
# ==========================================
def process_current_files(uploaded_files):
    df_h, df_r, df_o = None, None, None
    for f in uploaded_files:
        name_lower = f.name.lower()
        if name_lower.endswith('.zip'):
            with zipfile.ZipFile(f) as z:
                for filename in z.namelist():
                    fn_lower = filename.lower()
                    with z.open(filename) as f_in:
                        df_temp = pd.read_csv(f_in)
                        if "horselist" in fn_lower: df_h = df_temp
                        elif "racelist" in fn_lower: df_r = df_temp
                        elif "odds" in fn_lower: df_o = df_temp
        elif name_lower.endswith('.csv'):
            df_temp = pd.read_csv(f)
            if "horselist" in name_lower: df_h = df_temp
            elif "racelist" in name_lower: df_r = df_temp
            elif "odds" in name_lower: df_o = df_temp
    return df_h, df_r, df_o

# ==========================================
# 📊 6. 過去アーカイブ全自動全結合関数
# ==========================================
def process_archive_files(archive_files):
    list_horse, list_race, list_payback, list_odds = [], [], [], []
    for f in archive_files:
        name_lower = f.name.lower()
        if name_lower.endswith('.zip'):
            with zipfile.ZipFile(f) as z:
                for filename in z.namelist():
                    fn_lower = filename.lower()
                    with z.open(filename) as f_in:
                        try:
                            df_temp = pd.read_csv(f_in)
                            if "horselist" in fn_lower: list_horse.append(df_temp)
                            elif "racelist" in fn_lower: list_race.append(df_temp)
                            elif "payback" in fn_lower: list_payback.append(df_temp)
                            elif "odds" in fn_lower: list_odds.append(df_temp)
                        except: pass
        elif name_lower.endswith('.csv'):
            try:
                df_temp = pd.read_csv(f)
                if "horselist" in name_lower: list_horse.append(df_temp)
                elif "racelist" in name_lower: list_race.append(df_temp)
                elif "payback" in name_lower: list_payback.append(df_temp)
                elif "odds" in name_lower: list_odds.append(df_temp)
            except: pass
            
    df_h = pd.concat(list_horse, ignore_index=True) if list_horse else None
    df_r = pd.concat(list_race, ignore_index=True) if list_race else None
    df_p = pd.concat(list_payback, ignore_index=True) if list_payback else None
    df_o = pd.concat(list_odds, ignore_index=True) if list_odds else None
    return df_h, df_r, df_p, df_o

# ==========================================
# ⚙️ 7. 作戦司令パネル（サイドバー）
# ==========================================
st.sidebar.markdown("### ⚙️ 作戦司令パネル")
mode = st.sidebar.radio(
    "🔥 モードを選択せよ！", 
    ["地方競馬（実戦・当日ZIP丸投げ）", "中央競馬（JRAコピペ）", "📊 過去データ一括検証・勝因分析"]
)
st.sidebar.markdown("---")
target_win_rate = st.sidebar.slider(
    "🚨 購入を発動する最低AI推奨度（％）", 
    min_value=55, max_value=95, value=74, step=1
)

# ==========================================
# 📊 8. メイン実行ルーチン（完全フラット構造）
# ==========================================
if mode in ["地方競馬（実戦・当日ZIP丸投げ）", "中央競馬（JRAコピペ）"]:
    st.write("⚙️ 一括丸投げ仕分け ＆ 全レースワイド3点 リアルタイムオッズ完全連動")
    
    col1, col2 = st.columns(2)
    with col1: bet_strategy = st.radio("戦略選択", ["ガミり防止・傾斜配分モード（推奨）", "1点一律ベタ買いモード"])
    with col2: total_budget_per_race = st.number_input("💵 1レース総予算（円）", min_value=300, value=1000, step=100)

    uploaded_files = st.file_uploader("📋 当日データをここにドロップ！", type=["csv", "zip"], accept_multiple_files=True)

    if uploaded_files:
        df_h, df_r, df_o = process_current_files(uploaded_files)
        if df_h is not None and df_r is not None:
            if df_o is not None and ("賭式" in df_o.columns):
                df_wo_sub = df_o[df_o["賭式"] == "単勝"]
                df_win_odds = df_wo_sub[["競馬場", "レース番号", "番号1", "オッズ"]].rename(columns={"番号1": "馬番", "オッズ": "リアルタイム単勝オッズ"})
                df_h = pd.merge(df_h, df_win_odds, on=["競馬場", "レース番号", "馬番"], how="left")
                
            df_h["AI勝率スコア"] = df_h.apply(calc_true_ai_score, axis=1)
            all_wide_matches = []
            
            for track in df_h["競馬場"].unique():
                df_track_only = df_h[df_h["競馬場"] == track]
                for r in sorted(df_track_only["レース番号"].dropna().unique()):
                    df_r_race = df_track_only[df_track_only["レース番号"] == int(float(r))]
                    if len(df_r_race) >= 3:
                        sorted_horses = df_r_race.sort_values(by="AI勝率スコア", ascending=False).reset_index(drop=True)
                        top3 = sorted_horses.head(3)
                        n1, n2, n3 = top3.loc[0, '馬番'], top3.loc[1, '馬番'], top3.loc[2, '馬番']
                        avg_score = int((top3.loc[0, "AI勝率スコア"] + top3.loc[1, "AI勝率スコア"] + top3.loc[2, "AI勝率スコア"]) / 3)
                        
                        random.seed(int(avg_score))
                        win_rate = max(55, min(97, int(avg_score * 0.78 + random.randint(-1, 2))))
                        
                        race_time_str = "時刻不明"
                        df_time_search = df_r[(df_r["競馬場"] == track) & (df_r["レース番号"] == int(float(r)))]
                        if not df_time_search.empty:
                            race_time_str = str(df_time_search.iloc[0]["発走時刻"]) if "発走時刻" in df_time_search.columns else str(df_time_search.iloc[0]["発走予定時刻"])

                        odds12 = get_wide_odds_float(df_o, track, r, n1, n2)
                        odds13 = get_wide_odds_float(df_o, track, r, n1, n3)
                        odds23 = get_wide_odds_float(df_o, track, r, n2, n3)
                        
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
                        
                        win_odds_val = top3.loc[0, 'リアルタイム単勝オッズ'] if 'リアルタイム単勝オッズ' in top3.columns else 0.0
                        win_odds_str = f" [{win_odds_val}倍]" if float(win_odds_val) > 0 else ""
                        
                        df_ana_candidates = df_r_race[df_r_race["リアルタイム単勝オッズ"] >= 10.0]
                        ana_horse_row = df_ana_candidates.sort_values(by="AI勝率スコア", ascending=False).iloc[0] if not df_ana_candidates.empty else (sorted_horses.loc[3] if len(sorted_horses) >= 4 else None)
                        
                        if ana_horse_row is not None:
                            a_num = int(float(ana_horse_row['馬番']))
                            a_name = ana_horse_row['馬名']
                            a_odds = ana_horse_row['リアルタイム単勝オッズ']
                            ana_signal = f"🔥 LOCKON!! 【 {a_num}番 】 ({a_name}) [{a_odds}倍]"
                        else:
                            ana_signal = "ーー（安全第一・見送り）"
                        
                        if win_rate >= target_win_rate:
                            h_num = int(float(n1))
                            h_name = top3.loc[0, '馬名']
                            
                            # 🚨 徹底追放：f文字列の中身を変数化して超安全に結合！
                            race_title = f"{track} {int(float(r))}R"
                            combos_str = f"{str12}\n{str13}\n{str23}"
                            honmei_str = f"{h_num}番 ({h_name}){win_odds_str}"
                            rate_str = f"{win_rate} ％"
                            
                            all_wide_matches.append({
                                "対象レース": race_title,
                                "発走時刻": race_time_str,
                                "ワイド 3点買い目（オッズ＆推奨購入額）": combos_str,
                                "大本命馬": honmei_str,
                                "AI推奨度": rate_str,
                                "🔥 大穴単勝 (100円)": ana_signal
                            })                    

            if all_wide_matches:
                st.table(pd.DataFrame(all_wide_matches)[["対象レース", "発走時刻", "ワイド 3点買い目（オッズ＆推奨購入額）", "大本命馬", "AI推奨度", "🔥 大穴単勝 (100円)"]])
                line_msg = "🏇【AI・クラウド要塞報告】🏇\n"
                for match in all_wide_matches:
                    r_race = match["対象レース"]
                    r_time = match["発走時刻"]
                    r_combos = match["ワイド 3点買い目（オッズ＆推奨購入額）"]
                    r_honmei = match["大本命馬"]
                    r_ana = match["🔥 大穴単勝 (100円)"]
                    r_rate = match["AI推奨度"]
                    
                    line_msg += f"\n■ {r_race} (🕒発走: {r_time}) \n"
                    line_msg += f"👉AI推奨度: {r_rate}\n{r_combos}\n"
                    line_msg += f"★大本命: {r_honmei}\n🔥大穴単勝: {r_ana}\n----------------------------------\n"
                if df_o is not None: send_horse_line(line_msg)

elif mode == "📊 過去データ一括検証・勝因分析":
    st.markdown("### 🏯 過去ビッグデータ一括格納・自動検証エンジン")
    archive_files = st.file_uploader("📋 過去のZIP/CSVアーカイブを一括ドロップ", type=["zip", "csv"], accept_multiple_files=True)
    
    if archive_files:
        with st.spinner("⏳ 膨大なデータを自動結合中..."):
            df_m_horse, df_m_race, df_m_payback, df_m_odds = process_archive_files(archive_files)

        if df_m_horse is not None and df_m_payback is not None and df_m_odds is not None:
            st.success(f"🟢 統合成功！馬データ {len(df_m_horse)}行 / オッズデータ {len(df_m_odds)}行")
            
            if st.button("⚔️ 過去データ検証作戦（バックテスト）を開始せよ！"):
                backtest_results = []
                df_wo_sub = df_m_odds[df_m_odds["賭式"] == "単勝"]
                df_win_odds = df_wo_sub[["競馬場", "競走年月日", "レース番号", "番号1", "オッズ"]].rename(columns={"番号1": "馬番", "オッズ": "リアルタイム単勝オッズ"})
                df_m_horse = pd.merge(df_m_horse, df_win_odds, on=["競馬場", "競走年月日", "レース番号", "馬番"], how="left")
                df_m_horse["AI勝率スコア"] = df_m_horse.apply(calc_true_ai_score, axis=1)
                
                for (track, date, r), df_r_race in df_m_horse.groupby(["競馬場", "競走年月日", "レース番号"]):
                    if len(df_r_race) >= 3:
                        sorted_horses = df_r_race.sort_values(by="AI勝率スコア", ascending=False).reset_index(drop=True)
                        top3 = sorted_horses.head(3)
                        n1, n2, n3 = top3.loc[0, '馬番'], top3.loc[1, '馬番'], top3.loc[2, '馬番']
                        avg_score = int((top3.loc[0, "AI勝率スコア"] + top3.loc[1, "AI勝率スコア"] + top3.loc[2, "AI勝率スコア"]) / 3)
                        
                        random.seed(int(avg_score))
                        win_rate = max(55, min(97, int(avg_score * 0.78 + random.randint(-1, 2))))
                        
                        if win_rate >= target_win_rate:
                            odds12 = get_wide_odds_float(df_m_odds, track, r, n1, n2, date=date)
                            odds13 = get_wide_odds_float(df_m_odds, track, r, n1, n3, date=date)
                            odds23 = get_wide_odds_float(df_m_odds, track, r, n2, n3, date=date)
                            
                            total_budget = 1000
                            amt12, amt13, amt23 = 100, 100, 100
                            if odds12 > 0 and odds13 > 0 and odds23 > 0:
                                try:
                                    sum_inv = (1.0 / odds12) + (1.0 / odds13) + (1.0 / odds23)
                                    amt12 = max(100, int(round((total_budget / odds12) / sum_inv / 100) * 100))
                                    amt13 = max(100, int(round((total_budget / odds13) / sum_inv / 100) * 100))
                                    amt23 = max(100, int(round((total_budget / odds23) / sum_inv / 100) * 100))
                                except: pass
                            
                            actual_bet = amt12 + amt13 + amt23
                            df_pb = df_m_payback[(df_m_payback["競馬場"] == track) & (df_m_payback["競走年月日"] == date) & (df_m_payback["レース番号"] == int(float(r)))]
                            payback_total, hit_count = 0, 0
                            
                            if not df_pb.empty:
                                row_pb = df_pb.iloc[0]
                                pair12 = {min(int(n1), int(n2)), max(int(n1), int(n2))}
                                pair13 = {min(int(n1), int(n3)), max(int(n1), int(n3))}
                                pair23 = {min(int(n2), int(n3)), max(int(n2), int(n3))}
                                
                                for idx in [1, 2, 3]:
                                    w_b1 = row_pb.get(f"ワイド組番{idx}馬番1")
                                    w_b2 = row_pb.get(f"ワイド組番{idx}馬番2")
                                    w_amt = row_pb.get(f"ワイド払戻金{idx}（円）")
                                    if pd.notna(w_b1) and pd.notna(w_b2):
                                        pb_pair = {min(int(w_b1), int(w_b2)), max(int(w_b1), int(w_b2))}
                                        if pb_pair == pair12: payback_total += (amt12 / 100) * w_amt; hit_count += 1
                                        if pb_pair == pair13: payback_total += (amt13 / 100) * w_amt; hit_count += 1
                                        if pb_pair == pair23: payback_total += (amt23 / 100) * w_amt; hit_count += 1
                            
                            backtest_results.append({"投資": actual_bet, "払戻": payback_total, "収支": payback_total - actual_bet, "的中数": hit_count})
                
                if backtest_results:
                    df_res = pd.DataFrame(backtest_results)
                    total_races = len(df_res)
                    total_invest = df_res["投資"].sum()
                    total_payback = df_res["払戻"].sum()
                    total_profit = df_res["収支"].sum()
                    rec_rate = (total_payback / total_invest) * 100 if total_invest > 0 else 0
                    
                    # 🚨 徹底追放：複雑な集計処理を完全にf文字列の外側に隔離！
                    df_hit_any = df_res[df_res["的中数"] > 0]
                    df_hit_triple = df_res[df_res["的中数"] == 3]
                    any_hit_rate = (len(df_hit_any) / total_races) * 100
                    triple_hit_rate = (len(df_hit_triple) / total_races) * 100
                    
                    st.markdown("### 🏆 検証作戦結果レポート")
                    st.markdown('<div class="gold-box">', unsafe_allow_html=True)
                    st.write(f"📊 **総厳選出撃レース数:** {total_races} レース")
                    st.write(f"💵 **総投資額:** {int(total_invest):,} 円")
                    st.write(f"💰 **総払戻金:** {int(total_payback):,} 円")
                    
                    if total_profit >= 0:
                        st.write(f"📈 **トータル純利益:** +{int(total_profit):,} 円")
                    else:
                        st.write(f"📈 **トータル純損失:** {int(total_profit):,} 円")
                        
                    st.write(f"📈 **トータル回収率:** {rec_rate:.2f} %")
                    st.write(f"🎯 **1点でも的中した勝率:** {any_hit_rate:.1f} %")
                    st.write(f"🔥 **3点すべて総取り確率:** {triple_hit_rate:.1f} %")
                    st.markdown('</div>', unsafe_allow_html=True)
