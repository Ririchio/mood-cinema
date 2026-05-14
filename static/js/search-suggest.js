(function () {
    const root = document.querySelector("[data-suggest-root]");
    const input = document.querySelector("[data-suggest-input]");
    const panel = document.querySelector("[data-suggest-panel]");

    if (!root || !input || !panel) {
        return;
    }

    let timer = null;
    let controller = null;

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function closePanel() {
        panel.innerHTML = "";
        panel.classList.remove("suggest-panel--open");
    }

    function renderItems(items) {
        if (!items.length) {
            panel.innerHTML = `
                <div class="suggest-empty">
                    Ничего не найдено
                </div>
            `;
            panel.classList.add("suggest-panel--open");
            return;
        }

        panel.innerHTML = items.map(function (item) {
            const title = escapeHtml(item.title);
            const originalTitle = item.original_title ? escapeHtml(item.original_title) : "";
            const year = item.year ? escapeHtml(item.year) : "—";
            const type = escapeHtml(item.type);
            const poster = escapeHtml(item.poster_url);
            const url = escapeHtml(item.url);

            return `
                <a href="${url}" class="suggest-item">
                    <img src="${poster}" alt="${title}" class="suggest-item__poster" loading="lazy">
                    <span class="suggest-item__body">
                        <strong>${title}</strong>
                        ${originalTitle && originalTitle !== title ? `<small>${originalTitle}</small>` : ""}
                        <em>${type} · ${year}</em>
                    </span>
                </a>
            `;
        }).join("");

        panel.classList.add("suggest-panel--open");
    }

    async function loadSuggestions(query) {
        if (controller) {
            controller.abort();
        }

        controller = new AbortController();

        const url = new URL("/api/suggest", window.location.origin);
        url.searchParams.set("q", query);

        const response = await fetch(url.toString(), {
            signal: controller.signal,
            headers: {
                "X-Requested-With": "fetch",
            },
        });

        if (!response.ok) {
            throw new Error("Ошибка поиска");
        }

        return response.json();
    }

    input.addEventListener("input", function () {
        const query = input.value.trim();

        clearTimeout(timer);

        if (query.length < 2) {
            closePanel();
            return;
        }

        timer = setTimeout(async function () {
            try {
                panel.innerHTML = `<div class="suggest-empty">Ищем...</div>`;
                panel.classList.add("suggest-panel--open");

                const items = await loadSuggestions(query);
                renderItems(items);
            } catch (error) {
                if (error.name === "AbortError") {
                    return;
                }

                panel.innerHTML = `<div class="suggest-empty">Не удалось загрузить подсказки</div>`;
                panel.classList.add("suggest-panel--open");
            }
        }, 250);
    });

    document.addEventListener("click", function (event) {
        if (!root.contains(event.target)) {
            closePanel();
        }
    });

    input.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closePanel();
            input.blur();
        }
    });
})();