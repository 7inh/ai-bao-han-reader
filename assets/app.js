(() => {
  "use strict";

  const STORAGE_KEY = "ai-bao-han-last-chapter";
  const FONT_KEY = "ai-bao-han-font-size";
  const THEME_KEY = "ai-bao-han-theme";
  const MIN_FONT = 0.9;
  const MAX_FONT = 1.4;
  const TOC_WINDOW = 80;
  const DESKTOP_MQ = "(min-width: 768px)";
  const SITE_TITLE = "Ai Bảo Hắn Tu Tiên";

  let chapters = [];
  let byN = {};
  let currentN = null;
  let searchQuery = "";
  let activeSheet = null;
  const cache = new Map();

  const $ = (id) => document.getElementById(id);

  const landingView = $("landingView");
  const readerView = $("readerView");
  const bottomNav = $("bottomNav");
  const progressTrack = $("progressTrack");
  const progressFill = $("progressFill");
  const chapterTitle = $("chapterTitle");
  const chapterMeta = $("chapterMeta");
  const chapterUpdated = $("chapterUpdated");
  const chapterContent = $("chapterContent");
  const chapterCountMeta = $("chapterCountMeta");
  const resumeBtn = $("resumeBtn");
  const readerTop = $("readerTop");
  const desktopToc = $("desktopToc");
  const tocList = $("tocList");
  const desktopTocList = $("desktopTocList");
  const sheetBackdrop = $("sheetBackdrop");
  const tocSheet = $("tocSheet");
  const settingsSheet = $("settingsSheet");

  function formatUpdatedAt(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
  }

  function escapeHtml(text) {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function textToHtml(text) {
    const paras = text.trim().split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
    if (!paras.length) return "<p>（Trống）</p>";
    return paras.map((p) => `<p>${escapeHtml(p).replaceAll("\n", "<br>")}</p>`).join("");
  }

  function setFontSize(rem) {
    const clamped = Math.min(MAX_FONT, Math.max(MIN_FONT, rem));
    document.documentElement.style.setProperty("--font-size", `${clamped}rem`);
    localStorage.setItem(FONT_KEY, String(clamped));
    const slider = $("fontSlider");
    const label = $("fontValue");
    if (slider) slider.value = String(clamped);
    if (label) label.textContent = `${Math.round(clamped * 100)}%`;
  }

  function getSavedFontSize() {
    const raw = Number(localStorage.getItem(FONT_KEY));
    return Number.isFinite(raw) ? raw : 1.05;
  }

  function setTheme(theme) {
    const next = theme === "light" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem(THEME_KEY, next);
    const meta = document.querySelector('meta[name="theme-color"]');
    const color = getComputedStyle(document.documentElement).getPropertyValue("--theme-color").trim();
    if (meta && color) meta.content = color;
    $("themeDarkBtn")?.classList.toggle("is-active", next === "dark");
    $("themeLightBtn")?.classList.toggle("is-active", next === "light");
  }

  function getSavedTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }

  function parseHash() {
    const match = location.hash.match(/^#ch=(\d+)$/);
    return match ? Number(match[1]) : null;
  }

  function setHash(n) {
    const next = `#ch=${n}`;
    if (location.hash !== next) history.pushState(null, "", next);
  }

  function updateProgress() {
    if (!chapters.length || currentN == null) {
      progressTrack.classList.add("hidden");
      return;
    }
    progressTrack.classList.remove("hidden");
    const pct = (currentN / chapters.length) * 100;
    progressFill.style.width = `${pct}%`;
  }

  function isDesktop() {
    return window.matchMedia(DESKTOP_MQ).matches;
  }

  function syncReadingLayout() {
    const reading = currentN != null;
    document.body.classList.toggle("is-reading", reading && isDesktop());
    desktopToc.classList.toggle("hidden", !reading || !isDesktop());
  }

  function showLanding() {
    landingView.classList.remove("hidden");
    readerView.classList.add("hidden");
    bottomNav.classList.add("hidden");
    desktopToc.classList.add("hidden");
    document.body.classList.remove("is-reading");
    progressTrack.classList.add("hidden");
    document.title = SITE_TITLE;
    currentN = null;
    closeAllSheets();
    if (location.hash) history.replaceState(null, "", location.pathname);
  }

  function showReaderShell() {
    landingView.classList.add("hidden");
    readerView.classList.remove("hidden");
    bottomNav.classList.remove("hidden");
    syncReadingLayout();
    progressTrack.classList.remove("hidden");
  }

  function updateNavButtons() {
    const idx = chapters.findIndex((c) => c.n === currentN);
    $("prevBtn").disabled = idx <= 0;
    $("nextBtn").disabled = idx < 0 || idx >= chapters.length - 1;
    const label = idx >= 0 ? `${currentN}/${chapters.length}` : "—";
    $("navCenter").textContent = label;
    updateProgress();
  }

  function filteredChapters() {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return chapters;
    return chapters.filter((c) => c.title.toLowerCase().includes(q));
  }

  function buildTocSlice(list) {
    if (!list.length) return [];
    if (searchQuery.trim()) return list.slice(0, 120);

    if (currentN) {
      const centerIdx = list.findIndex((c) => c.n === currentN);
      if (centerIdx >= 0) {
        const half = Math.floor(TOC_WINDOW / 2);
        const start = Math.max(0, centerIdx - half);
        return list.slice(start, Math.min(list.length, start + TOC_WINDOW));
      }
    }
    return list.slice(0, TOC_WINDOW);
  }

  function renderTocList(container) {
    const list = filteredChapters();
    if (!list.length) {
      container.innerHTML = '<div class="toc-empty">Không có kết quả.</div>';
      return;
    }
    const slice = buildTocSlice(list);
    container.innerHTML = slice
      .map(
        (c) => `
        <button type="button" class="toc-item${c.n === currentN ? " active" : ""}" data-n="${c.n}">
          <span class="toc-item__title">${escapeHtml(c.title)}</span>
          ${c.updated_at ? `<span class="toc-item__date">${escapeHtml(formatUpdatedAt(c.updated_at))}</span>` : ""}
        </button>`
      )
      .join("");
  }

  function renderToc() {
    renderTocList(tocList);
    renderTocList(desktopTocList);
  }

  function showSkeleton() {
    chapterContent.innerHTML = `
      <div class="skeleton" aria-busy="true">
        <div class="skeleton__line"></div>
        <div class="skeleton__line"></div>
        <div class="skeleton__line"></div>
        <div class="skeleton__line skeleton__line--short"></div>
      </div>`;
  }

  async function loadChapterText(path) {
    if (cache.has(path)) return cache.get(path);
    const res = await fetch(path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const text = await res.text();
    cache.set(path, text);
    return text;
  }

  async function openChapter(n, { scrollTop = true } = {}) {
    const ch = byN[n];
    if (!ch) return;

    currentN = n;
    showReaderShell();
    chapterTitle.textContent = ch.title;
    chapterMeta.textContent = `Chương ${n} · ${ch.story}`;
    if (ch.updated_at) {
      chapterUpdated.textContent = `Cập nhật: ${formatUpdatedAt(ch.updated_at)}`;
      chapterUpdated.classList.remove("hidden");
    } else {
      chapterUpdated.textContent = "";
      chapterUpdated.classList.add("hidden");
    }
    document.title = `${ch.title} · ${SITE_TITLE}`;
    showSkeleton();
    updateNavButtons();
    renderToc();
    setHash(n);
    localStorage.setItem(STORAGE_KEY, String(n));
    readerTop.classList.remove("is-collapsed");

    try {
      const text = await loadChapterText(ch.path);
      if (currentN !== n) return;
      chapterContent.innerHTML = textToHtml(text);
    } catch (err) {
      if (currentN !== n) return;
      chapterContent.innerHTML = `<div class="error">Không tải được chương: ${escapeHtml(err.message || err)}</div>`;
    }

    if (scrollTop) window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function openSheet(sheet) {
    closeAllSheets();
    activeSheet = sheet;
    sheet.classList.add("is-open");
    sheet.setAttribute("aria-hidden", "false");
    sheetBackdrop.classList.add("is-open");
    document.body.style.overflow = "hidden";
    if (sheet === tocSheet) renderToc();
  }

  function closeAllSheets() {
    [tocSheet, settingsSheet].forEach((sheet) => {
      sheet.classList.remove("is-open");
      sheet.setAttribute("aria-hidden", "true");
    });
    sheetBackdrop.classList.remove("is-open");
    document.body.style.overflow = "";
    activeSheet = null;
  }

  function focusDesktopToc() {
    const input = $("desktopSearchInput");
    input?.focus();
    const active = desktopTocList.querySelector(".toc-item.active");
    if (active) {
      active.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  function openToc() {
    if (isDesktop()) {
      closeAllSheets();
      focusDesktopToc();
      return;
    }
    openSheet(tocSheet);
  }

  function bindTocClicks(container) {
    container.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-n]");
      if (!btn) return;
      openChapter(Number(btn.dataset.n));
      closeAllSheets();
    });
  }

  function setupScrollCollapse() {
    let lastY = 0;
    window.addEventListener(
      "scroll",
      () => {
        if (currentN == null) return;
        const y = window.scrollY;
        if (y > 80 && y > lastY) {
          readerTop.classList.add("is-collapsed");
        } else if (y < lastY - 10) {
          readerTop.classList.remove("is-collapsed");
        }
        lastY = y;
      },
      { passive: true }
    );
  }

  function setupSheetSwipe(sheet) {
    const handle = sheet.querySelector(".sheet__handle");
    if (!handle) return;
    let startY = 0;
    handle.addEventListener(
      "touchstart",
      (e) => {
        startY = e.touches[0].clientY;
      },
      { passive: true }
    );
    handle.addEventListener(
      "touchend",
      (e) => {
        const delta = e.changedTouches[0].clientY - startY;
        if (delta > 60) closeAllSheets();
      },
      { passive: true }
    );
  }

  async function init() {
    setTheme(getSavedTheme());
    setFontSize(getSavedFontSize());

    const res = await fetch("chapters.json");
    if (!res.ok) throw new Error("Không tải được chapters.json");
    chapters = await res.json();
    byN = Object.fromEntries(chapters.map((c) => [c.n, c]));

    chapterCountMeta.textContent = `${chapters.length.toLocaleString("vi-VN")} chương`;
    $("jumpInput").max = String(chapters.length);

    const saved = Number(localStorage.getItem(STORAGE_KEY));
    if (Number.isFinite(saved) && byN[saved]) {
      resumeBtn.classList.remove("hidden");
      resumeBtn.onclick = () => openChapter(saved);
    }

    const hashN = parseHash();
    if (hashN && byN[hashN]) {
      await openChapter(hashN, { scrollTop: false });
    }
  }

  $("startBtn").onclick = () => openChapter(1);
  $("homeBtn").onclick = showLanding;
  $("tocBtn").onclick = openToc;
  $("settingsBtn").onclick = () => openSheet(settingsSheet);
  $("closeTocBtn").onclick = closeAllSheets;
  $("closeSettingsBtn").onclick = closeAllSheets;
  sheetBackdrop.onclick = closeAllSheets;

  $("jumpBtn").onclick = () => {
    const n = Number($("jumpInput").value);
    if (byN[n]) openChapter(n);
  };
  $("jumpInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") $("jumpBtn").click();
  });

  $("prevBtn").onclick = () => {
    const idx = chapters.findIndex((c) => c.n === currentN);
    if (idx > 0) openChapter(chapters[idx - 1].n);
  };
  $("nextBtn").onclick = () => {
    const idx = chapters.findIndex((c) => c.n === currentN);
    if (idx >= 0 && idx < chapters.length - 1) openChapter(chapters[idx + 1].n);
  };

  $("fontSlider").addEventListener("input", (e) => {
    setFontSize(Number(e.target.value));
  });

  $("themeDarkBtn").onclick = () => setTheme("dark");
  $("themeLightBtn").onclick = () => setTheme("light");

  const onSearch = (e) => {
    searchQuery = e.target.value;
    $("searchInput").value = searchQuery;
    $("desktopSearchInput").value = searchQuery;
    renderToc();
  };
  $("searchInput").addEventListener("input", onSearch);
  $("desktopSearchInput").addEventListener("input", onSearch);

  bindTocClicks(tocList);
  bindTocClicks(desktopTocList);

  window.addEventListener("hashchange", () => {
    const n = parseHash();
    if (n && byN[n] && n !== currentN) openChapter(n, { scrollTop: false });
    if (!n && currentN !== null) showLanding();
  });

  window.addEventListener("keydown", (e) => {
    if (activeSheet && e.key === "Escape") closeAllSheets();
    if (currentN == null) return;
    if (e.key === "ArrowLeft") $("prevBtn").click();
    if (e.key === "ArrowRight") $("nextBtn").click();
  });

  window.addEventListener("resize", () => {
    syncReadingLayout();
    if (activeSheet === tocSheet && isDesktop()) closeAllSheets();
  });

  setupScrollCollapse();
  setupSheetSwipe(tocSheet);
  setupSheetSwipe(settingsSheet);

  init().catch((err) => {
    chapterCountMeta.textContent = "Lỗi tải mục lục";
    console.error(err);
  });
})();
