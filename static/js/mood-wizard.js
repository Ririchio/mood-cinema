(function () {
    const wizard = document.querySelector("[data-mood-wizard]");

    if (!wizard) {
        return;
    }

    const questions = Array.from(wizard.querySelectorAll("[data-question]"));
    const nextButton = wizard.querySelector("[data-wizard-next]");
    const submitButton = wizard.querySelector("[data-wizard-submit]");
    const message = wizard.querySelector("[data-wizard-message]");
    const counter = document.querySelector("[data-wizard-counter]");

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
        if (message) {
            message.hidden = false;
            message.style.display = "block";
        }
    }

    function hideMessage() {
        if (message) {
            message.hidden = true;
            message.style.display = "none";
        }
    }

    function updateQuestionNumbers(visibleQuestions) {
        visibleQuestions.forEach((question, index) => {
            const number = question.querySelector("[data-question-number]");

            if (number) {
                number.textContent = index + 1;
            }
        });
    }

    function render() {
        clearHiddenAnswers();

        const visibleQuestions = getVisibleQuestions();
        const currentQuestion = getCurrentQuestion();

        questions.forEach((question) => {
            const shouldShow = question === currentQuestion;
            question.hidden = !shouldShow;
            question.style.display = shouldShow ? "" : "none";
        });

        updateQuestionNumbers(visibleQuestions);

        if (counter) {
            counter.textContent = `${currentIndex + 1} / ${visibleQuestions.length}`;
        }

        const isLastQuestion = currentIndex === visibleQuestions.length - 1;

        showOnly(nextButton, !isLastQuestion);
        showOnly(submitButton, isLastQuestion);

        hideMessage();
    }

    function scrollToWizard() {
        wizard.scrollIntoView({
            behavior: "smooth",
            block: "start",
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
