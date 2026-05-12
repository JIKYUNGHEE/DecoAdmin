const sampleData = [
    {
        name: "2026 핸디아티코리아",
        gu: "강남구",
        venue: "코엑스",
        category: "전시/미술",
        tags: ["체험", "실내", "전시", "가성비"],
        score: 9.2,
        reason: "강남권 대규모 전시로 다양한 핸드메이드 체험이 가능함",
        appSection: "홈 추천 코스"
    },
    {
        name: "재능 혜화 마티네",
        gu: "종로구",
        venue: "JCC아트센터",
        category: "클래식",
        tags: ["공연", "클래식", "종로", "감성"],
        score: 8.8,
        reason: "종로 데이트 코스의 정석, 수준 높은 클래식 공연",
        appSection: "홈 추천 코스"
    },
    {
        name: "이호철북콘서트홀 상설전시",
        gu: "은평구",
        venue: "이호철북콘서트홀",
        category: "전시/미술",
        tags: ["무료", "북데이트", "정적인"],
        score: 8.5,
        reason: "무료로 즐기는 문학 전시, 조용한 데이트 선호 커플 추천",
        appSection: "검색 필터 연동"
    },
    {
        name: "서울아트책보고 워크숍",
        gu: "구로구",
        venue: "서울아트책보고",
        category: "교육/체험",
        tags: ["체험", "이색데이트", "예술"],
        score: 9.0,
        reason: "직접 참여하는 예술 활동으로 커플간 추억 쌓기 최적",
        appSection: "코스 상세 가이드"
    },
    {
        name: "밤의 석촌호수 산책 음악회",
        gu: "송파구",
        venue: "석촌호수",
        category: "콘서트",
        tags: ["야간", "산책", "무료", "낭만"],
        score: 9.5,
        reason: "잠실 지역 최고의 야간 데이트 코스, 무료 음악 공연 포함",
        appSection: "지도/야간 테마"
    }
];

function renderTable(data) {
    const tbody = document.getElementById('recommendation-body');
    tbody.innerHTML = '';

    data.forEach(item => {
        const tr = document.createElement('tr');
        
        const tagsHtml = item.tags.map(tag => `<span class="tag">${tag}</span>`).join('');
        
        tr.innerHTML = `
            <td><strong>${item.name}</strong></td>
            <td>${item.gu}</td>
            <td>${item.venue}</td>
            <td>${item.category}</td>
            <td>${tagsHtml}</td>
            <td><span class="score">${item.score}</span></td>
            <td>${item.reason}</td>
        `;
        
        tbody.appendChild(tr);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    renderTable(sampleData);
    
    // Add simple animation to KPI cards
    const kpiValues = document.querySelectorAll('.kpi-card .value');
    kpiValues.forEach(val => {
        val.style.opacity = '0';
        val.style.transform = 'translateY(10px)';
        val.style.transition = 'all 0.6s ease';
        
        setTimeout(() => {
            val.style.opacity = '1';
            val.style.transform = 'translateY(0)';
        }, 300);
    });
});
