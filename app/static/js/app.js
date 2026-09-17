document.addEventListener("DOMContentLoaded", () => {
    // Global chart instances
    let cashFlowChartInstance = null;
    let categoryChartInstance = null;

    // Toast Notifications
    function showToast(message, type = "success") {
        const container = document.getElementById("toast-container");
        if (!container) return;
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    }

    // Tab Navigation
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");
            tabBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(targetId).classList.add("active");

            if (targetId === "tab-analytics") {
                loadAnalytics();
            } else if (targetId === "tab-ledger") {
                loadLedger();
            }
        });
    });

    // Initial Data Load
    loadAnalytics();
    loadLedger();

    // 1. Fetch & Render Analytics
    async function loadAnalytics() {
        try {
            const res = await fetch("/api/analytics");
            if (!res.ok) return;
            const data = await res.json();

            // Update KPI Cards
            document.getElementById("kpi-cash-flow").textContent = `KES ${data.net_cash_flow.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
            const cashFlowBadge = document.getElementById("kpi-cash-flow-badge");
            cashFlowBadge.textContent = data.financial_health_signals.cash_flow_status;
            cashFlowBadge.className = data.net_cash_flow >= 0 ? "badge badge-success" : "badge badge-danger";

            document.getElementById("kpi-balance-subtext").textContent = `Est. Balance: KES ${data.current_balance.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
            document.getElementById("kpi-total-income").textContent = `KES ${data.total_income.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
            document.getElementById("kpi-income-txns").textContent = `${data.transaction_count} Total Transactions`;
            document.getElementById("kpi-total-expenses").textContent = `KES ${data.total_expenses.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
            document.getElementById("kpi-surplus-rate").textContent = `Surplus Rate: ${data.surplus_rate}%`;

            const healthRating = document.getElementById("kpi-health-rating");
            healthRating.textContent = data.financial_health_signals.health_rating;
            healthRating.className = data.net_cash_flow >= 0 ? "kpi-value text-success" : "kpi-value text-danger";

            const fulizaBadge = document.getElementById("kpi-fuliza-badge");
            if (data.financial_health_signals.fuliza_debt_alert) {
                fulizaBadge.textContent = "⚠️ Active Fuliza Overdraft";
                fulizaBadge.className = "badge badge-danger";
            } else {
                fulizaBadge.textContent = "✅ No Overdraft Debt";
                fulizaBadge.className = "badge badge-warning";
            }

            document.getElementById("ledger-count-badge").textContent = data.transaction_count;

            // Render Charts
            renderCashFlowChart(data.daily_trends || []);
            renderCategoryChart(data.top_spending_categories || {});

            // Render Leaderboards
            renderLeaderList("top-merchants-list", data.top_spending_entities, "expense");
            renderLeaderList("top-senders-list", data.top_income_sources, "income");
            renderDomainList("domain-breakdown-list", data.domain_breakdown || {});

        } catch (err) {
            console.error("Failed to load analytics:", err);
        }
    }

    // Render Cash Flow Trend Line Chart
    function renderCashFlowChart(trends) {
        const ctx = document.getElementById("cashFlowChart");
        if (!ctx) return;

        const labels = trends.map(t => t.date);
        const incomeData = trends.map(t => t.income);
        const expenseData = trends.map(t => t.expense);

        if (cashFlowChartInstance) {
            cashFlowChartInstance.destroy();
        }

        cashFlowChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels.length ? labels : ["No Data"],
                datasets: [
                    {
                        label: "Income (KES)",
                        data: incomeData.length ? incomeData : [0],
                        borderColor: "#10b981",
                        backgroundColor: "rgba(16, 185, 129, 0.1)",
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: "Expense (KES)",
                        data: expenseData.length ? expenseData : [0],
                        borderColor: "#ef4444",
                        backgroundColor: "rgba(239, 68, 68, 0.1)",
                        fill: true,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: "#9ca3af" } }
                },
                scales: {
                    x: { ticks: { color: "#6b7280" }, grid: { color: "#1e293b" } },
                    y: { ticks: { color: "#6b7280" }, grid: { color: "#1e293b" } }
                }
            }
        });
    }

    // Render Category Distribution Donut Chart
    function renderCategoryChart(categories) {
        const ctx = document.getElementById("categoryChart");
        if (!ctx) return;

        const labels = Object.keys(categories).map(c => c.charAt(0).toUpperCase() + c.slice(1));
        const values = Object.values(categories);

        if (categoryChartInstance) {
            categoryChartInstance.destroy();
        }

        categoryChartInstance = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: labels.length ? labels : ["No Data"],
                datasets: [{
                    data: values.length ? values : [1],
                    backgroundColor: [
                        "#818cf8", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#38bdf8", "#f472b6"
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { color: "#9ca3af", font: { size: 11 } } }
                }
            }
        });
    }

    function renderLeaderList(elementId, items, type) {
        const el = document.getElementById(elementId);
        if (!el) return;
        el.innerHTML = "";

        const keys = Object.keys(items);
        if (keys.length === 0) {
            el.innerHTML = '<li class="empty-state">No transaction records logged.</li>';
            return;
        }

        keys.forEach(key => {
            const li = document.createElement("li");
            li.className = "leader-item";
            const colorClass = type === "income" ? "text-success" : "text-danger";
            li.innerHTML = `
                <span class="leader-name">${key}</span>
                <span class="leader-val ${colorClass}">KES ${items[key].toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            `;
            el.appendChild(li);
        });
    }

    function renderDomainList(elementId, domains) {
        const el = document.getElementById(elementId);
        if (!el) return;
        el.innerHTML = "";

        const keys = Object.keys(domains);
        if (keys.length === 0) {
            el.innerHTML = '<li class="empty-state">No transaction records logged.</li>';
            return;
        }

        keys.forEach(dom => {
            const li = document.createElement("li");
            li.className = "leader-item";
            li.innerHTML = `
                <span class="leader-name">${dom.toUpperCase()}</span>
                <span class="leader-val text-muted">${domains[dom].count} txns (KES ${domains[dom].total_amount.toLocaleString(undefined, {minimumFractionDigits: 2})})</span>
            `;
            el.appendChild(li);
        });
    }

    // 2. Load Financial Ledger Table
    async function loadLedger() {
        const tbody = document.getElementById("ledger-table-body");
        if (!tbody) return;

        const q = document.getElementById("search-ledger")?.value || "";
        const domain = document.getElementById("filter-domain")?.value || "";
        const category = document.getElementById("filter-category")?.value || "";

        let url = `/api/transactions?q=${encodeURIComponent(q)}&domain=${encodeURIComponent(domain)}&category=${encodeURIComponent(category)}`;

        try {
            const res = await fetch(url);
            if (!res.ok) return;
            const data = await res.json();

            tbody.innerHTML = "";
            if (data.count === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted" style="padding: 24px;">No matching transactions in ledger.</td></tr>';
                return;
            }

            data.items.forEach(t => {
                const tr = document.createElement("tr");
                const typeColor = t.transaction_type === "income" ? "text-success" : "text-danger";
                const typeSign = t.transaction_type === "income" ? "+" : "-";

                tr.innerHTML = `
                    <td><strong>${t.reference}</strong></td>
                    <td>${t.date || ""} <span class="text-muted">${t.time || ""}</span></td>
                    <td><span class="badge badge-subtle">${t.domain.toUpperCase()}</span></td>
                    <td>${t.category.toUpperCase()}</td>
                    <td>${t.entity}</td>
                    <td><span class="badge ${t.transaction_type === 'income' ? 'badge-success' : 'badge-danger'}">${t.transaction_type}</span></td>
                    <td class="${typeColor} font-weight-bold">${typeSign} KES ${t.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td>KES ${t.balance.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td>
                        <button class="btn-del" data-id="${t.id}" title="Delete transaction">🗑️</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Bind Delete Buttons
            document.querySelectorAll(".btn-del").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const id = btn.getAttribute("data-id");
                    if (confirm("Delete this transaction from ledger?")) {
                        await fetch(`/api/transactions/${id}`, { method: "DELETE" });
                        showToast("Transaction deleted");
                        loadLedger();
                        loadAnalytics();
                    }
                });
            });

        } catch (err) {
            console.error("Failed to load ledger:", err);
        }
    }

    // Event Listeners for Filters
    document.getElementById("search-ledger")?.addEventListener("input", loadLedger);
    document.getElementById("filter-domain")?.addEventListener("change", loadLedger);
    document.getElementById("filter-category")?.addEventListener("change", loadLedger);

    // 3. Extract SMS Handlers
    const smsInput = document.getElementById("sms-input");
    const resultJson = document.getElementById("result-json");
    const statusBadge = document.getElementById("extraction-status-badge");

    async function handleExtract(autoSave = false) {
        const sms = smsInput.value.trim();
        if (!sms) {
            showToast("Please enter or paste an SMS text", "error");
            return;
        }

        resultJson.textContent = "Processing extraction...";
        statusBadge.textContent = "Extracting...";
        statusBadge.className = "badge badge-warning";

        try {
            const res = await fetch("/api/extract", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ sms, auto_save: autoSave })
            });

            const data = await res.json();
            resultJson.textContent = JSON.stringify(data, null, 2);

            if (data.is_valid) {
                statusBadge.textContent = data.saved ? "Extracted & Saved" : "Valid Schema";
                statusBadge.className = "badge badge-success";
                showToast(data.saved ? "Extracted and added to ledger!" : "Extraction complete!");
                if (data.saved) {
                    loadLedger();
                    loadAnalytics();
                }
            } else {
                statusBadge.textContent = "Invalid Schema";
                statusBadge.className = "badge badge-danger";
            }

        } catch (err) {
            resultJson.textContent = `Error: ${err.message}`;
            statusBadge.textContent = "Failed";
            statusBadge.className = "badge badge-danger";
        }
    }

    document.getElementById("extract-btn")?.addEventListener("click", () => handleExtract(false));
    document.getElementById("extract-and-save-btn")?.addEventListener("click", () => handleExtract(true));

    // Preset Chip Click Handlers
    document.querySelectorAll(".preset-chips .chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const smsText = chip.getAttribute("data-sms");
            if (smsText) {
                smsInput.value = smsText;
                handleExtract(false);
            }
        });
    });

    // 4. Seed Demo Data Button
    document.getElementById("btn-seed-sample")?.addEventListener("click", async () => {
        showToast("Seeding realistic sample transactions...");
        try {
            const res = await fetch("/api/sample-data", { method: "POST" });
            const data = await res.json();
            showToast(data.message);
            loadAnalytics();
            loadLedger();
        } catch (err) {
            showToast("Failed to seed sample data", "error");
        }
    });

    // 5. Reset Ledger Button
    document.getElementById("btn-reset-ledger")?.addEventListener("click", async () => {
        if (confirm("Are you sure you want to clear all ledger transactions?")) {
            await fetch("/api/transactions/reset", { method: "DELETE" });
            showToast("Ledger cleared");
            loadAnalytics();
            loadLedger();
        }
    });

    // 6. Local AI Advisor Chat Interface
    const advisorInput = document.getElementById("advisor-input");
    const advisorSendBtn = document.getElementById("advisor-send-btn");
    const chatMessages = document.getElementById("chat-messages");

    async function sendAdvisorQuery(queryText) {
        const q = queryText || advisorInput.value.trim();
        if (!q) return;

        // Append User Message
        const userBubble = document.createElement("div");
        userBubble.className = "chat-bubble user";
        userBubble.textContent = q;
        chatMessages.appendChild(userBubble);

        advisorInput.value = "";
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Thinking Indicator
        const assistantBubble = document.createElement("div");
        assistantBubble.className = "chat-bubble assistant";
        assistantBubble.innerHTML = '<div class="bubble-header">🤖 SME Financial Advisor</div><div class="bubble-content">Analyzing ledger and Pandas financial profile...</div>';
        chatMessages.appendChild(assistantBubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const res = await fetch("/api/insights", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: q })
            });

            const data = await res.json();
            // Format markdown text roughly
            let formattedText = data.insight
                .replace(/\n\n/g, "<br><br>")
                .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                .replace(/\n- /g, "<br>• ");

            assistantBubble.querySelector(".bubble-content").innerHTML = formattedText;
            chatMessages.scrollTop = chatMessages.scrollHeight;

        } catch (err) {
            assistantBubble.querySelector(".bubble-content").textContent = "Sorry, failed to generate financial insight.";
        }
    }

    advisorSendBtn?.addEventListener("click", () => sendAdvisorQuery());
    advisorInput?.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendAdvisorQuery();
    });

    document.querySelectorAll(".query-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const text = chip.getAttribute("data-query");
            if (text) sendAdvisorQuery(text);
        });
    });
});
