const fallbackData = [
    {
        name: "2026 핸디아티코리아",
        gu: "강남구",
        venue: "코엑스",
        category: "전시/미술",
        tags: ["체험", "실내", "전시", "가성비"],
        score: 9.2,
        reason: "강남권 대규모 전시로 다양한 핸드메이드 체험이 가능함",
        startDate: "2026-08-13",
        endDate: "2026-08-16",
        latitude: 37.511824,
        longitude: 127.059159,
        url: "",
    },
];

const state = {
    recommendations: [],
    selectedIds: new Set(),
    activeId: "",
};

function getCandidateId(item) {
    return [item.name, item.startDate, item.venue].join("|");
}

function formatDateRange(item) {
    if (!item.startDate && !item.endDate) {
        return "";
    }
    if (!item.endDate || item.startDate === item.endDate) {
        return item.startDate;
    }
    return `${item.startDate} ~ ${item.endDate}`;
}

function formatCoordinate(item) {
    if (item.latitude == null || item.longitude == null) {
        return "좌표 없음";
    }
    return `${Number(item.latitude).toFixed(5)}, ${Number(item.longitude).toFixed(5)}`;
}

function appendCell(row, value, className) {
    const cell = document.createElement("td");
    if (className) {
        cell.className = className;
    }
    cell.textContent = value ?? "";
    row.appendChild(cell);
    return cell;
}

function appendNameCell(row, item) {
    const cell = document.createElement("td");
    const strong = document.createElement("strong");
    const meta = document.createElement("span");

    strong.textContent = item.name ?? "";
    meta.className = "candidate-meta";
    meta.textContent = formatCoordinate(item);

    cell.append(strong, meta);
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

function appendSelectCell(row, id) {
    const cell = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "candidate-check";
    checkbox.checked = state.selectedIds.has(id);
    checkbox.setAttribute("aria-label", "앱 등록 후보 선택");
    checkbox.addEventListener("change", (event) => {
        if (event.target.checked) {
            state.selectedIds.add(id);
        } else {
            state.selectedIds.delete(id);
        }
        updateSummary(getFilteredData());
    });
    cell.appendChild(checkbox);
    row.appendChild(cell);
}

function appendLinkCell(row, item) {
    const cell = document.createElement("td");
    if (item.url) {
        const link = document.createElement("a");
        link.href = item.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "보기";
        cell.appendChild(link);
    } else {
        cell.textContent = "-";
    }
    row.appendChild(cell);
}

function updateSummary(data) {
    document.getElementById("candidate-count").textContent = `추천 후보 ${data.length}개`;
    document.getElementById("selected-count").textContent = `앱 등록 후보 ${state.selectedIds.size}개`;
}

function renderTable(data) {
    const tbody = document.getElementById("recommendation-body");
    tbody.replaceChildren();

    data.forEach((item) => {
        const id = getCandidateId(item);
        const row = document.createElement("tr");
        row.tabIndex = 0;
        row.className = id === state.activeId ? "is-active" : "";
        row.addEventListener("click", (event) => {
            if (event.target.closest("a") || event.target.closest("input")) {
                return;
            }
            state.activeId = id;
            renderDetail(item);
            renderTable(getFilteredData());
        });
        row.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                state.activeId = id;
                renderDetail(item);
                renderTable(getFilteredData());
            }
        });

        appendSelectCell(row, id);
        appendNameCell(row, item);
        appendCell(row, item.gu);
        appendCell(row, item.venue);
        appendCell(row, item.category);
        appendTagsCell(row, item.tags);
        appendScoreCell(row, item.score);
        appendCell(row, formatDateRange(item), "date-cell");
        appendLinkCell(row, item);
        appendCell(row, item.reason);

        tbody.appendChild(row);
    });

    updateSummary(data);
}

function renderDetail(item) {
    const panel = document.getElementById("candidate-detail");
    panel.replaceChildren();

    const title = document.createElement("h3");
    title.textContent = item.name;

    const meta = document.createElement("div");
    meta.className = "detail-grid";

    [
        ["지역", item.gu],
        ["장소", item.venue],
        ["분류", item.category],
        ["일정", formatDateRange(item)],
        ["좌표", formatCoordinate(item)],
        ["추천 점수", item.score],
    ].forEach(([label, value]) => {
        const block = document.createElement("div");
        const labelElement = document.createElement("span");
        const valueElement = document.createElement("strong");
        labelElement.textContent = label;
        valueElement.textContent = value ?? "";
        block.append(labelElement, valueElement);
        meta.appendChild(block);
    });

    const reason = document.createElement("p");
    reason.className = "detail-reason";
    reason.textContent = item.reason;

    const tags = document.createElement("div");
    tags.className = "detail-tags";
    (item.tags ?? []).forEach((tag) => {
        const tagElement = document.createElement("span");
        tagElement.className = "tag";
        tagElement.textContent = tag;
        tags.appendChild(tagElement);
    });

    panel.append(title, meta, tags, reason);

    if (item.url) {
        const link = document.createElement("a");
        link.href = item.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.className = "detail-link";
        link.textContent = "문화포털 상세 보기";
        panel.appendChild(link);
    }
}

function getControlValue(id) {
    return document.getElementById(id).value;
}

function getFilteredData() {
    const query = getControlValue("candidate-search").trim().toLowerCase();
    const gu = getControlValue("gu-filter");
    const category = getControlValue("category-filter");
    const tag = getControlValue("tag-filter");
    const selectedOnly = document.getElementById("selected-only").checked;
    const sort = getControlValue("sort-select");

    const filtered = state.recommendations.filter((item) => {
        const id = getCandidateId(item);
        const searchable = [item.name, item.gu, item.venue, item.category, item.reason, ...(item.tags ?? [])]
            .join(" ")
            .toLowerCase();
        return (!query || searchable.includes(query))
            && (!gu || item.gu === gu)
            && (!category || item.category === category)
            && (!tag || (item.tags ?? []).includes(tag))
            && (!selectedOnly || state.selectedIds.has(id));
    });

    return filtered.sort((a, b) => {
        if (sort === "date-asc") {
            return String(a.startDate ?? "").localeCompare(String(b.startDate ?? ""));
        }
        if (sort === "gu-asc") {
            return String(a.gu ?? "").localeCompare(String(b.gu ?? ""), "ko");
        }
        return Number(b.score ?? 0) - Number(a.score ?? 0);
    });
}

function populateSelect(id, values) {
    const select = document.getElementById(id);
    values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    });
}

function setupControls() {
    const unique = (values) => [...new Set(values.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), "ko"));
    populateSelect("gu-filter", unique(state.recommendations.map((item) => item.gu)));
    populateSelect("category-filter", unique(state.recommendations.map((item) => item.category)));
    populateSelect("tag-filter", unique(state.recommendations.flatMap((item) => item.tags ?? [])));

    ["candidate-search", "gu-filter", "category-filter", "tag-filter", "sort-select", "selected-only"].forEach((id) => {
        document.getElementById(id).addEventListener("input", () => {
            renderTable(getFilteredData());
        });
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
    state.recommendations = window.DECO_RECOMMENDATIONS?.length
        ? window.DECO_RECOMMENDATIONS
        : fallbackData;

    setupControls();
    renderTable(getFilteredData());
    if (state.recommendations.length > 0) {
        state.activeId = getCandidateId(state.recommendations[0]);
        renderDetail(state.recommendations[0]);
        renderTable(getFilteredData());
    }
    animateKpis();
});
