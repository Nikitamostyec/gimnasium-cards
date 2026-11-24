
(() => {
    "use strict";

    const STORAGE_KEY = "gymnasium16_grades_v2";
    const root = document.querySelector(".grades-page");

    if (!root) return;

    const el = {
        formWrapper: document.getElementById("subject-form-wrapper"),
        form: document.getElementById("subject-form"),
        input: document.getElementById("subject-name"),
        toggle: document.getElementById("toggle-subject-form"),
        cancel: document.getElementById("cancel-subject-form"),
        emptyAdd: document.getElementById("empty-add-subject"),
        empty: document.getElementById("grades-empty"),
        list: document.getElementById("subjects-list"),
        subjectsCount: document.getElementById("subjects-count"),
        overallAverage: document.getElementById("overall-average"),
        overallCount: document.getElementById("overall-count")
    };

    if (Object.values(el).some(item => !item)) {
        console.error("Калькулятор: не найдены необходимые элементы HTML.");
        return;
    }

    let subjects = loadSubjects();

    function createId() {
        return Date.now().toString(36) +
            Math.random().toString(36).slice(2, 9);
    }

    function loadSubjects() {
        try {
            const data = JSON.parse(
                localStorage.getItem(STORAGE_KEY) || "[]"
            );

            if (!Array.isArray(data)) return [];

            return data
                .filter(item => item && typeof item.name === "string")
                .map(item => ({
                    id: String(item.id || createId()),
                    name: item.name.trim().slice(0, 60),
                    grades: Array.isArray(item.grades)
                        ? item.grades.map(Number).filter(grade =>
                            Number.isInteger(grade) &&
                            grade >= 1 && grade <= 10
                        )
                        : [],
                    collapsed: item.collapsed === true
                }))
                .filter(item => item.name);
        } catch (error) {
            console.error("Ошибка загрузки оценок:", error);
            return [];
        }
    }

    function saveSubjects() {
        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify(subjects)
            );
        } catch (error) {
            alert("Не удалось сохранить оценки в браузере.");
            console.error(error);
        }
    }

    function escapeHTML(value) {
        return String(value).replace(/[&<>"']/g, char => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[char]);
    }

    function gradeClass(grade) {
        if (grade <= 4) return "grade-red";
        if (grade <= 7) return "grade-yellow";
        return "grade-green";
    }

    function average(grades) {
        if (!grades.length) return null;

        return grades.reduce((sum, grade) => sum + grade, 0)
            / grades.length;
    }

    function formatAverage(value) {
        if (value === null) return "—";

        return value.toFixed(2).replace(".", ",");
    }

    function openForm() {
        el.formWrapper.hidden = false;
        el.toggle.setAttribute("aria-expanded", "true");
        el.input.focus();
    }

    function closeForm() {
        el.formWrapper.hidden = true;
        el.toggle.setAttribute("aria-expanded", "false");
        el.form.reset();
    }

    function render() {
        const allGrades = subjects.flatMap(subject => subject.grades);
        const totalAverage = average(allGrades);

        el.subjectsCount.textContent =
            `${subjects.length} ${pluralSubjects(subjects.length)}`;

        el.overallCount.textContent = allGrades.length;
        el.overallAverage.textContent = formatAverage(totalAverage);

        el.empty.hidden = subjects.length !== 0;
        el.list.hidden = subjects.length === 0;

        el.list.innerHTML = subjects
            .map(renderSubject)
            .join("");
    }

    function pluralSubjects(count) {
        if (count === 1) return "предмет";
        if (count >= 2 && count <= 4) return "предмета";
        return "предметов";
    }

    function pluralGrades(count) {
        if (count === 1) return "оценка";
        if (count >= 2 && count <= 4) return "оценки";
        return "оценок";
    }

    function renderSubject(subject) {
        const avg = average(subject.grades);

        const history = subject.grades.length
            ? subject.grades.map(grade => `
                <span class="grade-circle ${gradeClass(grade)}"
                      aria-label="Оценка ${grade}">
                    ${grade}
                </span>
            `).join("")
            : `<span class="grades-no-history">Оценок пока нет</span>`;

        const gradeButtons = Array.from(
            { length: 10 },
            (_, index) => {
                const grade = index + 1;

                return `
                    <button type="button"
                        class="grade-circle grade-choice ${gradeClass(grade)}"
                        data-action="add-grade"
                        data-grade="${grade}"
                        data-subject-id="${escapeHTML(subject.id)}"
                        aria-label="Добавить оценку ${grade}"
                        title="Добавить оценку ${grade}">
                        ${grade}
                    </button>
                `;
            }
        ).join("");

        return `
            <article class="grades-subject-card ${subject.collapsed ? "is-collapsed" : ""}"
                     data-subject-id="${escapeHTML(subject.id)}">

                <div class="grades-subject-top">

                    <div class="grades-subject-heading">
                        <button type="button"
                            class="grades-collapse-button"
                            data-action="toggle-collapse"
                            data-subject-id="${escapeHTML(subject.id)}"
                            aria-expanded="${!subject.collapsed}"
                            aria-label="${subject.collapsed ? "Развернуть" : "Свернуть"} предмет">

                            <span class="grades-collapse-arrow">
                                ${subject.collapsed ? "›" : "⌄"}
                            </span>
                        </button>

                        <div class="grades-subject-title-wrap">
                            <h3 class="grades-subject-name">
                                ${escapeHTML(subject.name)}
                            </h3>

                            <div class="grades-subject-meta">
                                ${subject.grades.length}
                                ${pluralGrades(subject.grades.length)}
                            </div>
                        </div>
                    </div>

                    <div class="grades-subject-average">
                        <strong>${formatAverage(avg)}</strong>
                        <span>средний балл</span>
                    </div>
                </div>

                <div class="grades-subject-content"
                     ${subject.collapsed ? "hidden" : ""}>

                    <div class="grades-history-block">
                        <span class="grades-history-label">
                            История оценок
                        </span>

                        <div class="grades-history-list">
                            ${history}
                        </div>
                    </div>

                    <div class="grades-picker-wrap">
                        <span class="grades-picker-label">
                            Добавить оценку
                        </span>

                        <div class="grades-grade-picker">
                            ${gradeButtons}

                            <button type="button"
                                class="grades-picker-action"
                                data-action="undo-grade"
                                data-subject-id="${escapeHTML(subject.id)}"
                                aria-label="Удалить последнюю оценку"
                                title="Удалить последнюю оценку">
                                ↶
                            </button>

                            <button type="button"
                                class="grades-picker-action danger"
                                data-action="clear-grades"
                                data-subject-id="${escapeHTML(subject.id)}"
                                aria-label="Очистить все оценки"
                                title="Очистить все оценки">
                                ×
                            </button>
                        </div>
                    </div>

                    <div class="d-flex justify-content-end mt-2">
                        <button type="button"
                            class="grades-subject-delete"
                            data-action="delete-subject"
                            data-subject-id="${escapeHTML(subject.id)}">
                            Удалить предмет
                        </button>
                    </div>
                </div>
            </article>
        `;
    }

    function addSubject(name) {
        const cleanName = name.trim().replace(/\s+/g, " ");

        if (!cleanName) return;

        const duplicate = subjects.some(subject =>
            subject.name.toLocaleLowerCase("ru") ===
            cleanName.toLocaleLowerCase("ru")
        );

        if (duplicate) {
            alert("Такой предмет уже есть в списке.");
            el.input.focus();
            return;
        }

        subjects.push({
            id: createId(),
            name: cleanName.slice(0, 60),
            grades: [],
            collapsed: false
        });

        saveSubjects();
        render();
        closeForm();
    }

    el.toggle.addEventListener("click", () => {
        if (el.formWrapper.hidden) {
            openForm();
        } else {
            closeForm();
        }
    });

    el.emptyAdd.addEventListener("click", openForm);
    el.cancel.addEventListener("click", closeForm);

    el.form.addEventListener("submit", event => {
        event.preventDefault();
        addSubject(el.input.value);
    });

    el.list.addEventListener("click", event => {
        const button = event.target.closest("[data-action]");

        if (!button) return;

        const action = button.dataset.action;
        const subjectId = button.dataset.subjectId;

        const subject = subjects.find(
            item => item.id === subjectId
        );

        if (!subject) return;

        if (action === "toggle-collapse") {
            subject.collapsed = !subject.collapsed;
            saveSubjects();
            render();
            return;
        }

        if (action === "add-grade") {
            const grade = Number(button.dataset.grade);

            if (!Number.isInteger(grade) || grade < 1 || grade > 10) {
                return;
            }

            subject.grades.push(grade);
        }

        else if (action === "undo-grade") {
            if (!subject.grades.length) return;

            subject.grades.pop();
        }

        else if (action === "clear-grades") {
            if (!subject.grades.length) return;

            if (!confirm(
                `Очистить все оценки по предмету «${subject.name}»?`
            )) return;

            subject.grades = [];
        }

        else if (action === "delete-subject") {
            if (!confirm(
                `Удалить предмет «${subject.name}» вместе со всеми оценками?`
            )) return;

            subjects = subjects.filter(
                item => item.id !== subjectId
            );
        }

        else {
            return;
        }

        saveSubjects();
        render();
    });

    render();
})();
