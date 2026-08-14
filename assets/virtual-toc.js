(() => {
  "use strict";

  const DEFAULT_OVERSCAN = 12;

  function measureTocItemHeight() {
    const probe = document.createElement("button");
    probe.type = "button";
    probe.className = "toc-item";
    probe.innerHTML =
      '<span class="toc-item__title">Chương 9999: Tiêu đề mẫu cho mục lục</span>' +
      '<span class="toc-item__date">01/01/2026, 00:00</span>';
    probe.style.cssText =
      "position:fixed;left:-9999px;top:0;visibility:hidden;pointer-events:none;width:280px";
    document.body.appendChild(probe);
    const height = probe.offsetHeight;
    probe.remove();
    return height || 72;
  }

  function createVirtualTocList(container, { onSelect, escapeHtml, formatUpdatedAt, overscan = DEFAULT_OVERSCAN } = {}) {
    let items = [];
    let currentN = null;
    let itemHeight = measureTocItemHeight();
    let rafId = 0;

    container.classList.add("toc-virtual");
    container.innerHTML =
      '<div class="toc-virtual__track" aria-hidden="true"></div>' +
      '<div class="toc-virtual__items" role="list"></div>';

    const track = container.querySelector(".toc-virtual__track");
    const itemsEl = container.querySelector(".toc-virtual__items");

    function render() {
      if (!items.length) {
        track.style.height = "0";
        itemsEl.style.transform = "";
        itemsEl.innerHTML = '<div class="toc-empty">Không có kết quả.</div>';
        return;
      }

      const scrollTop = container.scrollTop;
      const viewHeight = container.clientHeight || 0;
      let start = Math.floor(scrollTop / itemHeight) - overscan;
      let end = Math.ceil((scrollTop + viewHeight) / itemHeight) + overscan;
      start = Math.max(0, start);
      end = Math.min(items.length, end);

      track.style.height = `${items.length * itemHeight}px`;
      itemsEl.style.transform = `translate3d(0, ${start * itemHeight}px, 0)`;
      itemsEl.innerHTML = items
        .slice(start, end)
        .map(
          (chapter) => `
        <button type="button" class="toc-item${chapter.n === currentN ? " active" : ""}" data-n="${chapter.n}" role="listitem">
          <span class="toc-item__title">${escapeHtml(chapter.title)}</span>
          ${
            chapter.updated_at
              ? `<span class="toc-item__date">${escapeHtml(formatUpdatedAt(chapter.updated_at))}</span>`
              : ""
          }
        </button>`
        )
        .join("");
    }

    function scheduleRender() {
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        rafId = 0;
        render();
      });
    }

    function scrollToIndex(index, { smooth = false, center = true } = {}) {
      if (index < 0 || index >= items.length) return;
      const top = index * itemHeight;
      let nextTop = top;
      if (center) {
        const viewHeight = container.clientHeight || 0;
        nextTop = Math.max(0, top - viewHeight / 2 + itemHeight / 2);
      }
      container.scrollTo({ top: nextTop, behavior: smooth ? "smooth" : "auto" });
      scheduleRender();
    }

    container.addEventListener(
      "scroll",
      () => {
        scheduleRender();
      },
      { passive: true }
    );

    container.addEventListener("click", (event) => {
      const button = event.target.closest("[data-n]");
      if (!button || !onSelect) return;
      onSelect(Number(button.dataset.n));
    });

    const resizeObserver = new ResizeObserver(() => {
      const nextHeight = measureTocItemHeight();
      if (nextHeight !== itemHeight) {
        itemHeight = nextHeight;
      }
      scheduleRender();
    });
    resizeObserver.observe(container);

    return {
      setItems(nextItems, { scrollToN = null, scrollToTop = false } = {}) {
        items = nextItems;
        if (!items.length) {
          render();
          return;
        }
        if (scrollToTop) {
          container.scrollTop = 0;
        } else if (scrollToN != null) {
          const index = items.findIndex((chapter) => chapter.n === scrollToN);
          if (index >= 0) {
            scrollToIndex(index, { smooth: false, center: true });
            return;
          }
        }
        scheduleRender();
      },
      setCurrentN(nextN) {
        currentN = nextN;
        scheduleRender();
      },
      scrollToN(n, smooth = false) {
        const index = items.findIndex((chapter) => chapter.n === n);
        if (index >= 0) scrollToIndex(index, { smooth, center: true });
      },
      scrollToTop() {
        container.scrollTop = 0;
        scheduleRender();
      },
      destroy() {
        resizeObserver.disconnect();
        if (rafId) cancelAnimationFrame(rafId);
      },
    };
  }

  window.createVirtualTocList = createVirtualTocList;
})();
