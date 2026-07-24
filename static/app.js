/* =========================================================================
   Trading Signal Scanner — Frontend Logic
   ========================================================================= */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentResults = [];
let watchlist = [];

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    loadWatchlist();
});

// ---------------------------------------------------------------------------
// Watchlist
// ---------------------------------------------------------------------------

async function loadWatchlist() {
    try {
        const res = await fetch("/api/watchlist");
        const data = await res.json();
        watchlist = data.watchlist || [];
        renderWatchlistChips();
    } catch (err) {
        console.error("Failed to load watchlist:", err);
    }
}

function renderWatchlistChips() {
    const container = document.getElementById("watchlistChips");
    container.innerHTML = watchlist
        .map(
            (ticker) => `
        <span class="chip">
            ${ticker}
            <button class="chip-remove" onclick="removeTicker('${ticker}')" title="Remove ${ticker}">&times;</button>
        </span>
    `
        )
        .join("");
}

async function addTicker() {
    const input = document.getElementById("addTickerInput");
    const ticker = input.value.trim().toUpperCase();

    if (!ticker) return;
    if (watchlist.includes(ticker)) {
        input.value = "";
        return;
    }

    try {
        const res = await fetch("/api/watchlist", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ticker }),
        });

        if (res.ok) {
            const data = await res.json();
            watchlist = data.watchlist;
            renderWatchlistChips();
            input.value = "";
        } else {
            const err = await res.json();
            console.warn("Add ticker failed:", err.error);
        }
    } catch (err) {
        console.error("Add ticker error:", err);
    }
}

async function removeTicker(ticker) {
    try {
        const res = await fetch(`/api/watchlist/${ticker}`, {
            method: "DELETE",
        });

        if (res.ok) {
            const data = await res.json();
            watchlist = data.watchlist;
            renderWatchlistChips();
        }
    } catch (err) {
        console.error("Remove ticker error:", err);
    }
}

// ---------------------------------------------------------------------------
// Scanning
// ---------------------------------------------------------------------------

async function runScan() {
    const btn = document.getElementById("scanBtn");
    const overlay = document.getElementById("loadingOverlay");
    const loadingText = document.getElementById("loadingText");

    // Show loading
    btn.disabled = true;
    overlay.classList.add("active");
    loadingText.textContent = `Scanning ${watchlist.length} tickers...`;

    try {
        const res = await fetch("/api/scan");
        const data = await res.json();

        currentResults = data.results || [];
        renderSignalTable(currentResults);
        renderSummaryCards(currentResults);

        // Update timestamp
        const tsEl = document.getElementById("scanTimestamp");
        tsEl.textContent = `Last scan: ${data.timestamp}`;
    } catch (err) {
        console.error("Scan failed:", err);
        alert("Scan failed. Check console for details.");
    } finally {
        btn.disabled = false;
        overlay.classList.remove("active");
    }
}

// ---------------------------------------------------------------------------
// Signal Table Rendering
// ---------------------------------------------------------------------------

function renderSignalTable(results) {
    const tbody = document.getElementById("signalTableBody");

    if (!results.length) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="10">No results. Click <strong>Scan Now</strong> to fetch signals.</td>
            </tr>`;
        return;
    }

    tbody.innerHTML = results.map((r) => {
        const priceStr = r.price != null ? `$${r.price.toFixed(2)}` : "N/A";
        const changeStr = r.change_pct != null ? `${r.change_pct >= 0 ? "+" : ""}${r.change_pct.toFixed(1)}%` : "N/A";
        const changeClass = r.change_pct > 0 ? "change-positive" : r.change_pct < 0 ? "change-negative" : "change-neutral";

        const signalClass = r.signal === "BUY" ? "signal-buy" : r.signal === "SELL" ? "signal-sell" : "signal-hold";

        return `
            <tr onclick="openTickerDetail('${r.ticker}')">
                <td class="ticker-cell">${r.ticker}</td>
                <td class="price-cell">${priceStr}</td>
                <td class="${changeClass}">${changeStr}</td>
                <td class="${r.bullish > r.bearish ? 'score-positive' : 'score-neutral'}">${r.bullish}</td>
                <td class="${r.bearish > r.bullish ? 'score-negative' : 'score-neutral'}">${r.bearish}</td>
                <td class="score-cell ${scoreColorClass(r.finnhub_score)}">${formatScore(r.finnhub_score)}</td>
                <td class="score-cell ${scoreColorClass(r.yahoo_score)}">${formatScore(r.yahoo_score)}</td>
                <td class="score-cell ${scoreColorClass(r.combined_score)}">${formatScore(r.combined_score)}</td>
                <td class="score-neutral">${r.total_articles}</td>
                <td><span class="signal-badge ${signalClass}"><span class="signal-dot"></span>${r.signal}</span></td>
            </tr>`;
    }).join("");
}

function formatScore(score) {
    if (score == null) return "N/A";
    return (score >= 0 ? "+" : "") + score.toFixed(3);
}

function scoreColorClass(score) {
    if (score > 0.05) return "score-positive";
    if (score < -0.05) return "score-negative";
    return "score-neutral";
}

// ---------------------------------------------------------------------------
// Summary Cards
// ---------------------------------------------------------------------------

function renderSummaryCards(results) {
    const container = document.getElementById("summaryCards");
    container.style.display = "grid";

    const buys = results.filter((r) => r.signal === "BUY").length;
    const sells = results.filter((r) => r.signal === "SELL").length;
    const holds = results.filter((r) => r.signal === "HOLD").length;

    document.getElementById("buyCount").textContent = buys;
    document.getElementById("sellCount").textContent = sells;
    document.getElementById("holdCount").textContent = holds;

    document.getElementById("tableCount").textContent = `${results.length} tickers scanned`;
}

// ---------------------------------------------------------------------------
// Ticker Detail Modal
// ---------------------------------------------------------------------------

async function openTickerDetail(ticker) {
    const overlay = document.getElementById("modalOverlay");
    const modal = document.getElementById("detailModal");

    // Set header
    document.getElementById("modalTicker").textContent = ticker;

    // Show modal with loading state
    const statsEl = document.getElementById("modalStats");
    const finnhubList = document.getElementById("finnhubNewsList");
    const yahooList = document.getElementById("yahooNewsList");

    statsEl.innerHTML = '<div class="news-loading">Loading...</div>';
    finnhubList.innerHTML = '<div class="news-loading">Loading articles...</div>';
    yahooList.innerHTML = '<div class="news-loading">Loading articles...</div>';
    document.getElementById("modalSignal").innerHTML = "";

    overlay.classList.add("active");

    try {
        const res = await fetch(`/api/ticker/${ticker}`);
        const data = await res.json();

        const signal = data.signal || {};
        const signalClass = signal.signal === "BUY" ? "signal-buy" : signal.signal === "SELL" ? "signal-sell" : "signal-hold";

        // Signal badge
        document.getElementById("modalSignal").innerHTML =
            `<span class="signal-badge ${signalClass}"><span class="signal-dot"></span>${signal.signal || "N/A"}</span>`;

        // Stats
        const priceStr = signal.price != null ? `$${signal.price.toFixed(2)}` : "N/A";
        const changeStr = signal.change_pct != null ? `${signal.change_pct >= 0 ? "+" : ""}${signal.change_pct.toFixed(1)}%` : "N/A";

        statsEl.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${priceStr}</div>
                <div class="stat-label">Price</div>
            </div>
            <div class="stat-card">
                <div class="stat-value ${signal.change_pct >= 0 ? 'score-positive' : 'score-negative'}">${changeStr}</div>
                <div class="stat-label">Change</div>
            </div>
            <div class="stat-card">
                <div class="stat-value ${scoreColorClass(signal.combined_score)}">${formatScore(signal.combined_score)}</div>
                <div class="stat-label">Combined</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${signal.total_articles || 0}</div>
                <div class="stat-label">Articles</div>
            </div>
        `;

        // News lists
        finnhubList.innerHTML = renderNewsList(data.finnhub_articles || []);
        yahooList.innerHTML = renderNewsList(data.yahoo_articles || []);

    } catch (err) {
        console.error("Ticker detail error:", err);
        statsEl.innerHTML = '<div class="news-loading">Failed to load data.</div>';
    }
}

function renderNewsList(articles) {
    if (!articles.length) {
        return '<div class="news-loading">No articles found.</div>';
    }

    return articles
        .map((a) => {
            const scoreClass = a.score > 0.05 ? "news-score-positive" : a.score < -0.05 ? "news-score-negative" : "news-score-neutral";
            const headline = a.headline || "Untitled";
            const source = a.source || "";
            const dateStr = a.datetime ? formatDate(a.datetime) : "";
            const url = a.url || "#";

            return `
            <div class="news-item">
                <span class="news-score ${scoreClass}">${formatScore(a.score)}</span>
                <div class="news-content">
                    <div class="news-headline"><a href="${url}" target="_blank" rel="noopener">${escapeHtml(headline)}</a></div>
                    <div class="news-meta">${escapeHtml(source)}${dateStr ? " &middot; " + dateStr : ""}</div>
                </div>
            </div>`;
        })
        .join("");
}

function formatDate(dateStr) {
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return "";
        const now = new Date();
        const diffMs = now - d;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

        if (diffHours < 1) return "Just now";
        if (diffHours < 24) return `${diffHours}h ago`;

        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `${diffDays}d ago`;

        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    } catch {
        return "";
    }
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function closeModal(event) {
    // If called from overlay click, only close if clicking the overlay itself
    if (event && event.target !== document.getElementById("modalOverlay")) return;

    document.getElementById("modalOverlay").classList.remove("active");
}

// Close modal on Escape key
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        document.getElementById("modalOverlay").classList.remove("active");
    }
});
