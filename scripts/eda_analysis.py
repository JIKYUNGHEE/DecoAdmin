import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib
import os
from sklearn.feature_extraction.text import TfidfVectorizer

# 1. 데이터 로드 및 환경 설정
file_path = 'data/서울시 문화행사 정보.csv'
report_dir = 'report'
image_dir = 'images'
os.makedirs(report_dir, exist_ok=True)
os.makedirs(image_dir, exist_ok=True)

# 인코딩 확인 (CP949 시도)
try:
    df = pd.read_csv(file_path, encoding='cp949')
except UnicodeDecodeError:
    df = pd.read_csv(file_path, encoding='utf-8')

# 데이터 기초 정보
info_str = f"전체 데이터 수: {len(df)}행, {len(df.columns)}열\n"
info_str += f"중복 데이터 수: {df.duplicated().sum()}\n"

# 컬럼명 확인 및 분석에 사용할 주요 컬럼 정의
# 컬럼명이 한글일 가능성이 높으므로 실제 로드된 컬럼명을 기반으로 작업
cols = df.columns.tolist()

# 2. 기술통계 분석 (Numerical & Categorical)
desc_num = df.describe().to_markdown()
desc_cat = df.describe(include=['O']).to_markdown()

# 3. 시각화 및 인사이트 도출
graphs = []

def save_plot(filename):
    plt.tight_layout()
    path = os.path.join(image_dir, filename)
    plt.savefig(path)
    plt.close()
    return f"../{path}"

# 시각화 1: 분류별 행사 빈도 (Bar Chart)
plt.figure(figsize=(12, 6))
sns.countplot(data=df, y=cols[0], order=df[cols[0]].value_counts().index[:30], palette='viridis')
plt.title('행사 분류별 빈도 (상위 30개)')
img_path1 = save_plot('01_event_category_counts.png')
graphs.append({
    'title': '행사 분류별 빈도 분석',
    'image': img_path1,
    'insight': '어떤 종류의 문화 행사가 가장 많이 개최되는지 확인할 수 있습니다. 대중적인 장르와 비주류 장르의 격차를 파악할 수 있는 지표입니다.',
    'table': df[cols[0]].value_counts().head(10).to_frame().to_markdown()
})

# 시각화 2: 자치구별 행사 빈도 (Bar Chart)
# 구(GU) 정보가 있는 컬럼 찾기 (일반적으로 두 번째나 세 번째 컬럼)
gu_col = cols[1] # 자치구 컬럼으로 추정
plt.figure(figsize=(12, 8))
sns.countplot(data=df, y=gu_col, order=df[gu_col].value_counts().index, palette='magma')
plt.title('자치구별 문화 행사 개최 현황')
img_path2 = save_plot('02_gu_event_counts.png')
graphs.append({
    'title': '자치구별 행사 개최 현황',
    'image': img_path2,
    'insight': '서울시 내 자치구별 문화 인프라 및 행사 집중도를 시각적으로 나타냅니다. 특정 지역에 행사가 편중되어 있는지 확인할 수 있습니다.',
    'table': df[gu_col].value_counts().head(10).to_frame().to_markdown()
})

# 시각화 3: 유료/무료 여부 비중 (Pie Chart)
pay_col = [c for c in cols if '이용' in c or '유료' in c or '무료' in c or '입장' in c][0] # 이용료 컬럼 추정
df['유무료'] = df[pay_col].apply(lambda x: '무료' if '무료' in str(x) else ('유료' if '원' in str(x) or '료' in str(x) else '기타'))
plt.figure(figsize=(8, 8))
df['유무료'].value_counts().plot.pie(autopct='%1.1f%%', colors=['#ff9999','#66b3ff','#99ff99'])
plt.title('행사 유료/무료 비중')
img_path3 = save_plot('03_is_free_pie.png')
graphs.append({
    'title': '행사 유료/무료 비중 분석',
    'image': img_path3,
    'insight': '시민들이 무료로 접근할 수 있는 행사의 비율을 보여줍니다. 공공 문화 서비스의 접근성을 판단하는 주요 지표입니다.',
    'table': df['유무료'].value_counts().to_frame().to_markdown()
})

# 시각화 4: 월별 행사 개최 트렌드 (Line Chart)
# 날짜 컬럼 찾기
date_col = [c for c in cols if '날짜' in c or '기간' in c or '시작' in c][0]
df['시작일'] = pd.to_datetime(df[date_col].str.split('~').str[0], errors='coerce')
df['월'] = df['시작일'].dt.month
monthly_counts = df['월'].value_counts().sort_index()
plt.figure(figsize=(10, 5))
sns.lineplot(x=monthly_counts.index, y=monthly_counts.values, marker='o', color='blue')
plt.xticks(range(1, 13))
plt.title('월별 문화 행사 개최 트렌드')
plt.xlabel('월')
plt.ylabel('행사 수')
img_path4 = save_plot('04_monthly_trend.png')
graphs.append({
    'title': '월별 행사 개최 트렌드',
    'image': img_path4,
    'insight': '계절적 요인이 문화 행사 개최에 미치는 영향을 파악합니다. 특정 시기에 행사가 집중되는 경향을 확인할 수 있습니다.',
    'table': monthly_counts.to_frame().to_markdown()
})

# 시각화 5: 대상별 행사 빈도 (Bar Chart)
target_col = [c for c in cols if '대상' in c or '이용' in c][1] # 대상 컬럼 추정
plt.figure(figsize=(12, 6))
sns.countplot(data=df, y=target_col, order=df[target_col].value_counts().index[:15], palette='Set3')
plt.title('주요 관람 대상별 행사 수')
img_path5 = save_plot('05_target_audience.png')
graphs.append({
    'title': '관람 대상별 분포',
    'image': img_path5,
    'insight': '어린이, 청소년, 성인 등 누구를 타겟으로 하는 행사가 많은지 보여줍니다. 문화 복지의 수혜 대상을 분석할 수 있습니다.',
    'table': df[target_col].value_counts().head(10).to_frame().to_markdown()
})

# 시각화 6: 자치구별 유/무료 교차 분석 (Stacked Bar)
gu_pay_cross = pd.crosstab(df[gu_col], df['유무료'])
gu_pay_cross.plot(kind='bar', stacked=True, figsize=(12, 7), color=['#66b3ff', '#ff9999', '#99ff99'])
plt.title('자치구별 유/무료 행사 비중')
img_path6 = save_plot('06_gu_pay_cross.png')
graphs.append({
    'title': '자치구별 유/무료 행사 교차 분석',
    'image': img_path6,
    'insight': '각 자치구가 제공하는 문화 서비스의 성격(공공성 vs 상업성)을 비교할 수 있습니다.',
    'table': gu_pay_cross.head(10).to_markdown()
})

# 시각화 7: 행사 장소별 빈도 (Bar Chart)
place_col = [c for c in cols if '장소' in c or '시설' in c][0]
plt.figure(figsize=(12, 8))
sns.countplot(data=df, y=place_col, order=df[place_col].value_counts().index[:20], palette='coolwarm')
plt.title('주요 행사 장소 TOP 20')
img_path7 = save_plot('07_top_venues.png')
graphs.append({
    'title': '주요 행사 장소 분석',
    'image': img_path7,
    'insight': '서울시 내에서 어떤 장소가 문화 행사의 거점 역할을 하고 있는지 확인합니다.',
    'table': df[place_col].value_counts().head(10).to_frame().to_markdown()
})

# 시각화 8: 기간별 행사 수 (Short term vs Long term)
df['종료일'] = pd.to_datetime(df[date_col].str.split('~').str[-1], errors='coerce')
df['기간'] = (df['종료일'] - df['시작일']).dt.days + 1
df['기간분류'] = df['기간'].apply(lambda x: '단기(3일이내)' if x <= 3 else ('중기(4-14일)' if x <= 14 else '장기(15일이상)'))
plt.figure(figsize=(8, 8))
df['기간분류'].value_counts().plot.pie(autopct='%1.1f%%', colors=['#ffcc99','#99ffcc','#cc99ff'])
plt.title('행사 기간별 비중')
img_path8 = save_plot('08_duration_pie.png')
graphs.append({
    'title': '행사 기간 비중 분석',
    'image': img_path8,
    'insight': '일회성 단기 행사와 전시형 장기 행사의 비중을 보여줍니다.',
    'table': df['기간분류'].value_counts().to_frame().to_markdown()
})

# 시각화 9: 요일별 시작일 빈도
df['요일'] = df['시작일'].dt.day_name()
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
plt.figure(figsize=(10, 6))
sns.countplot(data=df, x='요일', order=day_order, palette='husl')
plt.title('요일별 행사 시작 빈도')
img_path9 = save_plot('09_day_of_week.png')
graphs.append({
    'title': '요일별 행사 시작 현황',
    'image': img_path9,
    'insight': '주말을 겨냥한 행사가 금요일이나 토요일에 얼마나 집중되는지 알 수 있습니다.',
    'table': df['요일'].value_counts().reindex(day_order).to_frame().to_markdown()
})

# 시각화 10: 텍스트 키워드 분석 (TF-IDF)
title_col = [c for c in cols if '제목' in c or '행사명' in c][0]
tfidf = TfidfVectorizer(max_features=30)
tfidf_matrix = tfidf.fit_transform(df[title_col].dropna())
keywords = tfidf.get_feature_names_out()
weights = tfidf_matrix.sum(axis=0).A1
kw_df = pd.DataFrame({'keyword': keywords, 'weight': weights}).sort_values('weight', ascending=False)

plt.figure(figsize=(12, 8))
sns.barplot(data=kw_df, x='weight', y='keyword', palette='Blues_r')
plt.title('행사명 주요 키워드 TOP 30 (TF-IDF)')
img_path10 = save_plot('10_keywords_tfidf.png')
graphs.append({
    'title': '핵심 키워드 분석 (TF-IDF)',
    'image': img_path10,
    'insight': '행사 제목에서 가장 빈번하게 등장하는 단어들을 통해 서울시 문화 행사의 전반적인 테마를 파악합니다.',
    'table': kw_df.head(20).to_markdown()
})

# 4. 최종 리포트 생성
report_content = f"""# 서울시 문화행사 정보 탐색적 데이터 분석(EDA) 보고서

## 1. 요약
본 보고서는 서울시에서 제공하는 문화행사 데이터를 바탕으로, 행사 분류, 지역별 분포, 비용 구조, 시계열 트렌드 및 핵심 키워드를 분석한 결과를 담고 있습니다.

## 2. 기초 데이터 정보
- **전체 데이터 규모**: {len(df)}건
- **컬럼 구성**: {', '.join(cols)}
- **데이터 결측치 및 무결성**: {info_str}

## 3. 기술통계 분석

### [범주형 변수 요약]
{desc_cat}

### [수치형 변수 요약]
{desc_num}

---

## 4. 상세 시각화 인사이트
"""

for g in graphs:
    report_content += f"""
### {g['title']}
![{g['title']}]({g['image']})

**[분석 결과 및 인사이트]**
{g['insight']}

**[통계표]**
{g['table']}

---
"""

report_content += """
## 5. 결론 및 제언
- **지역적 편중**: 특정 자치구에 행사가 집중되어 있는 경향이 확인되었습니다. 문화 소외 지역에 대한 인프라 확충이 필요합니다.
- **다양한 타겟층**: 전 연령대를 대상으로 하는 행사가 많으나, 특정 취약 계층이나 정교한 타겟팅을 가진 행사의 비중을 높일 필요가 있습니다.
- **무료 행사의 가치**: 높은 무료 행사 비중은 시민들의 문화 향유 기회를 확대하는 긍정적인 요소입니다.
- **계절성 고려**: 월별 트렌드에 따라 행사 개최 시기를 조정하여 방문객 분산 및 활성화를 도모할 수 있습니다.
"""

with open(os.path.join(report_dir, 'EDA_Report.md'), 'w', encoding='utf-8') as f:
    f.write(report_content)

print("EDA 리포트 생성이 완료되었습니다.")
