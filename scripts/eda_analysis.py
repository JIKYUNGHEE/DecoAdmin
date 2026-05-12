import argparse
import json
import os
import urllib.error
import urllib.request
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))
warnings.filterwarnings("ignore", category=FutureWarning)

import koreanize_matplotlib  # noqa: F401
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer


DATA_PATH = ROOT / "data" / "seoul_culture_events.csv"
ENV_PATH = ROOT / ".env"
REPORT_DIR = ROOT / "report"
DOCS_IMAGE_DIR = ROOT / "docs" / "images"
DOCS_DATA_DIR = ROOT / "docs" / "data"
SEOUL_API_BASE_URL = "http://openapi.seoul.go.kr:8088"
SEOUL_API_SERVICE = "culturalEventInfo"

COLUMNS = {
    "category": "분류",
    "gu": "자치구",
    "title": "공연/행사명",
    "date": "날짜",
    "venue": "장소",
    "audience": "이용대상",
    "fee": "이용요금",
    "free_paid": "유무료",
    "theme": "테마분류",
    "longitude": "경도(Y좌표)",
    "latitude": "위도(X좌표)",
    "url": "문화포털상세URL",
    "time": "행사시간",
}

API_COLUMN_MAP = {
    "CODENAME": "분류",
    "GUNAME": "자치구",
    "TITLE": "공연/행사명",
    "DATE": "날짜",
    "PLACE": "장소",
    "ORG_NAME": "기관명",
    "USE_TRGT": "이용대상",
    "USE_FEE": "이용요금",
    "INQUIRY": "문의",
    "PLAYER": "출연자정보",
    "PROGRAM": "프로그램소개",
    "ETC_DESC": "기타내용",
    "ORG_LINK": "홈페이지?주소",
    "MAIN_IMG": "대표이미지",
    "RGSTDATE": "신청일",
    "TICKET": "시민/기관",
    "STRTDATE": "시작일",
    "END_DATE": "종료일",
    "THEMECODE": "테마분류",
    "LOT": "경도(Y좌표)",
    "LAT": "위도(X좌표)",
    "IS_FREE": "유무료",
    "HMPG_ADDR": "문화포털상세URL",
    "TIME": "행사시간",
}

TAG_RULES = {
    "무료": ["가성비", "무료"],
    "유료": ["유료"],
    "전시/미술": ["전시", "실내"],
    "교육/체험": ["체험", "이색데이트"],
    "클래식": ["공연", "클래식", "감성"],
    "콘서트": ["공연", "음악"],
    "연극": ["공연", "연극"],
    "뮤지컬/오페라": ["공연", "뮤지컬"],
    "축제": ["축제", "야외"],
    "도서": ["북데이트", "정적인"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deco Admin 문화행사 EDA 리포트와 추천 후보 데이터를 생성합니다.")
    parser.add_argument(
        "--source",
        choices=["auto", "api", "csv"],
        default="auto",
        help="데이터 원천입니다. auto는 API 키가 있으면 API, 없으면 CSV를 사용합니다.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="API에서 가져올 최대 행 수입니다. 0이면 전체 데이터를 가져옵니다.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="API 1회 요청당 행 수입니다.",
    )
    return parser.parse_args()


def load_env_file() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_csv() -> pd.DataFrame:
    try:
        return pd.read_csv(DATA_PATH, encoding="cp949")
    except UnicodeDecodeError:
        return pd.read_csv(DATA_PATH, encoding="utf-8")


def fetch_api_page(api_key: str, start_index: int, end_index: int) -> dict:
    url = f"{SEOUL_API_BASE_URL}/{api_key}/json/{SEOUL_API_SERVICE}/{start_index}/{end_index}/"
    request = urllib.request.Request(url, headers={"User-Agent": "DecoAdmin/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"서울 열린데이터광장 API 호출에 실패했습니다: {exc}") from exc


def extract_api_payload(payload: dict) -> tuple[list[dict], int]:
    if SEOUL_API_SERVICE not in payload:
        result = payload.get("RESULT") or {}
        code = result.get("CODE", "UNKNOWN")
        message = result.get("MESSAGE", "응답에 culturalEventInfo가 없습니다.")
        raise RuntimeError(f"서울 API 오류: {code} - {message}")

    body = payload[SEOUL_API_SERVICE]
    result = body.get("RESULT") or {}
    code = result.get("CODE")
    if code and code != "INFO-000":
        raise RuntimeError(f"서울 API 오류: {code} - {result.get('MESSAGE', '')}")
    return body.get("row", []), int(body.get("list_total_count", 0))


def normalize_api_rows(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows).rename(columns=API_COLUMN_MAP)
    for column in API_COLUMN_MAP.values():
        if column not in df.columns:
            df[column] = None
    if df["날짜"].isna().all():
        df["날짜"] = df["시작일"].fillna("") + "~" + df["종료일"].fillna("")
    for column in ["경도(Y좌표)", "위도(X좌표)"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df[list(API_COLUMN_MAP.values())]


def read_api(max_rows: int = 0, batch_size: int = 1000) -> pd.DataFrame:
    api_key = os.getenv("SEOUL_OPEN_API_KEY")
    if not api_key:
        raise RuntimeError("SEOUL_OPEN_API_KEY 환경변수가 없습니다. .env 파일 또는 쉘 환경변수로 설정해 주세요.")

    rows = []
    start = 1
    total_count = None
    batch_size = max(1, min(batch_size, 1000))

    while True:
        if max_rows:
            end = min(start + batch_size - 1, max_rows)
        else:
            end = start + batch_size - 1
        page_rows, discovered_total = extract_api_payload(fetch_api_page(api_key, start, end))
        if total_count is None:
            total_count = min(discovered_total, max_rows) if max_rows else discovered_total
        rows.extend(page_rows)
        if len(rows) >= total_count or not page_rows:
            break
        start = end + 1

    return normalize_api_rows(rows[:total_count])


def read_source(source: str, max_rows: int, batch_size: int) -> tuple[pd.DataFrame, str]:
    load_env_file()
    if source == "api" or (source == "auto" and os.getenv("SEOUL_OPEN_API_KEY")):
        return read_api(max_rows=max_rows, batch_size=batch_size), "서울 열린데이터광장 Open API"
    return read_csv(), "로컬 CSV"


def require_columns(df: pd.DataFrame) -> None:
    missing = [column for column in COLUMNS.values() if column not in df.columns]
    if missing:
        raise KeyError(f"필수 컬럼이 없습니다: {', '.join(missing)}")


def save_plot(filename: str) -> str:
    plt.tight_layout()
    DOCS_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCS_IMAGE_DIR / filename
    plt.savefig(path, dpi=160)
    plt.close()
    return f"../docs/images/{filename}"


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    date_range = result[COLUMNS["date"]].astype(str).str.split("~")
    result["분석_시작일"] = pd.to_datetime(date_range.str[0], errors="coerce")
    result["분석_종료일"] = pd.to_datetime(date_range.str[-1], errors="coerce")
    result["분석_월"] = result["분석_시작일"].dt.month
    result["분석_요일"] = result["분석_시작일"].dt.day_name()
    result["분석_기간"] = (result["분석_종료일"] - result["분석_시작일"]).dt.days + 1
    result["분석_기간분류"] = pd.cut(
        result["분석_기간"],
        bins=[0, 3, 14, float("inf")],
        labels=["단기(3일이내)", "중기(4-14일)", "장기(15일이상)"],
        include_lowest=True,
    )
    return result


def build_tags(row: pd.Series) -> list[str]:
    tags = []
    haystack = " ".join(
        str(row.get(column, ""))
        for column in [COLUMNS["category"], COLUMNS["title"], COLUMNS["venue"], COLUMNS["free_paid"], COLUMNS["theme"]]
    )
    for keyword, mapped_tags in TAG_RULES.items():
        if keyword in haystack:
            tags.extend(mapped_tags)
    if "19:" in str(row.get(COLUMNS["time"], "")) or "20:" in str(row.get(COLUMNS["time"], "")):
        tags.append("야간")
    if row.get(COLUMNS["gu"]) in {"종로구", "중구", "서초구", "마포구"}:
        tags.append("인기지역")
    return list(dict.fromkeys(tags))[:5]


def score_recommendation(row: pd.Series) -> float:
    score = 6.0
    category = str(row.get(COLUMNS["category"], ""))
    free_paid = str(row.get(COLUMNS["free_paid"], ""))
    gu = str(row.get(COLUMNS["gu"], ""))
    duration = row.get("분석_기간")
    weekday = str(row.get("분석_요일", ""))

    if category in {"전시/미술", "교육/체험", "클래식", "콘서트"}:
        score += 1.0
    if free_paid == "무료":
        score += 0.8
    if gu in {"종로구", "중구", "서초구", "마포구", "송파구"}:
        score += 0.7
    if pd.notna(duration) and 1 <= duration <= 14:
        score += 0.5
    if weekday in {"Friday", "Saturday", "Sunday"}:
        score += 0.5
    if pd.notna(row.get(COLUMNS["longitude"])) and pd.notna(row.get(COLUMNS["latitude"])):
        score += 0.3
    return round(min(score, 9.8), 1)


def build_reason(row: pd.Series) -> str:
    gu = row.get(COLUMNS["gu"], "서울")
    category = row.get(COLUMNS["category"], "문화행사")
    free_paid = row.get(COLUMNS["free_paid"], "")
    venue = row.get(COLUMNS["venue"], "주요 장소")
    price_phrase = "무료로 즐길 수 있어 부담이 낮고, " if free_paid == "무료" else ""
    return f"{price_phrase}{gu}의 {venue}에서 진행되는 {category} 콘텐츠로 데이트 코스에 연결하기 좋습니다."


def write_recommendations(df: pd.DataFrame) -> None:
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    candidates = df.dropna(subset=[COLUMNS["title"], COLUMNS["gu"], COLUMNS["venue"]]).copy()
    active_or_upcoming = candidates[candidates["분석_종료일"] >= pd.Timestamp.today().normalize()]
    if not active_or_upcoming.empty:
        candidates = active_or_upcoming
    candidates["추천점수"] = candidates.apply(score_recommendation, axis=1)
    candidates = candidates.sort_values(["추천점수", "분석_시작일"], ascending=[False, True])

    records = []
    for _, row in candidates.iterrows():
        records.append(
            {
                "name": row[COLUMNS["title"]],
                "gu": row[COLUMNS["gu"]],
                "venue": row[COLUMNS["venue"]],
                "category": row[COLUMNS["category"]],
                "tags": build_tags(row),
                "score": row["추천점수"],
                "reason": build_reason(row),
                "startDate": row["분석_시작일"].strftime("%Y-%m-%d") if pd.notna(row["분석_시작일"]) else "",
                "endDate": row["분석_종료일"].strftime("%Y-%m-%d") if pd.notna(row["분석_종료일"]) else "",
                "latitude": row[COLUMNS["latitude"]] if pd.notna(row[COLUMNS["latitude"]]) else None,
                "longitude": row[COLUMNS["longitude"]] if pd.notna(row[COLUMNS["longitude"]]) else None,
                "url": row[COLUMNS["url"]],
            }
        )

    json_text = json.dumps(records, ensure_ascii=False, indent=2)
    (DOCS_DATA_DIR / "recommendations.json").write_text(json_text + "\n", encoding="utf-8")
    (DOCS_DATA_DIR / "recommendations.js").write_text(
        "window.DECO_RECOMMENDATIONS = " + json_text + ";\n",
        encoding="utf-8",
    )


def write_filter_options(df: pd.DataFrame) -> None:
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    options = {
        "gu": sorted(df[COLUMNS["gu"]].dropna().unique().tolist()),
        "category": sorted(df[COLUMNS["category"]].dropna().unique().tolist()),
        "tag": sorted({tag for _, row in df.iterrows() for tag in build_tags(row)}),
    }
    json_text = json.dumps(options, ensure_ascii=False, indent=2)
    (DOCS_DATA_DIR / "filter-options.json").write_text(json_text + "\n", encoding="utf-8")
    (DOCS_DATA_DIR / "filter-options.js").write_text(
        "window.DECO_FILTER_OPTIONS = " + json_text + ";\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    REPORT_DIR.mkdir(exist_ok=True)
    raw_df, source_label = read_source(args.source, args.max_rows, args.batch_size)
    require_columns(raw_df)
    df = normalize_dates(raw_df)
    require_columns(df)

    cols = df.columns.tolist()
    info_str = f"전체 데이터 수: {len(df)}행, {len(cols)}열\n"
    info_str += f"중복 데이터 수: {df.duplicated().sum()}\n"
    info_str += "주요 결측치:\n"
    info_str += df[list(COLUMNS.values())].isna().sum().to_markdown()

    desc_num = df.describe().to_markdown()
    desc_cat = df.describe(include=["object", "str", "category"]).to_markdown()
    graphs = []

    plt.figure(figsize=(12, 6))
    sns.countplot(data=df, y=COLUMNS["category"], order=df[COLUMNS["category"]].value_counts().index[:30], palette="viridis")
    plt.title("행사 분류별 빈도 (상위 30개)")
    graphs.append(
        {
            "title": "행사 분류별 빈도 분석",
            "image": save_plot("01_event_category_counts.png"),
            "insight": "교육/체험, 전시/미술, 클래식처럼 데이트 테마로 전환하기 쉬운 장르가 어느 정도의 규모를 갖는지 확인하는 기본 분포입니다.",
            "table": df[COLUMNS["category"]].value_counts().head(10).to_frame("count").to_markdown(),
        }
    )

    plt.figure(figsize=(12, 8))
    sns.countplot(data=df, y=COLUMNS["gu"], order=df[COLUMNS["gu"]].value_counts().index, palette="magma")
    plt.title("자치구별 문화 행사 개최 현황")
    graphs.append(
        {
            "title": "자치구별 행사 개최 현황",
            "image": save_plot("02_gu_event_counts.png"),
            "insight": "종로구와 중구처럼 행사 밀도가 높은 지역은 초기 추천 코스의 거점으로 삼기 좋고, 낮은 지역은 보완 큐레이션이 필요합니다.",
            "table": df[COLUMNS["gu"]].value_counts().head(10).to_frame("count").to_markdown(),
        }
    )

    plt.figure(figsize=(8, 8))
    df[COLUMNS["free_paid"]].value_counts().plot.pie(autopct="%1.1f%%", colors=["#ff9999", "#66b3ff"])
    plt.title("행사 유료/무료 비중")
    graphs.append(
        {
            "title": "행사 유료/무료 비중 분석",
            "image": save_plot("03_is_free_pie.png"),
            "insight": "원본의 유무료 컬럼을 기준으로 비용 접근성을 확인합니다. 무료 행사는 가성비 데이트 태그와 초기 유입 콘텐츠에 직접 활용할 수 있습니다.",
            "table": df[COLUMNS["free_paid"]].value_counts().to_frame("count").to_markdown(),
        }
    )

    monthly_counts = df["분석_월"].value_counts().sort_index()
    plt.figure(figsize=(10, 5))
    sns.lineplot(x=monthly_counts.index, y=monthly_counts.values, marker="o", color="blue")
    plt.xticks(range(1, 13))
    plt.title("월별 문화 행사 개최 트렌드")
    plt.xlabel("월")
    plt.ylabel("행사 수")
    graphs.append(
        {
            "title": "월별 행사 개최 트렌드",
            "image": save_plot("04_monthly_trend.png"),
            "insight": "행사가 집중되는 월을 보면 시즌 기획과 추천 슬롯 운영 시점을 정할 수 있으며, 비수기에는 상설 전시형 콘텐츠를 보강해야 합니다.",
            "table": monthly_counts.to_frame("count").to_markdown(),
        }
    )

    plt.figure(figsize=(12, 6))
    sns.countplot(data=df, y=COLUMNS["audience"], order=df[COLUMNS["audience"]].value_counts().index[:15], palette="Set3")
    plt.title("주요 관람 대상별 행사 수")
    graphs.append(
        {
            "title": "관람 대상별 분포",
            "image": save_plot("05_target_audience.png"),
            "insight": "커플 데이트에 적합한 누구나, 성인, 청소년 이상 콘텐츠의 비중을 파악해 앱 추천 제외 조건과 우선 조건을 설계할 수 있습니다.",
            "table": df[COLUMNS["audience"]].value_counts().head(10).to_frame("count").to_markdown(),
        }
    )

    gu_pay_cross = pd.crosstab(df[COLUMNS["gu"]], df[COLUMNS["free_paid"]])
    gu_pay_cross.plot(kind="bar", stacked=True, figsize=(12, 7), color=["#66b3ff", "#ff9999"])
    plt.title("자치구별 유/무료 행사 비중")
    graphs.append(
        {
            "title": "자치구별 유/무료 행사 교차 분석",
            "image": save_plot("06_gu_pay_cross.png"),
            "insight": "지역별 무료 콘텐츠 규모를 비교하면 가성비 코스가 강한 자치구와 유료 공연 중심 자치구를 분리해 큐레이션할 수 있습니다.",
            "table": gu_pay_cross.head(10).to_markdown(),
        }
    )

    plt.figure(figsize=(12, 8))
    sns.countplot(data=df, y=COLUMNS["venue"], order=df[COLUMNS["venue"]].value_counts().index[:20], palette="coolwarm")
    plt.title("주요 행사 장소 TOP 20")
    graphs.append(
        {
            "title": "주요 행사 장소 분석",
            "image": save_plot("07_top_venues.png"),
            "insight": "반복적으로 행사가 열리는 장소는 운영자가 장소 상세, 주변 이동 동선, 근처 카페를 미리 보강하기 좋은 거점입니다.",
            "table": df[COLUMNS["venue"]].value_counts().head(10).to_frame("count").to_markdown(),
        }
    )

    plt.figure(figsize=(8, 8))
    df["분석_기간분류"].value_counts().plot.pie(autopct="%1.1f%%", colors=["#ffcc99", "#99ffcc", "#cc99ff"])
    plt.title("행사 기간별 비중")
    graphs.append(
        {
            "title": "행사 기간 비중 분석",
            "image": save_plot("08_duration_pie.png"),
            "insight": "단기 행사는 주말 추천에, 장기 행사는 홈 화면의 안정적인 상시 추천 콘텐츠에 배치하는 식으로 운영 전략을 나눌 수 있습니다.",
            "table": df["분석_기간분류"].value_counts().to_frame("count").to_markdown(),
        }
    )

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, x="분석_요일", order=day_order, palette="husl")
    plt.title("요일별 행사 시작 빈도")
    graphs.append(
        {
            "title": "요일별 행사 시작 현황",
            "image": save_plot("09_day_of_week.png"),
            "insight": "금요일과 토요일 시작 행사의 규모를 보면 주말 데이트 푸시 알림, 홈 추천 갱신, 큐레이션 마감 시점을 정할 수 있습니다.",
            "table": df["분석_요일"].value_counts().reindex(day_order).to_frame("count").to_markdown(),
        }
    )

    tfidf = TfidfVectorizer(max_features=30, token_pattern=r"(?u)\b[^\d\W][\w/+-]{1,}\b")
    tfidf_matrix = tfidf.fit_transform(df[COLUMNS["title"]].dropna())
    kw_df = pd.DataFrame(
        {
            "keyword": tfidf.get_feature_names_out(),
            "weight": tfidf_matrix.sum(axis=0).A1,
        }
    ).sort_values("weight", ascending=False)

    plt.figure(figsize=(12, 8))
    sns.barplot(data=kw_df, x="weight", y="keyword", palette="Blues_r")
    plt.title("행사명 주요 키워드 TOP 30 (TF-IDF)")
    graphs.append(
        {
            "title": "핵심 키워드 분석 (TF-IDF)",
            "image": save_plot("10_keywords_tfidf.png"),
            "insight": "연도 숫자 같은 노이즈를 줄이고 실제 테마성 단어를 추출해 앱 태그 후보와 검색 필터 우선순위를 정하는 데 활용합니다.",
            "table": kw_df.head(20).to_markdown(index=False),
        }
    )

    write_recommendations(df)
    write_filter_options(df)

    report_content = f"""# 서울시 문화행사 정보 탐색적 데이터 분석(EDA) 보고서

## 1. 요약
본 보고서는 서울시에서 제공하는 문화행사 데이터를 바탕으로, Deco 앱의 초기 추천 콘텐츠 운영에 필요한 행사 분류, 지역별 분포, 비용 구조, 시계열 트렌드 및 핵심 키워드를 분석한 결과를 담고 있습니다.

## 2. 기초 데이터 정보
- **데이터 원천**: {source_label}
- **전체 데이터 규모**: {len(df)}건
- **컬럼 구성**: {", ".join(cols)}
- **데이터 결측치 및 무결성**
{info_str}

## 3. 기술통계 분석

### [범주형 변수 요약]
{desc_cat}

### [수치형 변수 요약]
{desc_num}

---

## 4. 상세 시각화 인사이트
"""

    for graph in graphs:
        report_content += f"""
### {graph["title"]}
![{graph["title"]}]({graph["image"]})

**[분석 결과 및 인사이트]**
{graph["insight"]}

**[통계표]**
{graph["table"]}

---
"""

    report_content += """
## 5. Deco Admin 운영 제언
- **초기 거점**: 종로구, 중구, 서초구, 마포구처럼 행사가 많은 지역을 중심으로 홈 추천 코스를 먼저 구성합니다.
- **태그 체계**: 무료, 전시, 체험, 공연, 야간처럼 원본 데이터에서 안정적으로 추출 가능한 태그를 1차 필터로 사용합니다.
- **주말 운영**: 금요일과 토요일 시작 행사를 기준으로 목요일 오후에 주말 추천 후보를 확정하는 운영 흐름이 적합합니다.
- **데이터 연결**: 생성된 `docs/data/recommendations.json` 파일은 Deco 앱 홈 추천, 상세 설명, 지도 후보 데이터의 초기 원천으로 활용할 수 있습니다.
- **필터 운영**: 생성된 `docs/data/filter-options.json` 파일은 전체 데이터 기준의 지역, 분류, 태그 필터 목록으로 활용할 수 있습니다.
"""

    (REPORT_DIR / "EDA_Report.md").write_text(report_content, encoding="utf-8")
    print("EDA 리포트와 추천 후보 데이터 생성이 완료되었습니다.")


if __name__ == "__main__":
    main()
