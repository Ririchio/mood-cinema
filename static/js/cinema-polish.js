(function () {
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    if (motionQuery.matches) {
        document.documentElement.classList.add("reduced-motion");
        document.querySelectorAll(
            ".catalog-card, .recommendation-card, .hero-card, .mood-hero, .mood-result-hero, .filter-box, .catalog-header, .mood-question"
        ).forEach((element) => {
            element.classList.add("is-visible");
        });

        return;
    }

    const revealTargets = [
        ".catalog-card",
        ".recommendation-card",
        ".hero-card",
        ".mood-hero",
        ".mood-result-hero",
        ".filter-box",
        ".catalog-header",
        ".mood-question",
    ].join(",");

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) {
                return;
            }

            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
        });
    }, {
        threshold: 0.08,
        rootMargin: "0px 0px -24px 0px",
    });

    function observeRevealTargets(scope = document) {
        scope.querySelectorAll(revealTargets).forEach((element, index) => {
            if (element.classList.contains("is-visible")) {
                return;
            }

            element.style.transitionDelay = `${Math.min(index * 14, 90)}ms`;
            observer.observe(element);
        });
    }

    observeRevealTargets();

    let mutationTimer = null;

    const mutationObserver = new MutationObserver(() => {
        if (mutationTimer) {
            return;
        }

        mutationTimer = window.setTimeout(() => {
            observeRevealTargets();
            mutationTimer = null;
        }, 120);
    });

    mutationObserver.observe(document.body, {
        childList: true,
        subtree: true,
    });
})();