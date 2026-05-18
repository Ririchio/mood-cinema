(function () {
    const wizard = document.querySelector("[data-mood-wizard]");

    if (!wizard) {
        return;
    }

    const FIXED_TOTAL_STEPS = 8;

    const questions = Array.from(wizard.querySelectorAll("[data-question]"));
    const nextButton = wizard.querySelector("[data-wizard-next]");
    const submitButton = wizard.querySelector("[data-wizard-submit]");
    const message = wizard.querySelector("[data-wizard-message]");
    const counter = document.querySelector("[data-wizard-counter]");
    const progress = document.querySelector("[data-wizard-progress]");

    let currentIndex = 0;

    function getAnswers() {
        const answers = {};

        questions.forEach((question) => {
            const checked = question.querySelector("input[type='radio']:checked");

            if (checked) {
                answers[checked.name] = checked.value;
            }
        });

        return answers;
    }

    function conditionMatches(question, answers) {
        const raw = question.dataset.showIf;

        if (!raw || raw === "{}") {
            return true;
        }

        let condition = {};

        try {
            condition = JSON.parse(raw);
        } catch (error) {
            return true;
        }

        return Object.entries(condition).every(([field, expected]) => {
            const actual = answers[field];

            if (Array.isArray(expected)) {
                return expected.includes(actual);
            }

            return actual === expected;
        });
    }

    function getVisibleQuestions() {
        const answers = getAnswers();

        return questions.filter((question) => conditionMatches(question, answers));
    }

    function clearHiddenAnswers() {
        const answers = getAnswers();

        questions.forEach((question) => {
            if (conditionMatches(question, answers)) {
                return;
            }

            question.querySelectorAll("input[type='radio']").forEach((input) => {
                input.checked = false;
            });
        });
    }

    function getCurrentQuestion() {
        const visibleQuestions = getVisibleQuestions();

        if (currentIndex >= visibleQuestions.length) {
            currentIndex = visibleQuestions.length - 1;
        }

        if (currentIndex < 0) {
            currentIndex = 0;
        }

        return visibleQuestions[currentIndex];
    }

    function isAnswered(question) {
        return Boolean(question.querySelector("input[type='radio']:checked"));
    }

    function showOnly(button, shouldShow) {
        if (!button) {
            return;
        }

        button.hidden = !shouldShow;
        button.style.display = shouldShow ? "inline-flex" : "none";
    }

    function showMessage() {
        if (!message) {
            return;
        }

        message.hidden = false;
        message.style.display = "block";
    }

    function hideMessage() {
        if (!message) {
            return;
        }

        message.hidden = true;
        message.style.display = "none";
    }

    function getDisplayStep(visibleQuestions, isLastQuestion) {
        if (isLastQuestion) {
            return FIXED_TOTAL_STEPS;
        }

        return Math.min(currentIndex + 1, FIXED_TOTAL_STEPS - 1);
    }

    function updateQuestionNumbers(displayStep) {
        const currentQuestion = getCurrentQuestion();
        const number = currentQuestion.querySelector("[data-question-number]");

        if (number) {
            number.textContent = displayStep;
        }
    }

    function render() {
        clearHiddenAnswers();

        const visibleQuestions = getVisibleQuestions();
        const currentQuestion = getCurrentQuestion();
        const isLastQuestion = currentIndex === visibleQuestions.length - 1;
        const displayStep = getDisplayStep(visibleQuestions, isLastQuestion);

        questions.forEach((question) => {
            const shouldShow = question === currentQuestion;
            question.hidden = !shouldShow;
            question.style.display = shouldShow ? "" : "none";
        });

        updateQuestionNumbers(displayStep);

        if (counter) {
            counter.textContent = `${displayStep} / ${FIXED_TOTAL_STEPS}`;
        }

        if (progress) {
            progress.style.width = `${(displayStep / FIXED_TOTAL_STEPS) * 100}%`;
        }

        showOnly(nextButton, !isLastQuestion);
        showOnly(submitButton, isLastQuestion);

        hideMessage();
    }

    function scrollToWizard() {
        wizard.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    }

    function goNext() {
        const currentQuestion = getCurrentQuestion();

        if (!isAnswered(currentQuestion)) {
            showMessage();
            return;
        }

        currentIndex += 1;
        render();
        scrollToWizard();
    }

    wizard.addEventListener("change", (event) => {
        if (!event.target.matches("input[type='radio']")) {
            return;
        }

        hideMessage();

        const visibleQuestions = getVisibleQuestions();
        const currentQuestion = getCurrentQuestion();
        currentIndex = Math.max(0, visibleQuestions.indexOf(currentQuestion));

        render();
    });

    if (nextButton) {
        nextButton.addEventListener("click", goNext);
    }

    wizard.addEventListener("submit", (event) => {
        const visibleQuestions = getVisibleQuestions();
        const unanswered = visibleQuestions.find((question) => !isAnswered(question));

        if (unanswered) {
            event.preventDefault();
            currentIndex = visibleQuestions.indexOf(unanswered);
            render();
            showMessage();
        }
    });

    render();
})();
