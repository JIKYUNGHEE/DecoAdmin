const fallbackData = [
    {
        name: "2026 핸디아티코리아",
        gu: "강남구",
        venue: "코엑스",
        category: "전시/미술",
        tags: ["체험", "실내", "전시", "가성비"],
        score: 9.2,
        reason: "강남권 대규모 전시로 다양한 핸드메이드 체험이 가능함",
    },
    {
        name: "재능 혜화 마티네",
        gu: "종로구",
        venue: "JCC아트센터",
        category: "클래식",
        tags: ["공연", "클래식", "종로", "감성"],
        score: 8.8,
        reason: "종로 데이트 코스의 정석, 수준 높은 클래식 공연",
    },
];

function appendCell(row, value, className) {
    const cell = document.createElement("td");
    if (className) {
        cell.className = className;
    }
    cell.textContent = value ?? "";
    row.appendChild(cell);
    return cell;
}

function appendNameCell(row, value) {
    const cell = document.createElement("td");
    const strong = document.createElement("strong");
    strong.textContent = value ?? "";
    cell.appendChild(strong);
    row.appendChild(cell);
}

function appendTagsCell(row, tags = []) {
    const cell = document.createElement("td");
    tags.forEach((tag) => {
        const tagElement = document.createElement("span");
        tagElement.className = "tag";
        tagElement.textContent = tag;
        cell.appendChild(tagElement);
    });
    row.appendChild(cell);
}

function appendScoreCell(row, score) {
    const cell = document.createElement("td");
    const scoreElement = document.createElement("span");
    scoreElement.className = "score";
    scoreElement.textContent = score ?? "";
    cell.appendChild(scoreElement);
    row.appendChild(cell);
}

function renderTable(data) {
    const tbody = document.getElementById("recommendation-body");
    tbody.replaceChildren();

    data.forEach((item) => {
        const row = document.createElement("tr");

        appendNameCell(row, item.name);
        appendCell(row, item.gu);
        appendCell(row, item.venue);
        appendCell(row, item.category);
        appendTagsCell(row, item.tags);
        appendScoreCell(row, item.score);
        appendCell(row, item.reason);

        tbody.appendChild(row);
    });
}

function animateKpis() {
    const kpiValues = document.querySelectorAll(".kpi-card .value");
    kpiValues.forEach((value) => {
        value.style.opacity = "0";
        value.style.transform = "translateY(10px)";
        value.style.transition = "all 0.6s ease";

        setTimeout(() => {
            value.style.opacity = "1";
            value.style.transform = "translateY(0)";
        }, 300);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const recommendations = window.DECO_RECOMMENDATIONS?.length
        ? window.DECO_RECOMMENDATIONS
        : fallbackData;

    renderTable(recommendations);
    animateKpis();
});
