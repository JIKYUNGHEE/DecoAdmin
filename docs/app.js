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
    quickTag: "",
    statuses: new Map(),
    map: null,
    markers: new Map(),
    markerLayer: null,
    insightCharts: [],
    reportCharts: [],
    modalChart: null,
};

const DISPLAY_LIMIT = 12;
const MAP_LIMIT = 20;
const EVENT_LIMIT = 60;
const STATUS_OPTIONS = ["검토 전", "앱 등록 후보", "등록 완료", "제외"];
const WEEKEND_TAG = "주말";

function buildChartOptions(chart, isModal = false) {
    const isPointData = Array.isArray(chart.data) && chart.data.some((point) => typeof point === "object");
    const categories = chart.categories ?? (isPointData ? chart.data.map((point) => point.name) : []);
    const data = isPointData ? chart.data.map((point) => point.y) : chart.data;
    const type = chart.type ?? "column";

    return {
        chart: {
            type,
            backgroundColor: "transparent",
            height: isModal ? 520 : 300,
            spacing: [12, 8, 8, 8],
        },
        title: { text: null },
        credits: { enabled: false },
        legend: { enabled: false },
        tooltip: {
            pointFormat: `<b>{point.y:,.0f}</b> ${chart.yAxisTitle ?? ""}`,
        },
        xAxis: {
            categories,
            title: { text: isModal ? chart.xAxisTitle : null },
            labels: {
                style: { color: "#667085", fontSize: isModal ? "12px" : "10px" },
                step: type === "line" || isModal ? 1 : undefined,
            },
            lineColor: "#e6eaf0",
            tickColor: "#e6eaf0",
        },
        yAxis: {
            min: 0,
            title: { text: isModal ? chart.yAxisTitle : null },
            gridLineColor: "#e6eaf0",
            labels: { style: { color: "#667085" } },
        },
        plotOptions: {
            series: {
                color: "#ff4d6d",
                borderRadius: 4,
                cursor: "pointer",
                point: {
                    events: {
                        click() {
                            openChartModal(chart);
                        },
                    },
                },
            },
            line: {
                marker: {
                    enabled: true,
                    radius: isModal ? 5 : 4,
                },
            },
        },
        series: [{ name: chart.seriesName, data }],
    };
}

function renderReportCharts() {
    const grid = document.getElementById("report-chart-grid");
    if (!grid) {
        return;
    }
    grid.replaceChildren();
    state.reportCharts.forEach((chart) => chart?.destroy());
    state.reportCharts = [];

    if (!window.Highcharts || state.insightCharts.length === 0) {
        const fallback = document.createElement("p");
        fallback.className = "empty-state";
        fallback.textContent = "차트 데이터를 불러오지 못했습니다. 네트워크 또는 데이터 파일을 확인해 주세요.";
        grid.appendChild(fallback);
        return;
    }

    state.insightCharts.forEach((chart) => {
        const card = document.createElement("article");
        const chartContainer = document.createElement("div");
        const title = document.createElement("h3");
        const description = document.createElement("p");

        card.className = "report-card chart-report-card";
        card.tabIndex = 0;
        card.setAttribute("role", "button");
        card.setAttribute("aria-label", `${chart.title} 확대 보기`);
        chartContainer.className = "report-chart";
        title.textContent = chart.title;
        description.textContent = chart.description;
        card.append(chartContainer, title, description);
        card.addEventListener("click", () => openChartModal(chart));
        card.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                openChartModal(chart);
            }
        });
        grid.appendChild(card);
        state.reportCharts.push(Highcharts.chart(chartContainer, buildChartOptions(chart)));
    });
}

function openChartModal(chart) {
    if (!window.Highcharts) {
        return;
    }
    const modal = document.getElementById("chart-modal");
    const title = document.getElementById("chart-modal-title");
    const description = document.getElementById("chart-modal-desc");
    const container = document.getElementById("chart-modal-container");
    title.textContent = chart.title;
    description.textContent = chart.description;
    modal.hidden = false;
    document.body.classList.add("modal-open");
    if (state.modalChart) {
        state.modalChart.destroy();
    }
    container.replaceChildren();
    state.modalChart = Highcharts.chart(container, buildChartOptions(chart, true));
}

function closeChartModal() {
    const modal = document.getElementById("chart-modal");
    modal.hidden = true;
    document.body.classList.remove("modal-open");
    if (state.modalChart) {
        state.modalChart.destroy();
        state.modalChart = null;
    }
}

function setupChartModal() {
    document.querySelectorAll("[data-close-chart-modal]").forEach((element) => {
        element.addEventListener("click", closeChartModal);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !document.getElementById("chart-modal").hidden) {
            closeChartModal();
        }
    });
}

function getCandidateId(item) {
    return [item.name, item.startDate, item.venue].join("|");
}

function normalizeTags(item) {
    const tags = [...(item.tags ?? [])];
    const day = new Date(item.startDate).getDay();
    if ((day === 0 || day === 6) && !tags.includes(WEEKEND_TAG)) {
        tags.push(WEEKEND_TAG);
    }
    const text = [item.name, item.venue, item.reason].join(" ");
    if ((text.includes("산책") || text.includes("광장") || text.includes("호수")) && !tags.includes("산책")) {
        tags.push("산책");
    }
    return tags;
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

function isFree(item) {
    return normalizeTags(item).includes("무료") || item.reason?.includes("무료");
}

function validCoordinate(item) {
    const latitude = Number(item.latitude);
    const longitude = Number(item.longitude);
    return Number.isFinite(latitude)
        && Number.isFinite(longitude)
        && latitude >= 37
        && latitude <= 38
        && longitude >= 126
        && longitude <= 128;
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

function appendTagsCell(row, item) {
    const cell = document.createElement("td");
    normalizeTags(item).slice(0, 5).forEach((tag) => {
        const tagElement = document.createElement("span");
        tagElement.className = "tag";
        tagElement.textContent = tag;
        cell.appendChild(tagElement);
    });
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
            state.statuses.set(id, "앱 등록 후보");
        } else {
            state.selectedIds.delete(id);
            state.statuses.set(id, "검토 전");
        }
        renderRecommendations();
    });
    cell.appendChild(checkbox);
    row.appendChild(cell);
}

function appendStatusCell(row, id) {
    const cell = document.createElement("td");
    const select = document.createElement("select");
    select.className = "status-select";
    STATUS_OPTIONS.forEach((status) => {
        const option = document.createElement("option");
        option.value = status;
        option.textContent = status;
        select.appendChild(option);
    });
    select.value = state.statuses.get(id) ?? "검토 전";
    select.addEventListener("change", () => {
        state.statuses.set(id, select.value);
        if (select.value === "앱 등록 후보" || select.value === "등록 완료") {
            state.selectedIds.add(id);
        }
        if (select.value === "검토 전" || select.value === "제외") {
            state.selectedIds.delete(id);
        }
        renderRecommendations();
    });
    cell.appendChild(select);
    row.appendChild(cell);
}

function getFilteredRecommendations() {
    const query = document.getElementById("candidate-search").value.trim().toLowerCase();
    const gu = document.getElementById("gu-filter").value;
    const category = document.getElementById("category-filter").value;
    const sort = document.getElementById("sort-select").value;

    const filtered = state.recommendations.filter((item) => {
        const tags = normalizeTags(item);
        const searchable = [item.name, item.gu, item.venue, item.category, item.reason, ...tags]
            .join(" ")
            .toLowerCase();
        return (!query || searchable.includes(query))
            && (!gu || item.gu === gu)
            && (!category || item.category === category)
            && (!state.quickTag || tags.includes(state.quickTag));
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

function renderRecommendations() {
    const data = getFilteredRecommendations();
    const visible = data.slice(0, DISPLAY_LIMIT);
    const body = document.getElementById("recommendation-body");
    body.replaceChildren();

    visible.forEach((item) => {
        const id = getCandidateId(item);
        const row = document.createElement("tr");
        row.className = id === state.activeId ? "is-active" : "";
        row.addEventListener("click", (event) => {
            if (event.target.closest("input") || event.target.closest("select")) {
                return;
            }
            state.activeId = id;
            focusMapMarker(id);
            renderRecommendations();
        });

        appendSelectCell(row, id);
        appendCell(row, item.name);
        appendCell(row, item.gu);
        appendCell(row, item.venue);
        appendCell(row, item.category);
        appendTagsCell(row, item);
        appendCell(row, item.score, "score");
        appendCell(row, item.reason);
        appendStatusCell(row, id);
        body.appendChild(row);
    });

    document.getElementById("candidate-count").textContent = `추천 후보 ${data.length}개 중 ${visible.length}개 표시`;
    document.getElementById("selected-count").textContent = `앱 등록 후보 ${state.selectedIds.size}개`;
    renderRecommendationMap(data);
}

function renderEvents() {
    const gu = document.getElementById("event-gu-filter").value;
    const category = document.getElementById("event-category-filter").value;
    const free = document.getElementById("event-free-filter").value;
    const body = document.getElementById("event-body");
    body.replaceChildren();

    state.recommendations
        .filter((item) => (!gu || item.gu === gu)
            && (!category || item.category === category)
            && (!free || (free === "무료" ? isFree(item) : !isFree(item))))
        .slice(0, EVENT_LIMIT)
        .forEach((item) => {
            const row = document.createElement("tr");
            appendCell(row, item.name);
            appendCell(row, item.gu);
            appendCell(row, item.venue);
            appendCell(row, item.category);
            appendCell(row, item.startDate);
            appendCell(row, item.endDate);
            appendCell(row, isFree(item) ? "무료" : "유료");
            appendCell(row, item.time ?? "-");
            body.appendChild(row);
        });
}

function initMap() {
    const container = document.getElementById("recommendation-map");
    if (!container || !window.L || state.map) {
        return;
    }
    container.replaceChildren();
    state.map = L.map(container, { scrollWheelZoom: false }).setView([37.5665, 126.9780], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(state.map);
    state.markerLayer = L.layerGroup().addTo(state.map);
}

function markerPopup(item) {
    const tags = normalizeTags(item).slice(0, 5).join(", ");
    return `
        <strong>${item.name}</strong>
        <div>${item.gu} · ${item.venue}</div>
        <div>${item.category} · ${item.score}점</div>
        <div>${tags}</div>
        <p>${item.reason}</p>
    `;
}

function renderRecommendationMap(data) {
    initMap();
    if (!state.map || !state.markerLayer) {
        return;
    }
    state.markerLayer.clearLayers();
    state.markers.clear();

    const mapItems = data.filter(validCoordinate).slice(0, MAP_LIMIT);
    mapItems.forEach((item) => {
        const id = getCandidateId(item);
        const marker = L.marker([Number(item.latitude), Number(item.longitude)])
            .bindPopup(markerPopup(item));
        marker.addTo(state.markerLayer);
        state.markers.set(id, marker);
    });

    if (mapItems.length > 0) {
        const bounds = L.latLngBounds(mapItems.map((item) => [Number(item.latitude), Number(item.longitude)]));
        state.map.fitBounds(bounds, { padding: [24, 24], maxZoom: 13 });
    } else {
        state.map.setView([37.5665, 126.9780], 11);
    }
    setTimeout(() => state.map.invalidateSize(), 50);
}

function focusMapMarker(id) {
    const marker = state.markers.get(id);
    if (!marker || !state.map) {
        return;
    }
    state.map.setView(marker.getLatLng(), 14);
    marker.openPopup();
}

function populateSelect(id, values) {
    const select = document.getElementById(id);
    if (!select) {
        return;
    }
    values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    });
}

function setupFilters() {
    const unique = (values) => [...new Set(values.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), "ko"));
    const options = window.DECO_FILTER_OPTIONS ?? {};
    const guValues = options.gu?.length ? options.gu : unique(state.recommendations.map((item) => item.gu));
    const categoryValues = options.category?.length ? options.category : unique(state.recommendations.map((item) => item.category));
    populateSelect("gu-filter", guValues);
    populateSelect("event-gu-filter", guValues);
    populateSelect("category-filter", categoryValues);
    populateSelect("event-category-filter", categoryValues);

    ["candidate-search", "gu-filter", "category-filter", "sort-select"].forEach((id) => {
        document.getElementById(id).addEventListener("input", renderRecommendations);
    });
    ["event-gu-filter", "event-category-filter", "event-free-filter"].forEach((id) => {
        document.getElementById(id).addEventListener("input", renderEvents);
    });
    document.querySelectorAll(".tag-filter").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".tag-filter").forEach((item) => item.classList.remove("is-active"));
            button.classList.add("is-active");
            state.quickTag = button.dataset.tag;
            renderRecommendations();
        });
    });
}

function renderTags() {
    const tags = ["무료", "전시", "공연", "체험", "실내", "야외", "주말", "가성비", "산책", "야간"];
    const grid = document.getElementById("tag-management-grid");
    grid.replaceChildren();
    tags.forEach((tag) => {
        const count = state.recommendations.filter((item) => normalizeTags(item).includes(tag)).length;
        const card = document.createElement("article");
        card.className = "tag-card";
        const title = document.createElement("strong");
        const description = document.createElement("p");
        title.textContent = tag;
        description.textContent = `${count.toLocaleString()}개 추천 후보에 연결됨`;
        card.append(title, description);
        grid.appendChild(card);
    });
}

function renderDashboardInsights() {
    const insights = [
        ["지역 집중", "종로구와 중구는 초기 추천 코스의 핵심 문화 거점입니다."],
        ["테마 공급", "교육/체험, 전시/미술, 클래식은 데이트 테마로 전환하기 쉽습니다."],
        ["주말 타이밍", "금요일과 토요일 시작 행사를 중심으로 주말 추천을 구성합니다."],
        ["지도 연동", "좌표가 있는 후보는 앱 지도 핀과 이동 동선 설계에 활용할 수 있습니다."],
    ];
    const list = document.getElementById("dashboard-insights");
    list.replaceChildren();
    insights.forEach(([title, text]) => {
        const item = document.createElement("article");
        item.className = "summary-item";
        const strong = document.createElement("strong");
        const paragraph = document.createElement("p");
        strong.textContent = title;
        paragraph.textContent = text;
        item.append(strong, paragraph);
        list.appendChild(item);
    });
}

function setupTabs() {
    const buttons = document.querySelectorAll(".nav-item");
    const panels = document.querySelectorAll(".tab-panel");
    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            const tab = button.dataset.tab;
            buttons.forEach((item) => item.classList.toggle("is-active", item === button));
            panels.forEach((panel) => panel.classList.toggle("is-active", panel.id === `tab-${tab}`));
            const activePanel = document.getElementById(`tab-${tab}`);
            document.getElementById("page-title").textContent = activePanel.dataset.title;
            if (tab === "recommendations") {
                setTimeout(() => {
                    initMap();
                    renderRecommendationMap(getFilteredRecommendations());
                }, 80);
            }
            if (tab === "reports") {
                setTimeout(() => {
                    renderReportCharts();
                }, 80);
            }
        });
    });
}

function init() {
    state.recommendations = window.DECO_RECOMMENDATIONS?.length
        ? window.DECO_RECOMMENDATIONS
        : fallbackData;
    state.insightCharts = window.DECO_INSIGHT_CHARTS ?? [];
    document.getElementById("data-status").textContent = `추천 후보 ${state.recommendations.length.toLocaleString()}건 로드`;
    setupChartModal();
    setupTabs();
    setupFilters();
    renderDashboardInsights();
    renderEvents();
    renderTags();
    renderRecommendations();
    renderReportCharts();
}

document.addEventListener("DOMContentLoaded", init);
