// templates/frontend/swipe.js
const API_URL = 'http://localhost:8000/api';

// Функция для перехода на свайпер
function goToSwipe() {
    document.body.innerHTML = `
        <div class="swipe-container">
            <header>
                <div class="container">
                    <div class="header-content">
                        <div class="logo">
                            <img class="logo_img" src="/static/frontend/images/logo.png" alt="Logo">
                            <span>RottenLove</span>
                        </div>
                        <button onclick="goToHome()" class="btn btn-secondary">На главную</button>
                    </div>
                </div>
            </header>

            <div class="swipe-main">
                <h1>BrainRot Dating 🎭</h1>
                <p>Найди своего мэтча в мире мемов и абсурда</p>

                <div id="tinder-container"></div>

                <div class="swipe-buttons">
                    <button class="swipe-btn dislike" onclick="swipe('left')">👎</button>
                    <button class="swipe-btn superlike" onclick="swipe('up')">⭐</button>
                    <button class="swipe-btn like" onclick="swipe('right')">👍</button>
                </div>
            </div>
        </div>
    `;

    loadCharacters();
}

function goToHome() {
    window.location.href = '/';
}

// Загрузка персонажей
async function loadCharacters() {
    try {
        const response = await fetch(`${API_URL}/characters/`);
        const characters = await response.json();
        console.log('Персонажи загружены:', characters);

        // Здесь можно отобразить карточки
        displayCharacter(characters[0]);
    } catch (error) {
        console.error('Ошибка загрузки:', error);
        // Демо данные
        displayDemoCharacter();
    }
}

function displayCharacter(character) {
    const container = document.getElementById('tinder-container');
    container.innerHTML = `
        <div class="tinder-card">
            <div class="card-image">
                <div class="emoji">🎭</div>
            </div>
            <div class="card-content">
                <h2>${character.name}</h2>
                <p>${character.description}</p>
                <div class="iconic-phrase">"${character.iconic_phrase}"</div>
            </div>
        </div>
    `;
}

function displayDemoCharacter() {
    const container = document.getElementById('tinder-container');
    container.innerHTML = `
        <div class="tinder-card">
            <div class="card-image" style="background: linear-gradient(135deg, #a78bfa 0%, #ec4899 100%)">
                <div class="emoji">🎭</div>
            </div>
            <div class="card-content">
                <h2>Тралалело Тралала</h2>
                <p>Абсолютный абсурд, digital-дитя, замена мыслей на «тра-ла-ла».</p>
                <div class="iconic-phrase">"Тра-ла-ла, всё есть loop!"</div>
            </div>
        </div>
    `;
}

function swipe(direction) {
    alert(`Свайп ${direction === 'right' ? '👍 Лайк' : '👎 Дизлайк'}`);
    // Здесь будет реальный свайп
}