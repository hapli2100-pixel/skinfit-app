# streamlit_app_merged.py  ← 전체 교체

import streamlit as st
import pandas as pd
import altair as alt
import math, re

st.set_page_config(layout="wide")

# ===== Global Style =====
st.markdown("""
<style>
/* Hide default actions & anchor icons */
button[title="View fullscreen"], button[aria-label="View fullscreen"]{display:none!important;}
.vega-embed .vega-actions, .vega-actions, .vega-embed details{display:none!important;}
a[aria-label="anchor"], a.anchor, .stAnchor{display:none!important;}
h1 a, h2 a, h3 a, h4 a, h1 svg, h2 svg, h3 svg, h4 svg{display:none!important;}

/* Headings spacing */
h1, h2 { margin-top: 8px !important; margin-bottom: 10px !important; }
h3, h4 { margin-top: 6px !important; margin-bottom: 6px !important; }
.stMarkdown p { line-height: 1.55; }

/* Helper text (A 섹션) */
.purpose-helper{ font-size:1.20rem; font-weight:700; color:#374151; margin: 0 0 2px; }

/* Radios — 옵션 글자 더 크게 + 간격 넓게 (A, C 공통) */
[data-testid="stRadio"] div[role="radiogroup"]{ margin-top: 0 !important; }
[data-testid="stRadio"] div[role="radiogroup"] > label{
  font-size: 1.22rem;
  margin-right: 28px;
  margin-bottom: 14px;
}

/* ★ MultiSelect 라벨(피부 타입/피부 고민/자극도) — 글자 더 크게 */
div[data-testid="stMultiSelect"] > label{
  font-size: 1.38rem !important;
  font-weight: 700 !important;
  color:#1f2937 !important;
  margin-bottom: 6px !important;
}

/* ★ Expander(키워드 카테고리) 헤더 글자 크게 */
[data-testid="stExpander"] summary{
  font-size: 1.26rem !important;
  font-weight: 700 !important;
  color:#111827 !important;
}
[data-testid="stExpander"] summary p{ display:inline; } /* Streamlit이 summary 안에 p를 넣는 경우 대비 */

/* Field label (예산/브랜드 등) */
.field-label { font-size: 1.14rem; font-weight: 700; line-height: 1.25; margin: 2px 0 6px; }
.field-label .tip { display:inline-block; margin-left:6px; cursor:help; color:#6b7280; font-weight:600; }

/* Keyword chips (제품 이미지 아래) */
.tagline { margin-top: 6px; font-size: 0.92rem; color: #374151; }
.tagline .tag{
  display:inline-block; padding:2px 8px; border-radius:999px;
  border:1px solid #e5e7eb; margin:0 6px 6px 0; background:#f9fafb; color:#374151;
}

/* Product cards */
div.stContainer{
  border: 1px solid #e5e7eb !important;
  border-radius: 14px !important;
  background: #ffffff !important;
  padding: 12px 16px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.product-card{ position:relative; transition: box-shadow .2s ease, transform .2s ease; }
.product-card:hover{ box-shadow: 0 8px 22px rgba(0,0,0,.08); transform: translateY(-2px); }

/* Select corners */
[data-baseweb="select"] > div { border-radius: 10px; }

/* Spacing utilities */
.gap-xs{height:6px;} .gap-sm{height:12px;} .gap-md{height:18px;}
.gap-lg{height:28px;} .gap-xl{height:40px;} .gap-xxl{height:56px;}
</style>
""", unsafe_allow_html=True)

alt.renderers.set_embed_options(actions=False)

def gap(size="md"):
    st.markdown(f"<div class='gap-{size}'></div>", unsafe_allow_html=True)

# ===== 1) 데이터 로드 =====
PROD_FEAT_CSV  = "oliveyoung_lotion_data_with_features.csv"
REVIEWS_CSV    = "reviews_with_absa_results.csv"
TOP5_KW_CSV    = "keywords_top5.csv"

products_feat  = pd.read_csv(PROD_FEAT_CSV,  encoding="cp949")
reviews_df     = pd.read_csv(REVIEWS_CSV,    encoding="utf-8-sig")
keywords_long  = pd.read_csv(TOP5_KW_CSV,    encoding="utf-8-sig")

products_feat.columns = products_feat.columns.str.replace("\ufeff", "").str.strip()
reviews_df.columns = reviews_df.columns.str.replace("\ufeff", "").str.strip()
keywords_long.columns = keywords_long.columns.str.replace("\ufeff", "").str.strip()


# 정리
for df, col in [(products_feat,"product_id"), (reviews_df,"review_product_id"), (keywords_long,"review_product_id")]:
    if col in df.columns: df[col] = df[col].astype(str)
if "review_product_id" not in products_feat.columns:
    products_feat = products_feat.rename(columns={"product_id":"review_product_id"})
if "sale_price" in products_feat.columns:
    products_feat["sale_price"] = pd.to_numeric(products_feat["sale_price"], errors="coerce").fillna(0).astype(int)
products_feat = products_feat.sort_values("review_product_id").drop_duplicates("review_product_id", keep="first")

# Top5 키워드(세로형 → 리스트)
def build_top5_from_longform(df: pd.DataFrame) -> pd.DataFrame:
    need = {"review_product_id","keyword"}
    if not need.issubset(df.columns): return pd.DataFrame({"review_product_id": [], "top5_keywords": []})
    if "frequency" in df.columns:
        df = df.sort_values(["review_product_id","frequency"], ascending=[True, False])
    else:
        df = df.sort_values(["review_product_id"])
    top5 = (
        df.groupby("review_product_id")["keyword"]
          .apply(lambda s: [str(x).strip() for x in list(s.head(5)) if str(x).strip()])
          .reset_index(name="top5_keywords")
    )
    top5["top5_keywords"] = top5["top5_keywords"].apply(lambda L: L[:5] if isinstance(L, list) else [])
    return top5
top5_kw_df = build_top5_from_longform(keywords_long)

# 병합
prod_base = products_feat.merge(top5_kw_df, on="review_product_id", how="left")
prod_base["top5_keywords"] = prod_base["top5_keywords"].apply(lambda x: x if isinstance(x, list) else [])

# ===== 2) 만족도 점수 =====
MAX_REVIEWS_PER_PRODUCT = 1000
def calculate_wilson_score(positive_reviews, total_reviews, z=1.96):
    if total_reviews == 0: return 0.0
    p = positive_reviews / total_reviews
    num = p + (z*z)/(2*total_reviews) - z * ((p*(1-p) + (z*z)/(4*total_reviews))/total_reviews) ** 0.5
    den = 1 + (z*z)/total_reviews
    return num/den

def calculate_scores(df: pd.DataFrame, max_per_product: int = MAX_REVIEWS_PER_PRODUCT) -> pd.DataFrame:
    if df.empty or "review_product_id" not in df.columns:
        return pd.DataFrame(columns=["review_product_id","wilson_score","used_reviews"])

    capped = (
        df.groupby("review_product_id", group_keys=False)
          .head(max_per_product)
          .reset_index(drop=True)
    )

    total = capped.groupby("review_product_id").size().reset_index(name="used_reviews")

    if "sentiment_label" in capped.columns:
        pos = (
            capped[capped["sentiment_label"] == "긍정"]
            .groupby("review_product_id")
            .size()
            .reset_index(name="positive_reviews")
        )
    else:
        pos = total[["review_product_id"]].copy()
        pos["positive_reviews"] = 0

    m = pd.merge(total, pos, on="review_product_id", how="left").fillna({"positive_reviews": 0})
    m["wilson_score"] = m.apply(
        lambda r: calculate_wilson_score(r["positive_reviews"], r["used_reviews"]),
        axis=1
    )

    return m[["review_product_id", "wilson_score", "used_reviews"]]

overall_scores = calculate_scores(reviews_df).rename(
    columns={
        "wilson_score": "overall_wilson_score",
        "used_reviews": "overall_used_reviews"
    }
)

# ===== 3) Altair helpers =====
def render_vega(chart: alt.Chart):
    spec = chart.to_dict(); spec["usermeta"] = {"embedOptions":{"actions":False}}
    st.vega_lite_chart(spec, use_container_width=True)

def score_bar(score: float, show_value_label: bool=True):
    df = pd.DataFrame({"score":[float(score)], "c":[""]})
    base = alt.Chart(df).encode(y=alt.Y("c:N", axis=None))
    bar  = base.mark_bar(size=10).encode(
        x=alt.X("score:Q", axis=None, scale=alt.Scale(domain=[0,1])),
        tooltip=alt.Tooltip("score:Q", format=".2%"))
    if show_value_label:
        bar = bar + base.mark_text(align="left", baseline="middle", dx=5).encode(
            x="score:Q", text=alt.Text("score:Q", format=".0%"))
    render_vega(bar.configure_view(strokeWidth=0))

# ===== 4) 페이징 =====
PER_PAGE = 24
def page_slice(total: int, key_prefix: str):
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page_key = f"{key_prefix}_page"
    page = min(max(1, st.session_state.get(page_key, 1)), total_pages)
    start, end = (page-1)*PER_PAGE, (page-1)*PER_PAGE+PER_PAGE
    return page, total_pages, start, end

def pagination_controls(total: int, key_prefix: str, page: int, total_pages: int):
    BLOCK=10; block_idx=(page-1)//BLOCK; start_p=block_idx*BLOCK+1; end_p=min(start_p+BLOCK-1, total_pages)
    left, mid, right = st.columns([1,6,1])
    with left:
        if st.button("◀ 이전", key=f"{key_prefix}_prev", disabled=(start_p<=1)):
            st.session_state[f"{key_prefix}_page"]=max(start_p-BLOCK,1); st.rerun()
    with mid:
        st.markdown(f"<div style='text-align:center; font-weight:600; margin-bottom:6px;'>페이지 {page} / {total_pages}</div>", unsafe_allow_html=True)
        cols = st.columns(end_p-start_p+1)
        for i, col in enumerate(cols, start=start_p):
            with col:
                if st.button(str(i), key=f"{key_prefix}_p{i}", disabled=(i==page), use_container_width=True):
                    st.session_state[f"{key_prefix}_page"]=i; st.rerun()
    with right:
        if st.button("다음 ▶", key=f"{key_prefix}_next", disabled=(end_p>=total_pages)):
            st.session_state[f"{key_prefix}_page"]=min(start_p+BLOCK, total_pages); st.rerun()

# ===== 5) 카드 렌더러 =====
def _render_hashtags(tags):
    if not isinstance(tags, (list, tuple)) or not tags: return
    chips = " ".join([f"<span class='tag'>#{str(t).strip()}</span>" for t in tags if str(t).strip()])
    st.markdown(f"<div class='tagline'>{chips}</div>", unsafe_allow_html=True)

def render_cards(df: pd.DataFrame, show_filtered: bool=False):
    if df.empty:
        st.info("표시할 제품이 없습니다."); return
    for i in range(0, len(df), 2):
        c1, c2 = st.columns(2)
        rows = [df.iloc[i]]
        if i+1 < len(df): rows.append(df.iloc[i+1])
        for col, row in zip((c1, c2), rows):
            with col:
                with st.container(border=True):
                    st.markdown("<div class='product-card'>", unsafe_allow_html=True)
                    img_col, info_col = st.columns([1,1])
                    with img_col:
                        img = row.get("image_url")
                        if isinstance(img, str) and img:
                            st.image(img, use_container_width=True)
                        _render_hashtags(row.get("top5_keywords", []))
                    with info_col:
                        brand = row.get("brand_name"); name=row.get("product_name"); link=row.get("URL"); price=row.get("sale_price")
                        if pd.notna(brand): st.markdown(f"**{brand}**")
                        if pd.notna(name):  st.markdown(f"{name}")
                        if pd.notna(price):
                            try: st.markdown(f"{int(price)}원")
                            except Exception: st.markdown(f"{price}원")
                        if isinstance(link, str) and link:
                            st.markdown(f"[올리브영에서 보기]({link})")
                        if show_filtered and pd.notna(row.get("filtered_wilson_score")):
                            st.markdown(f"**나와 같은 피부 고민을 가진 사람들이 {row['filtered_wilson_score']:.0%} 만족했어요**", unsafe_allow_html=True)
                            score_bar(row['filtered_wilson_score'], show_value_label=True)
                        if pd.notna(row.get("overall_wilson_score")):
                            st.markdown(f"**구매자들의 {row['overall_wilson_score']:.0%}가 만족했어요**")
                            score_bar(row["overall_wilson_score"], show_value_label=True)
                    st.markdown("</div>", unsafe_allow_html=True)

# ===== 6) 라벨 정규화 =====
def normalize_skin_type(s: str):
    s = str(s)
    if re.search(r"건성|dry", s, re.I): return "건성"
    if re.search(r"지성|oily", s, re.I): return "지성"
    if re.search(r"복합|comb", s, re.I): return "복합성"
    return None
def normalize_skin_trouble(s: str):
    s = str(s)
    if re.search(r"보습|수분|hydr", s, re.I): return "보습"
    if re.search(r"진정|calm", s, re.I): return "진정"
    if re.search(r"주름|미백|탄력|anti|whiten", s, re.I): return "주름/미백"
    return None
def normalize_skin_sensitivity(s: str):
    s = str(s)
    if re.search(r"(무자극|저자극|순|자극\\s*없|mild|gentle)", s, re.I): return "자극 없이 순함"
    if re.search(r"(보통|무난|괜찮|normal)", s, re.I): return "보통"
    if re.search(r"(자극(?!\\s*없)|따가|화끈|irrit|트러블)", s, re.I): return "자극 있음"
    return None

# ===== 7) UI =====
st.write("당신의 피부에 맞는 화장품, 찾아드립니다")
st.title("고객 맞춤형 화장품 추천")

# --- A
st.subheader("A. 이용 목적")  # ← '(필수)' 제거
st.markdown("<div class='purpose-helper'>서비스 이용 목적을 선택하세요.</div>", unsafe_allow_html=True)
purpose = st.radio(
    "",  # 라벨은 위 helper로 대체
    ["둘러보기 (추천 받아보기)", "피부 고민 해결 (보습/진정/주름·미백)", "상세 조건 추가하기 (예산/브랜드)"],
    index=0, horizontal=True, label_visibility="collapsed",
)

gap("xxl")  # A ↔ B

# A: 둘러보기
if purpose.startswith("둘러보기"):
    out = pd.merge(prod_base, overall_scores, on="review_product_id", how="inner")
    out = out.sort_values("overall_wilson_score", ascending=False).drop_duplicates("review_product_id").head(20)
    st.subheader("안전/무난 제품 TOP20")
    st.write(f"총 {len(out)}개의 제품을 보여줍니다.")
    gap("sm")
    render_cards(out, show_filtered=False)

# --- B/C 조건
else:
    ALL_TYPES    = ["건성","지성","복합성"]
    ALL_TROUBLES = ["보습","진정","주름/미백"]
    ALL_SENS     = ["자극 있음","보통","자극 없이 순함"]

    def is_all_selected(sel, all_opts):
        return (not sel) or (set(sel) >= set(all_opts))

    st.subheader("B. 피부 고민 정보 (복수 선택 가능)")
    # st.caption("기본적으로 선택지 전체가 포함되어 추천됩니다.")  # ← 문구 삭제
    gap("xs")

    c1,c2,c3 = st.columns(3)
    with c1:
        sel_skin_type_ui = st.multiselect("피부 타입", ALL_TYPES, placeholder="피부 타입 선택")
    with c2:
        sel_skin_trouble_ui = st.multiselect("피부 고민", ALL_TROUBLES, placeholder="피부 고민 선택")
    with c3:
        sel_skin_sensitivity_ui = st.multiselect("자극도", ALL_SENS, placeholder="자극 정도 선택")

    made_selection = bool(sel_skin_type_ui or sel_skin_trouble_ui or sel_skin_sensitivity_ui)
    sel_skin_type        = ALL_TYPES    if is_all_selected(sel_skin_type_ui, ALL_TYPES) else sel_skin_type_ui
    sel_skin_trouble     = ALL_TROUBLES if is_all_selected(sel_skin_trouble_ui, ALL_TROUBLES) else sel_skin_trouble_ui
    sel_skin_sensitivity = ALL_SENS     if is_all_selected(sel_skin_sensitivity_ui, ALL_SENS) else sel_skin_sensitivity_ui

    gap("xxl")  # B ↔ C

    if purpose.startswith("상세 조건"):
        st.subheader("C. 예산/브랜드 고려하기")
        c4,c5 = st.columns(2)
        with c4:
            st.markdown("<div class='field-label'>예산<span class='tip' title='선택한 예산 범위 안에서, 고객 만족도가 높은 순으로 추천됩니다.'>ⓘ</span></div>", unsafe_allow_html=True)
            budget_options = ["적용 안 함","2만 원 이내","3만 원 이내","4만 원 이내","5만 원 이내","8만 원 이내","8만 원 +"]
            budget_choice = st.radio("", options=budget_options, index=0, horizontal=True, key="budget_radio", label_visibility="collapsed")
        with c5:
            st.markdown("<div class='field-label'>원하는 브랜드 선택하기</div>", unsafe_allow_html=True)
            brand_options = sorted(list(prod_base.get("brand_name", pd.Series()).dropna().unique()))
            brands = st.multiselect("", brand_options)
    else:
        budget_choice, brands = None, []

    # 리뷰 필터 & 점수
    f = reviews_df.copy()
    if "skin_type" in f.columns and not is_all_selected(sel_skin_type_ui, ALL_TYPES):
        pattern = "|".join(re.escape(x) for x in sel_skin_type)
        f = f[f["skin_type"].astype(str).str.contains(pattern, case=False, na=False)]
    if "skin_trouble" in f.columns and not is_all_selected(sel_skin_trouble_ui, ALL_TROUBLES):
        pattern = "|".join(re.escape(x) for x in sel_skin_trouble)
        f = f[f["skin_trouble"].astype(str).str.contains(pattern, case=False, na=False)]
    if "skin_sensitivity" in f.columns and not is_all_selected(sel_skin_sensitivity_ui, ALL_SENS):
        reg_map = {
            "자극 있음": r"(자극(?!\s*없)|따가움|따갑|화끈|트러블|불편|자극적)",
            "보통": r"(보통|무난|그럭저럭|적당|평범|괜찮)",
            "자극 없이 순함": r"(무자극|저자극|순함|부드러움|자극\s*없|편안|순한)",
        }
        patterns = [re.escape(x) for x in sel_skin_sensitivity] + [reg_map[k] for k in sel_skin_sensitivity if k in reg_map]
        vals = f["skin_sensitivity"].astype(str)
        f = f[vals.str.contains("|".join(patterns), case=False, na=False, regex=True)]

    user_scores = calculate_scores(f).rename(columns={"wilson_score":"user_wilson_score","used_reviews":"user_used_reviews"})

    # 주요 속성 계산
    tmp = pd.DataFrame({"review_product_id": reviews_df["review_product_id"]})
    tmp["n_skin_type"]        = reviews_df.get("skin_type", pd.Series(dtype=str)).map(normalize_skin_type)
    tmp["n_skin_trouble"]     = reviews_df.get("skin_trouble", pd.Series(dtype=str)).map(normalize_skin_trouble)
    tmp["n_skin_sensitivity"] = reviews_df.get("skin_sensitivity", pd.Series(dtype=str)).map(normalize_skin_sensitivity)
    maj = tmp.groupby("review_product_id").agg(
        major_skin_type=("n_skin_type", lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else None),
        major_skin_trouble=("n_skin_trouble", lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else None),
        major_skin_sensitivity=("n_skin_sensitivity", lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else None),
    ).reset_index()

    prod = prod_base.merge(maj, on="review_product_id", how="left")
    out  = user_scores.merge(prod, on="review_product_id", how="inner").merge(overall_scores, on="review_product_id", how="left")
    def match_weight(row, sel_types, sel_troubles, sel_sens):
        cnt = 0
        if sel_types and row.get("major_skin_type") in sel_types: cnt += 1
        if sel_troubles and row.get("major_skin_trouble") in sel_troubles: cnt += 1
        if sel_sens and row.get("major_skin_sensitivity") in sel_sens: cnt += 1
        return 1.0 if cnt>=3 else (0.8 if cnt==2 else (0.5 if cnt==1 else 0.2))
    out["Wmatch"] = out.apply(lambda r: match_weight(r, sel_skin_type, sel_skin_trouble, sel_skin_sensitivity), axis=1)
    out["filtered_wilson_score"] = out["user_wilson_score"] * out["Wmatch"]

    if 'brand_name' in out.columns and brands:
        out = out[out["brand_name"].isin(brands)]
    def _apply_budget_radio(df: pd.DataFrame, choice: str) -> pd.DataFrame:
        if (choice is None) or (choice=="적용 안 함") or ("sale_price" not in df.columns): return df
        if choice=="8만 원 +": return df[df["sale_price"]>80_000]
        m = re.search(r"(\d+)\s*만", choice)
        if m: return df[df["sale_price"] <= int(m.group(1))*10_000]
        return df
    out = _apply_budget_radio(out, budget_choice)

    gap("xxl")  # B/C ↔ 키워드

    # === 리뷰 키워드: 제목+툴팁, 카테고리별 expander ===
    st.markdown(
        "<h3>리뷰 키워드로 더 자세히 찾아보기"
        "<span class='tip' title='구매자들이 리뷰에서 가장 많이 언급한 키워드를 바탕으로 제품이 추천됩니다.'> ⓘ</span>"
        "</h3>",
        unsafe_allow_html=True
    )

    KW_GROUPS = {
        "피부 타입": ["건성", "지성", "복합성", "트러블성", "남성 피부"],
        "사용감": ["에멀전 제형","크림 제형","젤 제형","발림성","부드러워짐","매끈해짐","스틱밤 제형",
                 "빠른 흡수","산뜻","가벼움","촉촉","번들거림 없음","끈적임 없음","순함","트러블 발생","끈끈함","안정성","무향","향","깔끔함"],
        "기능": ["화이트닝","화잘먹","지속력","당기지 않음","올인원","여드름","보습","수분","탄력","주름","미백","진정","모공","오일컨트롤","휴대성"],
        "기타": ["양 조절 용이","레이어링 우수","여름","겨울","건조한 환경","운동 후","재구매","정착템","추천템","선물","여행용"],
    }
    selected_keywords = []
    for g_idx, (gname, items) in enumerate(KW_GROUPS.items()):
        with st.expander(gname, expanded=False):
            cols = st.columns(4)
            for idx, kw in enumerate(items):
                with cols[idx % 4]:
                    if st.checkbox(kw, key=f"kw_{g_idx}_{idx}"):
                        selected_keywords.append(kw)

    if selected_keywords:
        def _has_any_kw(L):
            S = set(str(x).strip() for x in (L or []))
            return any(k in S for k in selected_keywords)
        out = out[out["top5_keywords"].apply(_has_any_kw)]

    gap("xxl")  # 키워드 ↔ 결과

    # 결과
    st.subheader("결과")
    if out.empty:
        st.info("선택하신 조건에 맞는 제품이 없습니다.")
    else:
        if 'budget_choice' in locals() and budget_choice: st.caption(f"예산 선택: {budget_choice}")
        st.write(f"총 {len(out)}개의 제품이 있습니다.")
        gap("sm")
        page, total_pages, start, end = page_slice(len(out), "filtered")
        render_cards(out.iloc[start:end], show_filtered=made_selection)
        pagination_controls(len(out), "filtered", page, total_pages)