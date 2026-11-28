/**
 * ReviewShield Client-Side Auto-Scroll DOM Extractor & PII Scrubber.
 * Chỉ được nạp on-demand qua `chrome.scripting.executeScript` khi người dùng chủ động bấm nút
 * Quét trong Side Panel.
 *
 * Nguyên tắc an toàn:
 * - Không vượt CAPTCHA/anti-bot, không gửi request cào ngầm; tự động dừng ngay nếu phát hiện trang xác minh/đăng nhập.
 * - Giới hạn cứng tối đa 50 review và tối đa 12 lần chuyển bộ lọc/trang với độ trễ lịch sự.
 * - Không thu thập tên tài khoản, avatar, địa chỉ hay cookie của người mua.
 * - Ẩn danh toàn bộ PII (SĐT, email, URL cá nhân, mã đơn dài) ngay tại trình duyệt.
 */
(async () => {
  const cfg = Object.assign(
    {
      mode: "auto", // "auto" (tự cuộn + gom cân bằng) | "visible" (chỉ đọc màn hình hiện tại)
      targetCount: 20, // 20 | 30 | 50
      balanceStars: true,
      restoreScroll: true,
    },
    window.__RS_SCAN_CONFIG__ || {}
  );

  const HARD_MAX_REVIEWS = Math.min(50, Math.max(5, Number(cfg.targetCount) || 20));
  const MAX_SCROLL_STEPS = 24;
  const MAX_INTERACTIONS = 12;
  const MAX_DURATION_MS = 30000;
  const startedAt = Date.now();
  const origScrollY = window.scrollY || window.pageYOffset || 0;

  // Reset cờ dừng nếu không bị kích hoạt trước đó
  if (typeof window.__RS_ABORT_SCAN__ !== "boolean") {
    window.__RS_ABORT_SCAN__ = false;
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function isAborted() {
    return Boolean(window.__RS_ABORT_SCAN__) || Date.now() - startedAt > MAX_DURATION_MS;
  }

  function reportProgress(message, collected = 0) {
    try {
      if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
        const res = chrome.runtime.sendMessage({
          type: "RS_SCAN_PROGRESS",
          message,
          collected,
          target: HARD_MAX_REVIEWS,
        });
        if (res && typeof res.catch === "function") {
          res.catch(() => {});
        }
      }
    } catch (_) {
      // Bỏ qua nếu không có listener
    }
  }

  function cleanSpaces(str) {
    return String(str || "")
      .replace(/\uFFFC/g, "")
      .replace(/\r\n/g, "\n")
      .replace(/[ \t]+/g, " ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function scrubPii(text) {
    let out = cleanSpaces(text);
    // Số điện thoại Việt Nam (liền hoặc ngăn bằng dấu cách/chấm/gạch nối)
    out = out.replace(/(?:\+?84|0)(?:[\s.\-]?)(?:3|5|7|8|9)(?:[\s.\-]?\d){8}\b/g, "[đã ẩn SĐT]");
    // Địa chỉ email
    out = out.replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, "[đã ẩn email]");
    // Đường link mạng xã hội / URL cá nhân
    out = out.replace(/https?:\/\/[^\s)]+/gi, "[đã ẩn link]");
    out = out.replace(/\b(?:fb\.com|facebook\.com|zalo\.me|t\.me)\/[^\s)]+/gi, "[đã ẩn link]");
    // Chuỗi số dài >= 12 chữ số (mã đơn hàng / CCCD / số tài khoản)
    out = out.replace(/\b\d{12,}\b/g, "[đã ẩn mã]");
    return cleanSpaces(out);
  }

  function detectBlockedState() {
    const path = (location.pathname || "").toLowerCase();
    if (
      path.includes("/verify") ||
      path.includes("/captcha") ||
      path.includes("/buyer/login") ||
      path.includes("/security")
    ) {
      return "Trang đã chuyển sang bước xác minh/đăng nhập.";
    }
    const captchaEl = document.querySelector(
      'iframe[src*="captcha"], iframe[src*="recaptcha"], iframe[src*="hcaptcha"], iframe[src*="turnstile"], [class*="captcha-modal"], [id*="captcha"]'
    );
    if (captchaEl && captchaEl.offsetParent !== null) {
      return "Phát hiện hộp thoại xác minh người dùng (CAPTCHA).";
    }
    return null;
  }

  function detectPlatform(hostname) {
    const h = (hostname || "").toLowerCase();
    if (h.includes("shopee")) return "Shopee";
    if (h.includes("tiki")) return "Tiki";
    if (h.includes("dienmayxanh")) return "Điện Máy Xanh";
    if (h.includes("thegioididong")) return "Thế Giới Di Động";
    if (h.includes("lazada")) return "Lazada";
    if (h.includes("tiktok")) return "TikTok Shop";
    return hostname || "Sàn TMĐT";
  }

  function cleanProductTitle(raw) {
    let txt = cleanSpaces(raw);
    txt = txt.replace(/^(?:Yêu\s*thích\+?|Shopee\s*Mall|Mall|Preferred\+?)\s+/i, "");
    return cleanSpaces(txt);
  }

  function extractTitle() {
    const selectors = [
      'h1[class*="product"]',
      '[data-sqe="name"] h1',
      '[data-sqe="name"]',
      '[data-view-id="pdp_details_title"]',
      "main h1",
      "h1",
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      const txt = cleanProductTitle(el ? el.innerText : "");
      if (txt.length >= 4 && txt.length <= 320) {
        return txt;
      }
    }
    return cleanProductTitle((document.title || "Sản phẩm đang xem").split("|")[0].split("- Shopee")[0]);
  }

  function extractPlatformRating() {
    const ratingSelectors = [
      ".product-rating-overview__rating-score",
      '[class*="rating-overview"] [class*="score"]',
      ".review-rating__point",
      ".point",
      '[class*="rating-score"]',
    ];
    for (const sel of ratingSelectors) {
      const el = document.querySelector(sel);
      if (el) {
        const m = cleanSpaces(el.innerText).match(/\b([1-5](?:[.,]\d)?)\b/);
        if (m) {
          const val = parseFloat(m[1].replace(",", "."));
          if (val >= 1.0 && val <= 5.0) return Number(val.toFixed(1));
        }
      }
    }
    const bodyText = (document.body ? document.body.innerText : "").slice(0, 18000);
    const patterns = [
      /([1-5][.,]\d)\s*(?:trên\s*5|\/\s*5)/i,
      /([1-5][.,]\d)\s*\n?\s*[\d.,]+k?\s*Đánh\s*Giá/i,
      /đánh giá[^0-9]{0,20}([1-5][.,]\d)/i,
    ];
    for (const pat of patterns) {
      const m = bodyText.match(pat);
      if (m) {
        const val = parseFloat(m[1].replace(",", "."));
        if (val >= 1.0 && val <= 5.0) return Number(val.toFixed(1));
      }
    }
    return null;
  }

  function stripShopeeNoise(rawText) {
    let text = String(rawText || "");
    // Cắt bỏ phản hồi của người bán
    text = text.replace(/Phản\s*[Hh]ồi\s*[Cc]ủa\s*Người\s*Bán[\s\S]*/i, "");
    text = text.replace(/Seller'?s?\s*Response[\s\S]*/i, "");

    let lines = text
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);

    // Nếu trong 4 dòng đầu có dòng timestamp (YYYY-MM-DD HH:MM), cắt bỏ toàn bộ phần phía trên
    // (tên tài khoản / huy hiệu người mua) để đảm bảo 0% PII ngay cả khi Shopee đổi class CSS.
    const tsIdx = lines.findIndex((l, idx) => idx <= 4 && /^20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}/.test(l));
    if (tsIdx >= 0) {
      lines = lines.slice(tsIdx + 1);
    }

    lines = lines.filter((l) => {
      if (!l) return false;
      if (/^20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}/.test(l)) return false;
      if (/^Phân loại hàng\s*:/i.test(l)) return false;
      if (/^Hữu ích\??(\s*\(\d+\))?$/i.test(l)) return false;
      if (/^\d{1,4}$/.test(l)) return false; // số lượt thích đơn lẻ cuối review
      if (/^\d+\s*:\s*\d+$/.test(l)) return false; // thời lượng video
      if (/^(?:Báo cáo|Xem thêm|Thu gọn|Đã mua hàng|Đánh giá của người mua)$/i.test(l)) return false;
      return true;
    });

    return scrubPii(lines.join("\n"));
  }

  function isWarmOrFilledColor(colorStr) {
    const c = String(colorStr || "").trim().toLowerCase();
    if (!c || c === "none" || c === "transparent" || c === "rgba(0, 0, 0, 0)") return false;
    const rgb = c.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
    if (rgb) {
      const r = Number(rgb[1]);
      const g = Number(rgb[2]);
      const b = Number(rgb[3]);
      // Loại bỏ xám nhạt (sao rỗng)
      if (Math.abs(r - g) < 15 && Math.abs(g - b) < 15 && r > 150) return false;
      return true;
    }
    return c !== "#ccc" && c !== "#d5d5d5" && c !== "#e0e0e0" && c !== "#dbdbdb";
  }

  function countStarsInNode(node, forcedRating = null) {
    if (forcedRating && forcedRating >= 1 && forcedRating <= 5) {
      return forcedRating;
    }
    // 1. Shopee / DMX / TGDĐ active star classes
    const activeIcons = node.querySelectorAll(
      ".icon-rating-solid--active, [class*='rating-solid--active'], [class*='star-active'], .iconcmt-starbuy, .icon-star-orange"
    );
    if (activeIcons.length >= 1 && activeIcons.length <= 5) {
      return activeIcons.length;
    }
    // 2. Tiki / CSS percentage width stars
    const widthBar = node.querySelector(
      '[class*="Stars__StyledStars"] [style*="width"], [class*="rating"] [style*="width"]'
    );
    if (widthBar && widthBar.style && widthBar.style.width) {
      const m = widthBar.style.width.match(/(\d+(?:\.\d+)?)%/);
      if (m) {
        const stars = Math.round((parseFloat(m[1]) / 100) * 5);
        if (stars >= 1 && stars <= 5) return stars;
      }
    }
    // 3. Fallback: tìm nhóm đúng 5 thẻ SVG sao trong thẻ đánh giá (chống đổi class CSS)
    const candidates = [
      ...node.querySelectorAll('[class*="rating"], [class*="star"]'),
      ...node.querySelectorAll("div, span"),
    ];
    for (const wrap of candidates) {
      if (cleanSpaces(wrap.innerText || "").length > 0) continue;
      const svgs = [...wrap.querySelectorAll("svg")];
      if (svgs.length === 5) {
        let filled = 0;
        for (const svg of svgs) {
          const cls = (svg.getAttribute("class") || "").toLowerCase();
          if (cls.includes("active") || cls.includes("solid")) {
            filled += 1;
            continue;
          }
          const shape = svg.querySelector("polygon, path");
          if (shape) {
            const attrFill = (shape.getAttribute("fill") || "").toLowerCase();
            if (attrFill === "none") continue;
            const compFill = window.getComputedStyle ? window.getComputedStyle(shape).fill : attrFill;
            if (isWarmOrFilledColor(compFill || attrFill)) {
              filled += 1;
            }
          }
        }
        if (filled >= 1 && filled <= 5) return filled;
      }
    }
    return 5;
  }

  function findReviewSection(platform) {
    if (platform === "Shopee") {
      const direct = document.querySelector(
        ".product-ratings, [class*='product-ratings'], .shopee-product-comment-list"
      );
      if (direct) return direct.closest("section, div[class*='rating']") || direct;
    }
    if (platform === "Tiki") {
      const direct = document.querySelector('[class*="customer-reviews"], .review-comment');
      if (direct) return direct.closest("section, div[class*='review']") || direct.parentElement;
    }
    if (platform === "Điện Máy Xanh" || platform === "Thế Giới Di Động") {
      const direct = document.querySelector(".box-review, .comment, ul.comment-list");
      if (direct) return direct;
    }

    // Tìm theo tiêu đề văn bản (chống đổi class CSS)
    const headings = document.querySelectorAll("h2, h3, h4, div");
    for (const el of headings) {
      if (el.children.length > 2) continue;
      const t = cleanSpaces(el.innerText || "");
      if (
        /^(?:ĐÁNH GIÁ SẢN PHẨM|Product Ratings|Khách hàng đánh giá|Đánh giá sản phẩm)$/i.test(t)
      ) {
        let parent = el.parentElement;
        for (let i = 0; i < 4 && parent; i += 1) {
          if ((parent.innerText || "").length > 180) return parent;
          parent = parent.parentElement;
        }
        return el.parentElement || el;
      }
    }
    return null;
  }

  function findShopeeCards() {
    // Tầng 1: selector chuẩn Shopee
    let cards = [
      ...document.querySelectorAll(
        ".shopee-product-rating, [data-cmtid], [class*='shopee-product-rating__main']"
      ),
    ];
    cards = cards.filter((el) => !cards.some((other) => other !== el && other.contains(el)));
    if (cards.length > 0) return cards;

    // Tầng 2: fallback theo cấu trúc timestamp YYYY-MM-DD HH:MM trong khu vực Đánh giá
    const section = findReviewSection("Shopee") || document.body;
    if (!section) return [];
    const tsRegex = /^20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}/;
    const allTsNodes = [...section.querySelectorAll("div, span")].filter((el) => {
      if (el.children.length > 3) return false;
      return tsRegex.test(cleanSpaces(el.innerText || ""));
    });

    const structuralCards = [];
    for (const tsEl of allTsNodes) {
      let cur = tsEl.parentElement;
      let best = null;
      for (let depth = 0; depth < 6 && cur && cur !== section; depth += 1) {
        const txt = cur.innerText || "";
        const tsMatches = txt.match(/20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}/g) || [];
        if (tsMatches.length === 1 && txt.length < 4000) {
          best = cur;
        } else if (tsMatches.length > 1) {
          break;
        }
        cur = cur.parentElement;
      }
      if (best && !structuralCards.includes(best)) {
        structuralCards.push(best);
      }
    }
    return structuralCards.filter(
      (el) => !structuralCards.some((other) => other !== el && other.contains(el))
    );
  }

  function extractShopee(forcedRating = null) {
    const uniqueCards = findShopeeCards();
    const results = [];
    for (const card of uniqueCards) {
      const clone = card.cloneNode(true);
      clone
        .querySelectorAll(
          "[class*='author-name'], [class*='avatar'], [class*='seller-response'], [class*='actions'], [class*='tags'], [class*='image-list'], button, video, img, svg"
        )
        .forEach((n) => n.remove());

      const rating = countStarsInNode(card, forcedRating);
      const bodyCandidate =
        clone.querySelector('[style*="margin-top: 0.75rem"], [class*="rating__content"]') || clone;
      const text = stripShopeeNoise(bodyCandidate.innerText || "");
      if (text.length >= 3) {
        results.push({ rating, text });
      }
    }
    return results;
  }

  function extractTiki(forcedRating = null) {
    const cards = [
      ...document.querySelectorAll(".review-comment, [class*='review-comment__container']"),
    ];
    const uniqueCards = cards.filter(
      (el) => !cards.some((other) => other !== el && other.contains(el))
    );
    const results = [];
    for (const card of uniqueCards) {
      const rating = countStarsInNode(card, forcedRating);
      const titleEl = card.querySelector(".review-comment__title");
      const bodyEl = card.querySelector(".review-comment__content");
      const combined = [titleEl ? titleEl.innerText : "", bodyEl ? bodyEl.innerText : ""]
        .filter(Boolean)
        .join(". ");
      const text = scrubPii(combined);
      if (text.length >= 3) {
        results.push({ rating, text });
      }
    }
    return results;
  }

  function extractDmxTgdd(forcedRating = null) {
    const cards = [...document.querySelectorAll(".comment-item, .cmt-item, ul.comment-list > li")];
    const uniqueCards = cards.filter(
      (el) => !cards.some((other) => other !== el && other.contains(el))
    );
    const results = [];
    for (const card of uniqueCards) {
      const rating = countStarsInNode(card, forcedRating);
      const bodyEl = card.querySelector(".cmt-txt, .txt-content, .comment-content, p");
      const text = scrubPii(bodyEl ? bodyEl.innerText : "");
      if (text.length >= 3) {
        results.push({ rating, text });
      }
    }
    return results;
  }

  function extractVisibleByPlatform(platform, forcedRating = null) {
    if (platform === "Shopee") return extractShopee(forcedRating);
    if (platform === "Tiki") return extractTiki(forcedRating);
    if (platform === "Điện Máy Xanh" || platform === "Thế Giới Di Động") {
      return extractDmxTgdd(forcedRating);
    }
    let res = extractShopee(forcedRating);
    if (!res.length) res = extractTiki(forcedRating);
    if (!res.length) res = extractDmxTgdd(forcedRating);
    return res;
  }

  function extractFromSelection() {
    const selText = cleanSpaces(window.getSelection ? window.getSelection().toString() : "");
    if (!selText || selText.length < 6) return [];
    const lines = selText
      .split(/\n+/)
      .map((l) => l.trim())
      .filter((l) => l.length >= 4);

    const results = [];
    const linePat = /^(?:\[?\s*([1-5])\s*(?:sao|★|\*)?\s*\]?\s*[:\-–—.]?\s*)(.+)$/i;
    for (const line of lines) {
      const m = line.match(linePat);
      const rating = m ? parseInt(m[1], 10) : 5;
      const text = scrubPii(m ? m[2] : line);
      if (text.length >= 3) {
        results.push({ rating, text });
      }
      if (results.length >= HARD_MAX_REVIEWS) break;
    }
    return results;
  }

  function getFingerprint(items) {
    return items
      .slice(0, 6)
      .map((r) => `${r.rating}:${r.text.slice(0, 35)}`)
      .join("||");
  }

  async function waitForDomReviews(platform, timeoutMs = 2600) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (isAborted() || detectBlockedState()) return extractVisibleByPlatform(platform);
      const found = extractVisibleByPlatform(platform);
      if (found.length > 0) return found;
      await sleep(200);
    }
    return extractVisibleByPlatform(platform);
  }

  async function waitForReviewsChange(platform, prevFp, forcedRating = null, timeoutMs = 2800) {
    const start = Date.now();
    await sleep(450);
    while (Date.now() - start < timeoutMs) {
      if (isAborted() || detectBlockedState()) break;
      const current = extractVisibleByPlatform(platform, forcedRating);
      const fp = getFingerprint(current);
      if (current.length > 0 && fp !== prevFp) {
        await sleep(180);
        return extractVisibleByPlatform(platform, forcedRating);
      }
      await sleep(200);
    }
    return extractVisibleByPlatform(platform, forcedRating);
  }

  async function autoScrollToReviews(platform) {
    // Nếu review đã hiện sẵn trong DOM thì chỉ cần cuộn tới nhẹ
    if (extractVisibleByPlatform(platform).length > 0) {
      const sec = findReviewSection(platform);
      if (sec) sec.scrollIntoView({ behavior: "instant", block: "start" });
      return true;
    }

    reportProgress("Đang tự cuộn tải mục Đánh giá sản phẩm…", 0);
    const stepPx = Math.max(520, Math.round(window.innerHeight * 0.85));
    let stuckCount = 0;
    let lastScrollY = -1;

    for (let step = 0; step < MAX_SCROLL_STEPS; step += 1) {
      if (isAborted() || detectBlockedState()) return false;

      const sec = findReviewSection(platform);
      if (sec) {
        sec.scrollIntoView({ behavior: "instant", block: "start" });
        const loaded = await waitForDomReviews(platform, 2600);
        if (loaded.length > 0) return true;
      }

      if (extractVisibleByPlatform(platform).length > 0) {
        return true;
      }

      const nextY = (window.scrollY || 0) + stepPx;
      window.scrollTo({ top: nextY, behavior: "instant" });
      await sleep(280);

      const curY = window.scrollY || 0;
      const docHeight = document.documentElement.scrollHeight || document.body.scrollHeight || 0;
      if (Math.abs(curY - lastScrollY) < 10 || curY + window.innerHeight >= docHeight - 20) {
        stuckCount += 1;
        if (stuckCount >= 2) break;
      } else {
        stuckCount = 0;
      }
      lastScrollY = curY;
    }

    const sec = findReviewSection(platform);
    if (sec) {
      sec.scrollIntoView({ behavior: "instant", block: "start" });
      const loaded = await waitForDomReviews(platform, 2400);
      if (loaded.length > 0) return true;
    }
    return extractVisibleByPlatform(platform).length > 0;
  }

  function parseFilterCount(labelText) {
    const m = labelText.match(/\(\s*([\d.,]+)\s*([kKmM]?)\s*\)/);
    if (!m) return 1; // Không ghi số lượng (vd: "Tất Cả") -> coi là có dữ liệu
    let num = parseFloat(m[1].replace(",", "."));
    if (Number.isNaN(num)) return 1;
    const unit = (m[2] || "").toLowerCase();
    if (unit === "k") num *= 1000;
    if (unit === "m") num *= 1000000;
    return Math.round(num);
  }

  function findShopeeFilters() {
    const section = findReviewSection("Shopee") || document.body;
    let nodes = [...section.querySelectorAll(".product-rating-overview__filter")];
    if (!nodes.length) {
      const pat = /^(?:Tất Cả|Có Bình Luận|[1-5]\s*Sao)(?:\s*\([\d.,kKmM]+\))?$/i;
      const raw = [...section.querySelectorAll("div, button, span")].filter((el) => {
        const t = cleanSpaces(el.innerText || "");
        return t.length >= 4 && t.length <= 32 && pat.test(t);
      });
      nodes = raw.filter((el) => !raw.some((child) => child !== el && el.contains(child)));
    }

    const map = {};
    for (const el of nodes) {
      const txt = cleanSpaces(el.innerText || "");
      const count = parseFilterCount(txt);
      if (/^Tất Cả/i.test(txt)) map.all = { el, count, text: txt };
      else if (/^Có Bình Luận/i.test(txt)) map.withComment = { el, count, text: txt };
      else if (/^5\s*Sao/i.test(txt)) map.star5 = { el, count, text: txt };
      else if (/^4\s*Sao/i.test(txt)) map.star4 = { el, count, text: txt };
      else if (/^3\s*Sao/i.test(txt)) map.star3 = { el, count, text: txt };
      else if (/^2\s*Sao/i.test(txt)) map.star2 = { el, count, text: txt };
      else if (/^1\s*Sao/i.test(txt)) map.star1 = { el, count, text: txt };
    }
    return map;
  }

  function findShopeeNextButton() {
    const section = findReviewSection("Shopee") || document.body;
    const direct = section.querySelector(".shopee-icon-button--right");
    if (direct && !direct.disabled && !direct.className.includes("disabled")) {
      return direct;
    }
    // Fallback 1: thanh điều hướng chuẩn
    const navs = [...section.querySelectorAll('nav, [role="navigation"], [class*="page-controller"]')];
    for (const nav of navs) {
      const btns = [...nav.querySelectorAll("button")];
      if (btns.length >= 3) {
        const last = btns[btns.length - 1];
        if (last && !last.disabled && last.getAttribute("aria-disabled") !== "true") {
          return last;
        }
      }
    }
    // Fallback 2: tìm nhóm nút chứa nút trang "1" và "2" rồi lấy nút mũi tên cuối bên phải
    const pageOneBtn = [...section.querySelectorAll("button")].find(
      (b) => cleanSpaces(b.innerText || "") === "1"
    );
    if (pageOneBtn && pageOneBtn.parentElement) {
      const btns = [...pageOneBtn.parentElement.querySelectorAll("button")];
      if (btns.length >= 3) {
        const last = btns[btns.length - 1];
        if (last && !last.disabled && last.getAttribute("aria-disabled") !== "true") {
          return last;
        }
      }
    }
    return null;
  }

  function findTikiNextButton() {
    const section = findReviewSection("Tiki") || document.body;
    const btn = section.querySelector(
      'a.btn.next, button.btn.next, [data-view-id="pdp_review_pagination_next"], li.next a'
    );
    if (btn && !btn.disabled && !btn.classList.contains("disabled")) return btn;
    return null;
  }

  // Kho lưu review khử trùng trong phiên quét
  const seen = new Set();
  const collected = [];
  let interactionCount = 0;

  function addBatch(items, limit = HARD_MAX_REVIEWS) {
    let added = 0;
    for (const item of items) {
      if (collected.length >= limit || collected.length >= HARD_MAX_REVIEWS) break;
      const rating = Math.min(5, Math.max(1, Number(item.rating) || 5));
      const text = cleanSpaces(item.text);
      if (text.length < 3) continue;
      const key = `${rating}|${text.toLowerCase().replace(/\s+/g, " ")}`;
      if (seen.has(key)) continue;
      seen.add(key);
      collected.push({ rating, text });
      added += 1;
    }
    return added;
  }

  async function paginateShopee(forcedRating, targetLimit, maxPages, label) {
    let page = 1;
    while (
      page < maxPages &&
      collected.length < targetLimit &&
      collected.length < HARD_MAX_REVIEWS &&
      interactionCount < MAX_INTERACTIONS &&
      !isAborted() &&
      !detectBlockedState()
    ) {
      const nextBtn = findShopeeNextButton();
      if (!nextBtn) break;
      const prevFp = getFingerprint(extractShopee(forcedRating));
      interactionCount += 1;
      nextBtn.click();
      page += 1;
      reportProgress(`Đang quét ${label} · trang ${page}…`, collected.length);
      const nextBatch = await waitForReviewsChange("Shopee", prevFp, forcedRating, 2800);
      const added = addBatch(nextBatch, targetLimit);
      if (added === 0) break;
      await sleep(320);
    }
  }

  async function collectShopeeAuto() {
    const filters = findShopeeFilters();
    const lowQuota = cfg.balanceStars ? Math.max(4, Math.round(HARD_MAX_REVIEWS * 0.4)) : 0;
    const generalLimit = Math.max(6, HARD_MAX_REVIEWS - lowQuota);

    // Chặng 1: Gom đánh giá tổng hợp (ưu tiên "Có Bình Luận" để tránh sao trống không chữ)
    if (filters.withComment && filters.withComment.count > 0 && interactionCount < MAX_INTERACTIONS) {
      const prevFp = getFingerprint(extractShopee());
      interactionCount += 1;
      filters.withComment.el.click();
      reportProgress("Đang quét mục Có Bình Luận…", collected.length);
      const batch = await waitForReviewsChange("Shopee", prevFp, null, 2800);
      addBatch(batch, generalLimit);
      await sleep(300);
    } else {
      reportProgress("Đang quét trang đánh giá đầu tiên…", collected.length);
      addBatch(extractShopee(), generalLimit);
    }

    await paginateShopee(null, generalLimit, cfg.balanceStars ? 4 : 8, "Có Bình Luận");

    // Chặng 2: Tự động chuyển sang bộ lọc 1★, 2★, 3★ để bắt rủi ro thực tế
    if (cfg.balanceStars && collected.length < HARD_MAX_REVIEWS && !isAborted() && !detectBlockedState()) {
      const lowOrder = [
        { key: "star1", star: 1, name: "1 Sao" },
        { key: "star2", star: 2, name: "2 Sao" },
        { key: "star3", star: 3, name: "3 Sao" },
      ];
      for (const item of lowOrder) {
        if (
          collected.length >= HARD_MAX_REVIEWS ||
          interactionCount >= MAX_INTERACTIONS ||
          isAborted() ||
          detectBlockedState()
        ) {
          break;
        }
        const refreshed = findShopeeFilters();
        const tab = refreshed[item.key];
        if (!tab || tab.count <= 0) continue;

        const prevFp = getFingerprint(extractShopee());
        interactionCount += 1;
        tab.el.click();
        reportProgress(`Đang gom thêm đánh giá ${item.name}…`, collected.length);
        const batch = await waitForReviewsChange("Shopee", prevFp, item.star, 2800);
        addBatch(batch, HARD_MAX_REVIEWS);
        await sleep(320);

        if (collected.length < HARD_MAX_REVIEWS && HARD_MAX_REVIEWS >= 30 && tab.count > 6) {
          await paginateShopee(item.star, HARD_MAX_REVIEWS, 2, item.name);
        }
      }
    }

    // Chặng 3: Nếu sản phẩm có ít đánh giá 1–3★ nên chưa đủ mục tiêu, bổ sung thêm từ 4★ / 5★
    if (
      collected.length < HARD_MAX_REVIEWS &&
      interactionCount < MAX_INTERACTIONS &&
      !isAborted() &&
      !detectBlockedState()
    ) {
      const refreshed = findShopeeFilters();
      const fillOrder = [
        { key: "star4", star: 4, name: "4 Sao" },
        { key: "star5", star: 5, name: "5 Sao" },
      ];
      for (const item of fillOrder) {
        if (
          collected.length >= HARD_MAX_REVIEWS ||
          interactionCount >= MAX_INTERACTIONS ||
          isAborted() ||
          detectBlockedState()
        ) {
          break;
        }
        const tab = refreshed[item.key];
        if (!tab || tab.count <= 0) continue;
        const prevFp = getFingerprint(extractShopee());
        interactionCount += 1;
        tab.el.click();
        reportProgress(`Đang bổ sung đánh giá ${item.name}…`, collected.length);
        const batch = await waitForReviewsChange("Shopee", prevFp, item.star, 2800);
        addBatch(batch, HARD_MAX_REVIEWS);
        await sleep(300);
      }
    }
  }

  async function collectTikiAuto() {
    reportProgress("Đang quét đánh giá Tiki…", 0);
    addBatch(extractTiki(), HARD_MAX_REVIEWS);
    let page = 1;
    while (
      page < 6 &&
      collected.length < HARD_MAX_REVIEWS &&
      interactionCount < MAX_INTERACTIONS &&
      !isAborted() &&
      !detectBlockedState()
    ) {
      const nextBtn = findTikiNextButton();
      if (!nextBtn) break;
      const prevFp = getFingerprint(extractTiki());
      interactionCount += 1;
      nextBtn.click();
      page += 1;
      reportProgress(`Đang quét Tiki · trang ${page}…`, collected.length);
      const batch = await waitForReviewsChange("Tiki", prevFp, null, 2800);
      const added = addBatch(batch, HARD_MAX_REVIEWS);
      if (added === 0) break;
      await sleep(320);
    }
  }

  // ===== LUỒNG CHẠY CHÍNH =====
  const hostname = location.hostname || "";
  const platform = detectPlatform(hostname);
  const initialTitle = extractTitle();
  let platformRating = extractPlatformRating();
  let sourceMode = cfg.mode === "visible" ? "dom_visible" : "dom_auto";
  let blockedReason = detectBlockedState();
  let userStopped = false;

  try {
    if (!blockedReason) {
      if (cfg.mode === "visible") {
        addBatch(extractVisibleByPlatform(platform), HARD_MAX_REVIEWS);
      } else {
        const mounted = await autoScrollToReviews(platform);
        // Cập nhật lại điểm sàn sau khi khu vực Đánh giá đã hiển thị đầy đủ
        const ratingAfterScroll = extractPlatformRating();
        if (typeof ratingAfterScroll === "number") {
          platformRating = ratingAfterScroll;
        }
        blockedReason = detectBlockedState();
        if (!blockedReason && mounted) {
          if (platform === "Shopee") {
            await collectShopeeAuto();
          } else if (platform === "Tiki") {
            await collectTikiAuto();
          } else {
            addBatch(extractVisibleByPlatform(platform), HARD_MAX_REVIEWS);
          }
        }
        blockedReason = blockedReason || detectBlockedState();
        userStopped = Boolean(window.__RS_ABORT_SCAN__);
      }

      // Fallback bôi đen văn bản nếu không tìm thấy review trong DOM
      if (!collected.length) {
        const selItems = extractFromSelection();
        if (selItems.length > 0) {
          addBatch(selItems, HARD_MAX_REVIEWS);
          sourceMode = "selection";
        } else {
          sourceMode = "none";
        }
      }
    }
  } finally {
    window.__RS_ABORT_SCAN__ = false;
    if (cfg.mode !== "visible" && cfg.restoreScroll) {
      try {
        window.scrollTo({ top: origScrollY, behavior: "instant" });
      } catch (_) {
        window.scrollTo(0, origScrollY);
      }
    }
  }

  const productName = initialTitle || extractTitle();
  const reviews = collected.map((item, idx) => ({
    id: `r${idx + 1}`,
    author: `user_${String(idx + 1).padStart(2, "0")}`,
    rating: item.rating,
    text: item.text,
  }));

  let note = "";
  if (blockedReason) {
    note = `${blockedReason} Đã dừng ngay để bảo vệ tài khoản (${reviews.length} review đã gom trước đó).`;
  } else if (reviews.length > 0) {
    if (sourceMode === "selection") {
      note = `Đã lấy ${reviews.length} đánh giá từ đoạn văn bản bạn bôi đen (đã ẩn danh PII).`;
    } else if (userStopped) {
      note = `Đã dừng theo yêu cầu — giữ lại ${reviews.length} đánh giá đã gom trên ${platform} (100% ẩn danh PII).`;
    } else if (cfg.mode === "visible") {
      note = `Đã quét nhanh ${reviews.length} đánh giá đang hiển thị trên ${platform} (100% ẩn danh PII).`;
    } else {
      note = `Đã tự cuộn và gom ${reviews.length} đánh giá trên ${platform} (đã tự động cân bằng dải sao & ẩn danh 100% PII).`;
    }
  } else {
    note =
      "Chưa tìm thấy đánh giá sau khi tự cuộn. Sản phẩm có thể chưa có bình luận chữ, hoặc sàn yêu cầu đăng nhập để xem đánh giá — bạn cũng có thể bôi đen vùng review hoặc dùng tab 'Dán review thủ công'.";
  }

  return {
    ok: reviews.length > 0,
    blocked: Boolean(blockedReason),
    stopped_by_user: userStopped,
    platform,
    product_name: productName,
    platform_rating: platformRating,
    category: "phu_kien_dien_tu",
    source_mode: sourceMode,
    reviews,
    note,
  };
})();
