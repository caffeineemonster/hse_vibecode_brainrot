/**
 * BrainRot Test - JavaScript
 */

class BrainRotTest {
    constructor() {
        this.questions = [];
        this.currentQuestionIndex = 0;
        this.answers = {};
        this.totalQuestions = 0;
        
        this.init();
    }
    
    async init() {
        await this.loadQuestions();
        this.setupElements();
        this.renderQuestion();
        this.setupEventListeners();
        this.updateProgress();
    }
    
    async loadQuestions() {
        try {
            // Загружаем вопросы с сервера
            const response = await fetch('/api/test/questions/');
            if (response.ok) {
                const data = await response.json();
                this.questions = data;
                this.totalQuestions = data.length;
            } else {
                // Если API недоступно, используем демо-вопросы
                this.loadDemoQuestions();
            }
        } catch (error) {
            console.log('Используем демо-вопросы');
            this.loadDemoQuestions();
        }
    }
    
    loadDemoQuestions() {
        this.questions = [
            {
                id: 1,
                text: "Как вы обычно реагируете на неожиданную проблему?",
                options: [
                    { id: 1, text: "Смотрю на неё как на шутку и начинаю импровизировать с улыбкой." },
                    { id: 2, text: "Составляю чёткий план, анализирую слабые места и действую методично." },
                    { id: 3, text: "Игнорирую или делаю вид, что её нет, пока она не решится сама." },
                    { id: 4, text: "Превращаю её в личную драму — теперь это сюжет моей жизни." },
                    { id: 5, text: "Делаю один медленный, но невероятно уверенный шаг навстречу." },
                    { id: 6, text: "Начинаю нервно чистить или наводить порядок в чём-то другом." }
                ]
            },
            {
                id: 2,
                text: "Что для вас идеальный способ провести вечер?",
                options: [
                    { id: 1, text: "Смотреть 10-часовые loops или бессмысленные тренды." },
                    { id: 2, text: "Играть в стратегию или смотреть документальный фильм о войне." },
                    { id: 3, text: "Стоять и смотреть в одну точку, сливаясь с интерьером." },
                    { id: 4, text: "Смотреть старый фильм-нуар или слушать оперу в одиночестве." },
                    { id: 5, text: "Медленно идти по пустынному/лесному месту, никуда не торопясь." },
                    { id: 6, text: "Быть незаметным, но всё видеть и слышать в людном месте." }
                ]
            },
            // Добавь остальные вопросы из своего списка...
        ];
        this.totalQuestions = this.questions.length;
    }
    
    setupElements() {
        this.questionText = document.getElementById('questionText');
        this.optionsContainer = document.getElementById('optionsContainer');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.submitBtn = document.getElementById('submitBtn');
        this.currentQuestionEl = document.getElementById('currentQuestion');
        this.totalQuestionsEl = document.getElementById('totalQuestions');
        this.progressPercent = document.getElementById('progressPercent');
        this.progressFill = document.getElementById('progressFill');
        this.counter = document.getElementById('counter');
        
        this.resultContainer = document.getElementById('resultContainer');
        this.resultCharacterName = document.getElementById('resultCharacterName');
        this.resultDescription = document.getElementById('resultDescription');
        this.compatibilityScore = document.getElementById('compatibilityScore');
        this.resultTraits = document.getElementById('resultTraits');
        this.resultCharacterImage = document.getElementById('resultCharacterImage');
        
        this.gotoProfileBtn = document.getElementById('gotoProfileBtn');
        this.gotoSwipeBtn = document.getElementById('gotoSwipeBtn');
    }
    
    renderQuestion() {
        if (this.currentQuestionIndex >= this.questions.length) {
            this.showSubmitButton();
            return;
        }
        
        const question = this.questions[this.currentQuestionIndex];
        this.questionText.textContent = question.text;
        
        // Обновляем счетчик
        this.currentQuestionEl.textContent = this.currentQuestionIndex + 1;
        this.totalQuestionsEl.textContent = this.totalQuestions;
        this.counter.textContent = `${this.currentQuestionIndex + 1}/${this.totalQuestions}`;
        
        // Очищаем контейнер с вариантами
        this.optionsContainer.innerHTML = '';
        
        // Добавляем варианты ответов
        question.options.forEach((option, index) => {
            const optionElement = document.createElement('div');
            optionElement.className = `option ${this.answers[this.currentQuestionIndex] === option.id ? 'selected' : ''}`;
            optionElement.innerHTML = `
                <label>
                    <input type="radio" name="question${this.currentQuestionIndex}" value="${option.id}">
                    <span class="option-text">${option.text}</span>
                </label>
            `;
            
            // Добавляем обработчик выбора
            optionElement.addEventListener('click', () => {
                this.selectOption(option.id);
            });
            
            this.optionsContainer.appendChild(optionElement);
        });
        
        // Обновляем состояние кнопок
        this.updateNavigation();
        this.updateProgress();
    }
    
    selectOption(optionId) {
        // Снимаем выделение со всех вариантов
        document.querySelectorAll('.option').forEach(opt => {
            opt.classList.remove('selected');
        });
        
        // Выделяем выбранный вариант
        const selectedOption = document.querySelector(`input[value="${optionId}"]`);
        if (selectedOption) {
            selectedOption.closest('.option').classList.add('selected');
            selectedOption.checked = true;
        }
        
        // Сохраняем ответ
        this.answers[this.currentQuestionIndex] = optionId;
        
        // Активируем кнопку "Далее"
        this.nextBtn.disabled = false;
    }
    
    updateNavigation() {
        // Кнопка "Назад"
        this.prevBtn.disabled = this.currentQuestionIndex === 0;
        
        // Кнопка "Далее"
        const hasAnswer = this.answers[this.currentQuestionIndex] !== undefined;
        this.nextBtn.disabled = !hasAnswer;
        
        // Показываем/скрываем кнопку отправки
        if (this.currentQuestionIndex === this.totalQuestions - 1 && hasAnswer) {
            this.submitBtn.style.display = 'block';
        } else {
            this.submitBtn.style.display = 'none';
        }
    }
    
    updateProgress() {
        const progress = ((this.currentQuestionIndex + 1) / this.totalQuestions) * 100;
        this.progressFill.style.width = `${progress}%`;
        this.progressPercent.textContent = `${Math.round(progress)}%`;
    }
    
    nextQuestion() {
        if (this.currentQuestionIndex < this.totalQuestions - 1) {
            this.currentQuestionIndex++;
            this.renderQuestion();
        }
    }
    
    prevQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.renderQuestion();
        }
    }
    
    showSubmitButton() {
        document.querySelector('.question-container').style.display = 'none';
        document.querySelector('.test-navigation').style.display = 'none';
        this.submitBtn.style.display = 'block';
    }
    
    async submitTest() {
        if (Object.keys(this.answers).length < this.totalQuestions) {
            alert('Пожалуйста, ответьте на все вопросы перед отправкой.');
            return;
        }
        
        // Показываем загрузку
        this.submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Анализируем ответы...';
        this.submitBtn.disabled = true;
        
        try {
            // Отправляем ответы на сервер
            const response = await fetch('/api/test/submit/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    answers: this.answers,
                    test_type: 'brainrot'
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showResult(result);
            } else {
                // Если API недоступно, показываем демо-результат
                this.showDemoResult();
            }
        } catch (error) {
            console.error('Error submitting test:', error);
            this.showDemoResult();
        }
    }
    
    showResult(resultData) {
        // Скрываем элементы теста
        document.querySelector('.question-container').style.display = 'none';
        document.querySelector('.test-navigation').style.display = 'none';
        this.submitBtn.style.display = 'none';
        document.querySelector('.instructions').style.display = 'none';
        
        // Показываем результат
        const result = resultData.result || resultData;
        
        this.resultCharacterName.textContent = result.character?.name || "Загадочный персонаж";
        this.resultDescription.textContent = result.character?.description || "Твой уникальный BrainRot персонаж!";
        this.compatibilityScore.textContent = result.compatibility || "85%";
        
        // Добавляем черты персонажа
        if (result.character?.traits) {
            this.resultTraits.innerHTML = result.character.traits.map(trait => 
                `<span class="trait-badge">${trait}</span>`
            ).join('');
        }
        
        // Добавляем изображение персонажа
        if (result.character?.image_url) {
            this.resultCharacterImage.innerHTML = `<img src="${result.character.image_url}" alt="${result.character.name}">`;
        } else {
            // Используем иконку по умолчанию
            const icons = ['🧠', '🎭', '👑', '🌟', '💫', '🎪'];
            const randomIcon = icons[Math.floor(Math.random() * icons.length)];
            this.resultCharacterImage.innerHTML = `<div style="font-size: 5rem;">${randomIcon}</div>`;
        }
        
        // Показываем контейнер с результатом
        this.resultContainer.style.display = 'block';
        
        // Добавляем обработчики для кнопок
        this.gotoProfileBtn.addEventListener('click', () => {
            window.location.href = '/profile/';
        });
        
        this.gotoSwipeBtn.addEventListener('click', () => {
            window.location.href = '/swipe/';
        });
        
        // Прокручиваем к результату
        this.resultContainer.scrollIntoView({ behavior: 'smooth' });
    }
    
    showDemoResult() {
        const demoResult = {
            character: {
                name: "Digital Jester",
                description: "Мастер абсурда и цифрового карнавала. Ты превращаешь всё в шутку, даже когда мир вокруг серьёзен. Твоя суперсила — видеть смешное в самом безнадёжном.",
                traits: ["Абсурд", "Импровизация", "Цифровой шутник"],
                image_url: null
            },
            compatibility: "92%",
            message: "Демо-результат. Войдите в систему для прохождения реального теста."
        };
        
        this.showResult(demoResult);
    }
    
    setupEventListeners() {
        // Кнопки навигации
        this.nextBtn.addEventListener('click', () => {
            if (this.currentQuestionIndex < this.totalQuestions - 1) {
                this.nextQuestion();
            }
        });
        
        this.prevBtn.addEventListener('click', () => {
            this.prevQuestion();
        });
        
        // Кнопка отправки
        this.submitBtn.addEventListener('click', () => {
            this.submitTest();
        });
        
        // Управление с клавиатуры
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight' && !this.nextBtn.disabled) {
                this.nextQuestion();
            } else if (e.key === 'ArrowLeft' && !this.prevBtn.disabled) {
                this.prevQuestion();
            } else if (e.key === 'Enter' && this.submitBtn.style.display === 'block') {
                this.submitTest();
            }
        });
    }
}

// Инициализация теста при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.brainRotTest = new BrainRotTest();
});
