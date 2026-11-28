/**
 * ReviewShield Side Panel Controller.
 * Quản lý tự động cuộn & gom cân bằng đánh giá, xuất JSON ẩn danh PII và gọi Backend `/api/analyze`.
 */

const DEFAULT_BACKEND_URL = "https://hackathonane.duckdns.org";
const STORAGE_KEY_BACKEND = "rs_backend_url";

const LABEL_META = {
  verified_insight: { name: "Trải nghiệm thật", pill: "pill-mint", color: "#2ED8A3", weight: "w=1.00" },
  low_signal: { name: "Nhận xu / Chung chung", pill: "pill-amber", color: "#F5B942", weight: "w=0.15" },
  suspicious_pattern: { name: "Nghi vấn lặp mẫu", pill: "pill-coral", color: "#FF6B4A", weight: "w=0.10" },
  logistics_only: { name: "Chỉ nói vận chuyển", pill: "pill-blue", color: "#52A5FF", weight: "w=0.00" },
};

const TRUST_META = {
  high: { text: "Độ tin cậy cao", pill: "pill-mint" },
  medium: { text: "Cần đọc kỹ thêm", pill: "pill-amber" },
  low: { text: "Rủi ro lệch điểm", pill: "pill-red" },
  insufficient_data: { text: "Chưa đủ dữ liệu", pill: "pill-blue" },
};

const state = {
  mode: "scan", // "scan" | "manual"
  backendUrl: DEFAULT_BACKEND_URL,
  platform: "Shopee",
  category: "phu_kien_dien_tu",
  lastPageKey: "",
  reviews: [],
  lastResult: null,
  activeFilter: "all",
  isScanning: false,
  scanningTabId: null,
};

const $ = (id) => document.getElementById(id);

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeUrl(url) {
  return String(url || DEFAULT_BACKEND_URL).trim().replace(/\/+$/, "");
}

function getPageKey(urlStr) {
  try {
    const u = new URL(urlStr);
    return `${u.origin}${u.pathname}`;
  } catch (_) {
    return "";
  }
}

function showNotice(msg, isError = false) {
  const box = $("scanNotice");
  box.textContent = msg;
  box.style.borderLeftColor = isError ? "#FF5C77" : "#2ED8A3";
  box.classList.remove("hidden");
}

function showError(msg) {
  const box = $("errorBox");
  if (!msg) {
    box.classList.add("hidden");
    box.textContent = "";
    return;
  }
  box.textContent = msg;
  box.classList.remove("hidden");
}

function buildProductPayload() {
  const productName = $("inputProductName").value.trim() || "Sản phẩm từ ReviewShield Extension";
  const rawRating = parseFloat($("inputPlatformRating").value);
  const platformRating =
    !Number.isNaN(rawRating) && rawRating >= 1.0 && rawRating <= 5.0
      ? Number(rawRating.toFixed(1))
      : null;

  return {
    product_id: "ext_live",
    product_name: productName,
    category: state.category || "phu_kien_dien_tu",
    platform: state.platform || "Shopee",
    platform_rating: platformRating,
    reviews: state.reviews.map((r, i) => ({
      id: `r${i + 1}`,
      author: `user_${String(i + 1).padStart(2, "0")}`,
      rating: r.rating,
      text: r.text,
    })),
  };
}

function renderCollectedState() {
  const count = state.reviews.length;
  $("collectedCount").textContent = `${count} review`;

  if (count > 0) {
    const c5 = state.reviews.filter((r) => r.rating === 5).length;
    const c4 = state.reviews.filter((r) => r.rating === 4).length;
    const c13 = state.reviews.filter((r) => r.rating <= 3).length;
    $("starSummary").textContent = `Phân bổ đã gom (${state.platform}): 5★: ${c5} · 4★: ${c4} · 1–3★: ${c13}`;
    $("starSummary").classList.remove("hidden");
  } else {
    $("starSummary").classList.add("hidden");
  }

  $("jsonPreview").textContent = JSON.stringify(buildProductPayload(), null, 2);
}

function setMode(mode) {
  state.mode = mode;
  $("tabScan").classList.toggle("active", mode === "scan");
  $("tabManual").classList.toggle("active", mode === "manual");
  $("panelScan").classList.toggle("hidden", mode !== "scan");
  $("panelManual").classList.toggle("hidden", mode !== "manual");
  showError("");
}

async function checkHealth() {
  const badge = $("healthBadge");
  badge.className = "status-pill status-btn";
  badge.textContent = "Đang kết nối…";
  try {
    const resp = await fetch(`${state.backendUrl}/api/health`, { method: "GET" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    badge.className = "status-pill status-btn ok";
    badge.textContent = `${data.model || "API OK"} · ${data.cache_backend || "cache"}`;
  } catch (_) {
    badge.className = "status-pill status-btn err";
    badge.textContent = "Mất kết nối API";
  }
}

async function stopActiveScan() {
  if (!state.isScanning || !state.scanningTabId) return;
  $("btnStopScan").disabled = true;
  $("btnStopScan").textContent = "Đang dừng…";
  try {
    await chrome.scripting.executeScript({
      target: { tabId: state.scanningTabId },
      func: () => {
        window.__RS_ABORT_SCAN__ = true;
      },
    });
  } catch (_) {
    // ignore
  }
}

async function scanActiveTab(scanMode = "auto") {
  if (state.isScanning) return;
  showError("");

  const btnAuto = $("btnScanPage");
  const btnVisible = $("btnScanVisible");
  const btnStop = $("btnStopScan");
  const btnClear = $("btnClearList");

  const targetCount = Math.min(200, Math.max(10, parseInt($("selectTargetCount").value, 10) || 20));
  const balanceStars = $("chkBalanceStars").checked;

  state.isScanning = true;
  btnAuto.disabled = true;
  btnVisible.disabled = true;
  btnClear.disabled = true;
  btnAuto.textContent = scanMode === "auto" ? "Đang tự cuộn & quét…" : "Đang quét nhanh…";
  if (scanMode === "auto") {
    btnStop.classList.remove("hidden");
    btnStop.disabled = false;
    btnStop.textContent = "Dừng";
  }

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      throw new Error("Không tìm thấy tab đang mở.");
    }
    if (tab.url && !/^https?:\/\//i.test(tab.url)) {
      throw new Error(
        "Trang hiện tại là trang hệ thống trình duyệt. Hãy chuyển sang tab Shopee, Tiki hoặc Điện Máy Xanh rồi bấm Quét."
      );
    }

    // Tự động làm mới danh sách nếu người dùng đã chuyển sang sản phẩm khác
    const pageKey = tab.url ? getPageKey(tab.url) : "";
    if (pageKey && state.lastPageKey && pageKey !== state.lastPageKey) {
      state.reviews = [];
      $("inputProductName").value = "";
      $("inputPlatformRating").value = "";
    }
    if (pageKey) state.lastPageKey = pageKey;

    // Xin quyền host 1 chạm nếu trang hiện tại chưa có trong host_permissions
    if (tab.url && chrome.permissions) {
      try {
        const originPattern = `${new URL(tab.url).origin}/*`;
        const hasPerm = await chrome.permissions.contains({ origins: [originPattern] });
        if (!hasPerm) {
          const granted = await chrome.permissions.request({ origins: [originPattern] });
          if (!granted) {
            throw new Error("Bạn chưa cấp quyền đọc trang web này. Hãy bấm 'Cho phép' khi trình duyệt hỏi.");
          }
        }
      } catch (permErr) {
        if (permErr && permErr.message && permErr.message.includes("chưa cấp quyền")) {
          throw permErr;
        }
      }
    }

    state.scanningTabId = tab.id;
    showNotice(
      scanMode === "auto"
        ? `Đang tự cuộn xuống mục Đánh giá & gom tối đa ${targetCount} review (không cần vuốt tay)…`
        : "Đang quét các đánh giá đang hiển thị trên màn hình…"
    );

    const scanConfig = {
      mode: scanMode,
      targetCount,
      balanceStars,
      restoreScroll: true,
    };

    let injected;
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (cfg) => {
          window.__RS_SCAN_CONFIG__ = cfg;
          window.__RS_ABORT_SCAN__ = false;
        },
        args: [scanConfig],
      });
      injected = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["content.js"],
      });
    } catch (execErr) {
      throw new Error(
        `Chưa có quyền đọc trang này (${execErr.message || execErr}). Hãy vào chrome://extensions → bấm Tải lại (↻) ReviewShield → thử Quét lại.`
      );
    }

    const res = injected && injected[0] ? injected[0].result : null;
    if (!res) {
      throw new Error("Không đọc được nội dung trang. Hãy tải lại trang hoặc dùng chế độ Dán thủ công.");
    }

    if (res.product_name && !$("inputProductName").value.trim()) {
      $("inputProductName").value = res.product_name;
    }
    if (typeof res.platform_rating === "number" && !$("inputPlatformRating").value) {
      $("inputPlatformRating").value = String(res.platform_rating);
    }
    if (res.platform) state.platform = res.platform;
    if (res.category) state.category = res.category;

    if (!res.reviews || !res.reviews.length) {
      showNotice(res.note || "Chưa tìm thấy đánh giá trên trang.", true);
      renderCollectedState();
      return;
    }

    // Cộng dồn và khử trùng theo (rating + text chuẩn hóa)
    const existingKeys = new Set(
      state.reviews.map((r) => `${r.rating}|${r.text.toLowerCase().replace(/\s+/g, " ").trim()}`)
    );
    let added = 0;
    for (const rev of res.reviews) {
      if (state.reviews.length >= 200) break;
      const key = `${rev.rating}|${rev.text.toLowerCase().replace(/\s+/g, " ").trim()}`;
      if (!existingKeys.has(key)) {
        existingKeys.add(key);
        state.reviews.push({ rating: rev.rating, text: rev.text });
        added += 1;
      }
    }

    if (res.blocked) {
      showNotice(res.note, true);
    } else if (added > 0) {
      showNotice(
        `${res.note} (+${added} mới · tổng ${state.reviews.length} review sẵn sàng để Soi bằng AI).`
      );
    } else {
      showNotice(`${res.note} (Tất cả ${state.reviews.length} review đã có sẵn trong danh sách.)`);
    }
    renderCollectedState();
  } catch (err) {
    showNotice(err.message || "Lỗi khi quét trang hiện tại.", true);
  } finally {
    state.isScanning = false;
    state.scanningTabId = null;
    btnAuto.disabled = false;
    btnVisible.disabled = false;
    btnClear.disabled = false;
    btnAuto.textContent = "Tự động quét review";
    btnStop.classList.add("hidden");
  }
}

function highlightQuote(fullText, quote, label) {
  const safeFull = escapeHtml(fullText);
  const q = String(quote || "").trim();
  if (!q) return safeFull;
  const idx = fullText.toLowerCase().indexOf(q.toLowerCase());
  if (idx < 0) return safeFull;
  const before = escapeHtml(fullText.slice(0, idx));
  const match = escapeHtml(fullText.slice(idx, idx + q.length));
  const after = escapeHtml(fullText.slice(idx + q.length));
  return `${before}<mark class="hl-${escapeHtml(label)}">${match}</mark>${after}`;
}

function renderReviewsList() {
  const container = $("reviewsList");
  const data = state.lastResult && state.lastResult.data ? state.lastResult.data : null;
  if (!data || !Array.isArray(data.reviews)) {
    container.innerHTML = "";
    return;
  }

  const filtered =
    state.activeFilter === "all"
      ? data.reviews
      : data.reviews.filter((r) => r.label === state.activeFilter);

  if (!filtered.length) {
    container.innerHTML = `<div class="hint">Không có đánh giá nào thuộc nhóm lọc này.</div>`;
    return;
  }

  container.innerHTML = filtered
    .map((rev) => {
      const meta = LABEL_META[rev.label] || LABEL_META.low_signal;
      const stars = "★".repeat(Math.max(1, Math.min(5, Number(rev.rating) || 5)));
      const bodyHtml = highlightQuote(rev.text || rev.evidence_quote || "", rev.evidence_quote, rev.label);
      return `
        <div class="review-card">
          <div class="review-head">
            <span>
              <strong>${escapeHtml(rev.id)}</strong> ·
              <span style="color:var(--amber)">${stars}</span> ·
              <span class="pill ${meta.pill}">${escapeHtml(meta.name)}</span>
            </span>
            <span style="font-size:10.5px; color:var(--mint); font-weight:700;">${meta.weight}</span>
          </div>
          <div class="review-text">${bodyHtml}</div>
          ${rev.short_reason ? `<div class="review-reason">${escapeHtml(rev.short_reason)}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function renderResult(resp) {
  state.lastResult = resp;
  state.activeFilter = "all";

  $("refusalBox").classList.add("hidden");
  $("resultSection").classList.add("hidden");

  const data = resp.data || {};
  if (data.refused) {
    $("refusalCode").textContent = data.reason || "guardrail";
    $("refusalText").textContent = resp.output || "Yêu cầu nằm ngoài phạm vi phân tích.";
    $("refusalBox").classList.remove("hidden");
    return;
  }
  if (data.error) {
    showError(`Lỗi xử lý mô hình (${data.error}): ${data.detail || "Vui lòng thử lại."}`);
    return;
  }

  const scores = data.scores || {};
  const trace = resp.trace || {};
  const groundingRate = typeof data.grounding_rate === "number" ? data.grounding_rate : 100;

  $("badgeGrounding").textContent = `Grounding ${groundingRate.toFixed(0)}%`;
  $("badgeCache").classList.toggle("hidden", !resp.cached);
  $("traceInfo").textContent = resp.cached
    ? `${trace.model || ""} · ${trace.latency_s || 0}s`
    : `${trace.model || ""} · ${trace.tokens_in || 0}/${trace.tokens_out || 0} tok · ${trace.latency_s || 0}s`;

  $("resProductName").textContent = data.product_name || "Kết quả phân tích";
  const tl = TRUST_META[scores.trust_level] || TRUST_META.insufficient_data;
  $("resTrustBadge").className = `pill ${tl.pill}`;
  $("resTrustBadge").textContent = tl.text;

  $("resPlatformScore").textContent =
    typeof scores.platform_rating === "number" ? `${scores.platform_rating.toFixed(1)}` : "—";
  $("resRealScore").textContent =
    typeof scores.real_trust_score === "number" ? `${scores.real_trust_score.toFixed(1)}` : "N/A";
  $("resVerifiedRatio").textContent =
    typeof scores.verified_ratio === "number" ? `${scores.verified_ratio.toFixed(1)}%` : "—";

  if (typeof scores.score_delta === "number") {
    const sign = scores.score_delta > 0 ? "+" : "";
    $("resDeltaLine").textContent = `Chênh lệch so với điểm sàn: ${sign}${scores.score_delta.toFixed(1)}★ (${scores.direction || ""})`;
  } else {
    $("resDeltaLine").textContent = "Chưa đủ đánh giá chất lượng sản phẩm (toàn bộ là lỗi vận chuyển).";
  }

  if (scores.logistics_warning) {
    $("resLogisticsWarn").textContent =
      "Phát hiện đánh giá chỉ phản ánh lỗi vận chuyển/shipper — đã tách riêng (w=0.00) để không kéo oan điểm sản phẩm.";
    $("resLogisticsWarn").classList.remove("hidden");
  } else {
    $("resLogisticsWarn").classList.add("hidden");
  }

  const counts = scores.label_counts || {};
  const total = Object.values(counts).reduce((a, b) => a + Number(b || 0), 0) || 1;
  const order = ["verified_insight", "low_signal", "suspicious_pattern", "logistics_only"];
  $("distBar").innerHTML = order
    .map((k) => {
      const pct = ((Number(counts[k] || 0) / total) * 100).toFixed(1);
      return `<div style="width:${pct}%; background:${LABEL_META[k].color};"></div>`;
    })
    .join("");
  $("distLegend").innerHTML = order
    .map((k) => `<span><strong style="color:${LABEL_META[k].color}">${Number(counts[k] || 0)}</strong> ${LABEL_META[k].name}</span>`)
    .join("");

  const risks = Array.isArray(data.top_risks) ? data.top_risks : [];
  $("risksList").innerHTML = risks.length
    ? risks
        .map(
          (r, idx) => `
            <div class="risk-item">
              <div class="risk-title">${idx + 1}. ${escapeHtml(r.title || "Rủi ro")}</div>
              <div class="risk-detail">
                ${escapeHtml(r.detail || "")}
                ${r.source_review_ids && r.source_review_ids.length ? ` <strong>(Nguồn: ${escapeHtml(r.source_review_ids.join(", "))})</strong>` : ""}
              </div>
            </div>
          `
        )
        .join("")
    : `<div class="hint">Chưa ghi nhận nhược điểm lặp lại từ nhóm đánh giá trải nghiệm cụ thể.</div>`;

  const questions = Array.isArray(data.questions_for_seller) ? data.questions_for_seller : [];
  $("questionsList").innerHTML = questions.map((q) => `<li>${escapeHtml(q)}</li>`).join("");

  const chips = [
    { key: "all", label: `Tất cả (${(data.reviews || []).length})` },
    ...order.map((k) => ({ key: k, label: `${LABEL_META[k].name} (${Number(counts[k] || 0)})` })),
  ];
  $("filterChips").innerHTML = chips
    .map(
      (c) =>
        `<button class="filter-chip ${c.key === state.activeFilter ? "active" : ""}" data-filter="${c.key}" type="button">${escapeHtml(c.label)}</button>`
    )
    .join("");
  $("filterChips").querySelectorAll(".filter-chip").forEach((el) => {
    el.addEventListener("click", () => {
      state.activeFilter = el.getAttribute("data-filter") || "all";
      $("filterChips").querySelectorAll(".filter-chip").forEach((b) => {
        b.classList.toggle("active", b.getAttribute("data-filter") === state.activeFilter);
      });
      renderReviewsList();
    });
  });

  renderReviewsList();
  $("resultSection").classList.remove("hidden");
}

async function runAnalyze() {
  showError("");
  const bypassCache = $("chkBypassCache").checked;
  let body;

  if (state.mode === "scan") {
    if (!state.reviews.length) {
      showError("Chưa có đánh giá nào. Hãy bấm 'Tự động quét review' hoặc chuyển sang tab 'Dán review thủ công'.");
      return;
    }
    body = { ...buildProductPayload(), bypass_cache: bypassCache };
  } else {
    const raw = $("manualInput").value.trim();
    if (!raw) {
      showError("Ô nhập đang trống. Hãy dán danh sách đánh giá dạng [5] nội dung… hoặc JSON sản phẩm.");
      return;
    }
    body = { raw_text: raw, bypass_cache: bypassCache };
  }

  const btn = $("btnAnalyze");
  const txt = $("btnAnalyzeText");
  btn.disabled = true;
  if (state.mode === "scan" && state.reviews.length > 20) {
    const batches = Math.ceil(state.reviews.length / 20);
    txt.textContent = `Đang phân tích ${state.reviews.length} review (${batches} lô AI thật)…`;
  } else {
    txt.textContent = "Đang phân tích bằng AI thật…";
  }

  try {
    const resp = await fetch(`${state.backendUrl}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(payload.detail || `Lỗi máy chủ (HTTP ${resp.status})`);
    }
    renderResult(payload);
  } catch (err) {
    showError(
      `${err.message || "Không thể kết nối tới Backend"} (${state.backendUrl}). Nếu đang chạy thử trên máy cá nhân, hãy bấm mục 'Cài đặt Backend API' ở dưới → chọn 'Localhost :8000' → 'Lưu & Kiểm tra'.`
    );
  } finally {
    btn.disabled = false;
    txt.textContent = "Soi đánh giá bằng AI";
  }
}

async function init() {
  try {
    const saved = await chrome.storage.local.get([STORAGE_KEY_BACKEND]);
    if (saved && saved[STORAGE_KEY_BACKEND]) {
      state.backendUrl = normalizeUrl(saved[STORAGE_KEY_BACKEND]);
    }
  } catch (_) {
    // Fallback outside extension context
  }
  $("inputBackendUrl").value = state.backendUrl;
  renderCollectedState();
  checkHealth();

  // Nhận tiến độ quét trực tiếp từ content.js
  if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg && msg.type === "RS_SCAN_PROGRESS" && state.isScanning) {
        showNotice(`${msg.message} (${msg.collected}/${msg.target} review)`);
      }
    });
  }

  $("healthBadge").addEventListener("click", () => {
    const box = $("settingsBox");
    box.open = true;
    box.scrollIntoView({ behavior: "smooth", block: "end" });
  });

  $("tabScan").addEventListener("click", () => setMode("scan"));
  $("tabManual").addEventListener("click", () => setMode("manual"));
  $("btnScanPage").addEventListener("click", () => scanActiveTab("auto"));
  $("btnScanVisible").addEventListener("click", () => scanActiveTab("visible"));
  $("btnStopScan").addEventListener("click", stopActiveScan);
  $("btnAnalyze").addEventListener("click", runAnalyze);

  $("btnClearList").addEventListener("click", () => {
    state.reviews = [];
    state.lastPageKey = "";
    $("inputProductName").value = "";
    $("inputPlatformRating").value = "";
    $("scanNotice").classList.add("hidden");
    renderCollectedState();
  });

  $("inputProductName").addEventListener("input", renderCollectedState);
  $("inputPlatformRating").addEventListener("input", renderCollectedState);

  $("btnCopyJson").addEventListener("click", async () => {
    const jsonStr = JSON.stringify(buildProductPayload(), null, 2);
    await navigator.clipboard.writeText(jsonStr);
    showNotice("Đã sao chép JSON chuẩn ReviewShield (đã ẩn danh PII) vào Clipboard!");
  });

  $("btnDownloadJson").addEventListener("click", () => {
    const jsonStr = JSON.stringify(buildProductPayload(), null, 2);
    const blob = new Blob([jsonStr], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reviewshield_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  $("btnCopyQuestions").addEventListener("click", async () => {
    const qs =
      state.lastResult &&
      state.lastResult.data &&
      Array.isArray(state.lastResult.data.questions_for_seller)
        ? state.lastResult.data.questions_for_seller
        : [];
    if (!qs.length) return;
    const text = qs.map((q, i) => `${i + 1}. ${q}`).join("\n");
    await navigator.clipboard.writeText(text);
    const btn = $("btnCopyQuestions");
    btn.textContent = "Đã sao chép!";
    setTimeout(() => {
      btn.textContent = "Sao chép cả 3";
    }, 1500);
  });

  $("btnPresetVps").addEventListener("click", () => {
    $("inputBackendUrl").value = DEFAULT_BACKEND_URL;
  });
  $("btnPresetLocal").addEventListener("click", () => {
    $("inputBackendUrl").value = "http://localhost:8000";
  });
  $("btnSaveBackend").addEventListener("click", async () => {
    state.backendUrl = normalizeUrl($("inputBackendUrl").value);
    $("inputBackendUrl").value = state.backendUrl;
    try {
      await chrome.storage.local.set({ [STORAGE_KEY_BACKEND]: state.backendUrl });
    } catch (_) {
      // ignore
    }
    checkHealth();
  });
}

document.addEventListener("DOMContentLoaded", init);
