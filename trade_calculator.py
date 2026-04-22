import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(page_title="무역 수익 계산기", layout="wide")

PRICES_FILE = Path("D:/Calc/prices.json")
XLSX_FILE = "D:/Calc/메모장.xlsx"

PORT_ORDER = [
    "평경", "개경", "명주", "천주", "광주", "담수", "안남", "브루나이",
    "섬라국", "크메르", "술루", "스리비자야", "말레이", "버마",
    "천축", "실론", "페르시아", "대식국", "미스르", "바스라"
]
SPECIALS = {
    "평경": "목재", "개경": "녹용", "명주": "도자기", "천주": "녹차",
    "광주": "비단", "담수": "진주", "안남": "벼", "브루나이": "제비집",
    "섬라국": "상아", "크메르": "파인애플", "술루": "꽃게", "스리비자야": "술",
    "말레이": "어육", "버마": "철광석", "천축": "향료", "실론": "야자",
    "페르시아": "수정", "대식국": "옥 제품", "미스르": "피혁", "바스라": "백은"
}
ITEMS = [
    "목재", "녹용", "도자기", "녹차", "비단", "진주", "벼", "제비집",
    "상아", "파인애플", "꽃게", "술", "어육", "철광석", "향료", "야자",
    "수정", "옥 제품", "피혁", "백은"
]


def init_prices_from_xlsx():
    df = pd.read_excel(XLSX_FILE, sheet_name="데이터", usecols=["항구", "화물", "가격"])
    prices = {port: {item: 0 for item in ITEMS} for port in PORT_ORDER}
    for _, row in df.iterrows():
        port, item = row["항구"], row["화물"]
        if port in prices and item in prices[port]:
            prices[port][item] = int(row["가격"])
    return prices


def load_prices():
    if PRICES_FILE.exists():
        data = json.loads(PRICES_FILE.read_text(encoding="utf-8"))
        # 이전 버전(dict) 호환: {"buy":..,"sell":..} → 단일 숫자
        for port in PORT_ORDER:
            data.setdefault(port, {})
            for item in ITEMS:
                v = data[port].get(item, 0)
                if isinstance(v, dict):
                    v = v.get("buy", 0) or v.get("sell", 0) or 0
                data[port][item] = int(v)
        return data
    prices = init_prices_from_xlsx()
    save_prices(prices)
    return prices


def save_prices(prices):
    PRICES_FILE.write_text(json.dumps(prices, ensure_ascii=False, indent=2), encoding="utf-8")


prices = load_prices()

st.title("⚓ 항구 무역 수익 계산기")

# =========================
# 1) 출발 항구 선택
# =========================
departure = st.selectbox(
    "🛒 출발 항구",
    PORT_ORDER,
    format_func=lambda p: f"{p}  [특산품: {SPECIALS[p]}]"
)

st.divider()

# =========================
# 2) 항구별 화물 가격 입력
# =========================
st.subheader("📝 항구별 화물 가격 입력")

edit_port = st.selectbox(
    "가격을 입력할 항구 선택",
    PORT_ORDER,
    format_func=lambda p: f"{p}  [특산품: {SPECIALS[p]}]",
    key="edit_port_select",
)

rows = []
for item in ITEMS:
    rows.append({
        "화물": item,
        "가격": prices[edit_port][item],
        "특산품": "⭐" if item == SPECIALS[edit_port] else "",
    })
df_edit = pd.DataFrame(rows)

edited = st.data_editor(
    df_edit,
    hide_index=True,
    use_container_width=True,
    column_config={
        "화물": st.column_config.TextColumn("화물", disabled=True),
        "특산품": st.column_config.TextColumn("특산품", disabled=True, width="small"),
        "가격": st.column_config.NumberColumn("가격", min_value=0, step=1),
    },
    key=f"editor_{edit_port}",
)

# 변경사항 자동 저장
changed = False
for _, row in edited.iterrows():
    item = row["화물"]
    new_price = int(row["가격"])
    if prices[edit_port][item] != new_price:
        prices[edit_port][item] = new_price
        changed = True
if changed:
    save_prices(prices)

st.divider()

# =========================
# 3) 결과 - Top 10
# =========================
st.subheader(f"📊 {departure} 출발 — 화물별 최고 수익 Top 15")

dep_prices = prices[departure]
# 화물별로 최고 수익 도착지 하나씩만 집계
best_per_item = {}
for item in ITEMS:
    buy = dep_prices[item]
    if buy <= 0:
        continue
    best = None
    for dest in PORT_ORDER:
        if dest == departure:
            continue
        sell = prices[dest][item]
        if sell <= 0 or sell <= buy:
            continue
        profit = sell - buy
        rate = profit / buy
        if best is None or rate > best["수익률"]:
            best = {
                "도착지": dest,
                "화물": item,
                "구매가격": buy,
                "판매가격": sell,
                "차익": profit,
                "수익률": rate,
            }
    if best is not None:
        best_per_item[item] = best

if not best_per_item:
    st.warning(f"{departure}보다 비싸게 팔 수 있는 화물이 없습니다. 가격을 먼저 입력하세요.")
else:
    top_n = sorted(best_per_item.values(), key=lambda x: -x["수익률"])[:15]
    df_top = pd.DataFrame(top_n)
    df_top.index = range(1, len(df_top) + 1)

    medals = ["🥇", "🥈", "🥉"]
    cols = st.columns(3)
    for i in range(min(3, len(top_n))):
        r = top_n[i]
        with cols[i]:
            st.metric(
                label=f"{medals[i]} {r['도착지']} · {r['화물']}",
                value=f"{r['수익률']*100:+.1f}%",
                delta=f"차익 {r['차익']:+,}"
            )

    display = df_top.copy()
    display["수익률"] = display["수익률"].apply(lambda x: f"{x*100:+.1f}%")
    sel = st.dataframe(
        display,
        use_container_width=True,
        column_config={
            "구매가격": st.column_config.NumberColumn("구매가격", format="%d"),
            "판매가격": st.column_config.NumberColumn("판매가격", format="%d"),
            "차익": st.column_config.NumberColumn("차익", format="%+d"),
        },
        on_select="rerun",
        selection_mode="single-row",
        key="top_select",
    )

    selected_rows = sel.selection.rows if sel and sel.selection else []
    if selected_rows:
        sel_idx = selected_rows[0]
        selected_dest = top_n[sel_idx]["도착지"]

        st.divider()
        st.subheader(f"📦 {departure} → {selected_dest}  화물 수익률 Top 15")

        dest_candidates = []
        for item in ITEMS:
            buy = dep_prices[item]
            sell = prices[selected_dest][item]
            if buy > 0 and sell > 0 and sell > buy:
                profit = sell - buy
                dest_candidates.append({
                    "화물": item,
                    "구매가격": buy,
                    "판매가격": sell,
                    "차익": profit,
                    "수익률": profit / buy,
                })

        if not dest_candidates:
            st.info(f"{selected_dest}에서 이익이 나는 화물이 없습니다.")
        else:
            dest_top = sorted(dest_candidates, key=lambda x: -x["수익률"])[:15]
            df_dest = pd.DataFrame(dest_top)
            df_dest.index = range(1, len(df_dest) + 1)
            df_dest["수익률"] = df_dest["수익률"].apply(lambda x: f"{x*100:+.1f}%")
            st.dataframe(
                df_dest,
                use_container_width=True,
                column_config={
                    "구매가격": st.column_config.NumberColumn("구매가격", format="%d"),
                    "판매가격": st.column_config.NumberColumn("판매가격", format="%d"),
                    "차익": st.column_config.NumberColumn("차익", format="%+d"),
                }
            )
    else:
        st.caption("💡 위 표에서 행을 클릭하면 해당 도착지의 화물별 수익률 Top 15가 아래에 표시됩니다.")
