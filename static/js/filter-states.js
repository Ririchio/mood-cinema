(function () {
    const chips = document.querySelectorAll("[data-state-chip]");
    const hiddenFields = document.getElementById("filter-state-fields");

    if (!chips.length || !hiddenFields) {
        return;
    }

    const stateOrder = ["neutral", "include", "exclude"];

    function getNextState(currentState) {
        const currentIndex = stateOrder.indexOf(currentState);

        if (currentIndex === -1) {
            return "include";
        }

        return stateOrder[(currentIndex + 1) % stateOrder.length];
    }

    function getInputName(kind, state) {
        if (kind === "genre" && state === "include") {
            return "include_genres";
        }

        if (kind === "genre" && state === "exclude") {
            return "exclude_genres";
        }

        if (kind === "country" && state === "include") {
            return "include_countries";
        }

        if (kind === "country" && state === "exclude") {
            return "exclude_countries";
        }

        return null;
    }

    function updateChipView(chip) {
        const state = chip.dataset.state || "neutral";

        chip.classList.remove("state-chip--neutral", "state-chip--include", "state-chip--exclude");
        chip.classList.add(`state-chip--${state}`);
    }

    function rebuildHiddenInputs() {
        hiddenFields.innerHTML = "";

        chips.forEach(function (chip) {
            const state = chip.dataset.state || "neutral";
            const kind = chip.dataset.kind;
            const id = chip.dataset.id;

            if (state === "neutral") {
                return;
            }

            const inputName = getInputName(kind, state);

            if (!inputName) {
                return;
            }

            const input = document.createElement("input");
            input.type = "hidden";
            input.name = inputName;
            input.value = id;

            hiddenFields.appendChild(input);
        });
    }

    chips.forEach(function (chip) {
        updateChipView(chip);

        chip.addEventListener("click", function () {
            const currentState = chip.dataset.state || "neutral";
            const nextState = getNextState(currentState);

            chip.dataset.state = nextState;

            updateChipView(chip);
            rebuildHiddenInputs();
        });
    });

    rebuildHiddenInputs();
})();