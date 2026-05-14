const moodThemeRoot = document.querySelector("[data-mood-theme-root]");
const moodInputs = document.querySelectorAll("[data-mood-state-input]");

const moodThemeClasses = [
    "mood-theme--neutral",
    "mood-theme--sad",
    "mood-theme--anxious",
    "mood-theme--tired",
    "mood-theme--angry",
    "mood-theme--calm",
    "mood-theme--happy",
    "mood-theme--bored",
    "mood-theme--unknown",
];

function setMoodTheme(value) {
    if (!moodThemeRoot) {
        return;
    }

    moodThemeRoot.classList.remove(...moodThemeClasses);

    const nextTheme = value ? `mood-theme--${value}` : "mood-theme--neutral";

    moodThemeRoot.classList.add(nextTheme);
}

moodInputs.forEach((input) => {
    input.addEventListener("change", () => {
        setMoodTheme(input.value);
    });

    if (input.checked) {
        setMoodTheme(input.value);
    }
});