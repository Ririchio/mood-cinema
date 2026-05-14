(function () {
    const grid = document.getElementById("catalog-grid");
    const panel = document.getElementById("infinite-scroll-panel");
    const status = document.getElementById("infinite-scroll-status");

    if (!grid || !panel || !status) {
        return;
    }

    let hasNext = panel.dataset.hasNext === "1";
    let nextPage = Number(panel.dataset.nextPage || 0);
    let isLoading = false;

    function buildApiUrl(page) {
        const url = new URL(window.location.href);

        url.pathname = "/api/movies";
        url.searchParams.set("page", String(page));

        return url.toString();
    }

    async function loadNextPage() {
        if (!hasNext || isLoading || !nextPage) {
            return;
        }

        isLoading = true;
        panel.classList.add("infinite-panel--loading");
        status.textContent = "Загружаем ещё фильмы и сериалы...";

        try {
            const response = await fetch(buildApiUrl(nextPage), {
                headers: {
                    "X-Requested-With": "fetch",
                },
            });

            if (!response.ok) {
                throw new Error("Ошибка загрузки");
            }

            const data = await response.json();

            if (data.html && data.html.trim() !== "") {
                grid.insertAdjacentHTML("beforeend", data.html);
            }

            hasNext = Boolean(data.has_next);
            nextPage = data.next_page || 0;

            panel.dataset.hasNext = hasNext ? "1" : "0";
            panel.dataset.nextPage = nextPage ? String(nextPage) : "";

            if (hasNext) {
                status.textContent = "Прокрути ниже — подгрузим ещё фильмы и сериалы";
            } else {
                status.textContent = "Это все найденные фильмы и сериалы";
                observer.disconnect();
            }
        } catch (error) {
            status.textContent = "Не удалось подгрузить новые карточки. Обнови страницу и попробуй ещё раз.";
        } finally {
            isLoading = false;
            panel.classList.remove("infinite-panel--loading");
        }
    }

    const observer = new IntersectionObserver(
        function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    loadNextPage();
                }
            });
        },
        {
            root: null,
            rootMargin: "700px 0px",
            threshold: 0,
        }
    );

    if (hasNext) {
        observer.observe(panel);
    } else {
        status.textContent = "Это все найденные фильмы и сериалы";
    }
})();