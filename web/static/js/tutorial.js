// web/static/js/tutorial.js

document.addEventListener('DOMContentLoaded', () => {
    // Анимация появления секций при скролле
    const sections = document.querySelectorAll('.tutorial-section');
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const sectionObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    sections.forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        section.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        sectionObserver.observe(section);
    });

    // Интерактивные демонстрации
    const demoButtons = document.querySelectorAll('.demo-button');
    demoButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const demoType = e.target.dataset.demo;
            runDemo(demoType);
        });
    });

    // Подсветка клавиатурных сокращений
    document.querySelectorAll('.keyboard-shortcut').forEach(shortcut => {
        shortcut.setAttribute('role', 'tooltip');
        shortcut.setAttribute('aria-label', shortcut.textContent);
    });
});

function runDemo(type) {
    switch(type) {
        case 'fantasy':
            showFantasyDemo();
            break;
        case 'placement':
            showPlacementDemo();
            break;
        case 'scoring':
            showScoringDemo();
            break;
    }
}

function showFantasyDemo() {
    // Демонстрация механики фантазии
    console.log('Fantasy demo');
}

function showPlacementDemo() {
    // Демонстрация размещения карт
    console.log('Placement demo');
}

function showScoringDemo() {
    // Демонстрация подсчета очков
    console.log('Scoring demo');
}
