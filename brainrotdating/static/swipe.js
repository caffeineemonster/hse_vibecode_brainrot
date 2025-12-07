/**
 * BrainRot Dating - Swipe System
 * Tinder-like interface for BrainRot characters
 */

class SwipeSystem {
    constructor() {
        this.currentCharacter = null;
        this.characters = [];
        this.currentIndex = 0;
        this.swipeHistory = [];
        
        // DOM Elements
        this.cardElement = null;
        this.likeButton = null;
        this.dislikeButton = null;
        this.superLikeButton = null;
        this.skipButton = null;
        
        // API endpoints
        this.API_BASE = '/api';
        this.CHARACTERS_URL = `${this.API_BASE}/characters/`;
        this.SWIPE_URL = `${this.API_BASE}/swipes/`;
        
        this.init();
    }

    init() {
        this.loadElements();
        this.loadCharacters();
        this.setupEventListeners();
        this.updateStats();
    }

    loadElements() {
        this.cardElement = document.getElementById('swipeCard');
        this.likeButton = document.getElementById('likeBtn');
        this.dislikeButton = document.getElementById('dislikeBtn');
        this.superLikeButton = document.getElementById('superLikeBtn');
        this.skipButton = document.getElementById('skipBtn');
        this.loadMoreBtn = document.getElementById('loadMoreBtn');
        this.statsElement = document.getElementById('swipeStats');
    }

    async loadCharacters() {
        try {
            const response = await fetch(this.CHARACTERS_URL, {
                headers: {
                }
            });

            if (!response.ok) throw new Error('Failed to load characters');

            this.characters = await response.json();
            
            if (this.characters.length > 0) {
                this.currentIndex = 0;
                this.displayCharacter();
            } else {
                this.showNoCharacters();
            }
        } catch (error) {
            console.error('Error loading characters:', error);
            this.showError();
        }
    }

    displayCharacter() {
        this.currentCharacter = this.characters[this.currentIndex];
        
        if (!this.currentCharacter || !this.cardElement) return;

        const card = this.cardElement;
        
        // Очищаем предыдущие классы анимации
        card.className = 'swipe-card';
        
        // Заполняем карточку данными
        card.innerHTML = `
            <div class="character-image" 
                 style="background-image: url('${this.currentCharacter.image_url || '/static/images/default-character.jpg'}')">
                ${this.currentCharacter.is_popular ? '<span class="popular-badge">🔥 Популярный</span>' : ''}
            </div>
            
            <div class="character-info">
                <div class="character-header">
                    <h2 class="character-name">${this.currentCharacter.name}</h2>
                    <span class="character-age">${this.currentCharacter.age || '??'}</span>
                </div>
                
                <div class="character-category">${this.currentCharacter.category_display || this.currentCharacter.category}</div>
                
                <div class="character-description">
                    <p>${this.currentCharacter.description || 'Загадочный персонаж из BrainRot вселенной.'}</p>
                </div>
                
                <div class="character-traits">
                    ${this.currentCharacter.traits ? this.currentCharacter.traits.slice(0, 5).map(trait => 
                        `<span class="trait-tag">${trait}</span>`
                    ).join('') : ''}
                </div>
                
                <div class="character-stats">
                    <div class="stat">
                        <span class="stat-label">Совместимость:</span>
                        <span class="stat-value">${this.currentCharacter.compatibility || '?'}%</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Популярность:</span>
                        <span class="stat-value">${this.currentCharacter.popularity_score || 0}</span>
                    </div>
                </div>
                
                <div class="character-quote">
                    <i>"${this.currentCharacter.iconic_phrase || 'Будь собой! (Но какой версией?)'}"</i>
                </div>
            </div>
        `;
    }

    async swipe(action) {
        if (!this.currentCharacter) return;
        
        const characterId = this.currentCharacter.id;
        const swipeData = {
            character: characterId,
            swipe_type: action
        };
        
        // Анимация свайпа
        this.animateSwipe(action);
        
        try {
            const response = await fetch(this.SWIPE_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(swipeData)
            });
            
            if (response.ok) {
                this.swipeHistory.push({
                    character: this.currentCharacter.name,
                    action: action,
                    timestamp: new Date()
                });
                
                // Переход к следующему персонажу
                this.nextCharacter();
                this.updateStats();
                
                // Проверка на мэтч (если лайк)
                if (action === 'like' || action === 'super_like') {
                    this.checkForMatch(characterId);
                }
            } else {
                console.error('Swipe failed:', await response.json());
            }
        } catch (error) {
            console.error('Error swiping:', error);
        }
    }

    animateSwipe(action) {
        const card = this.cardElement;
        if (!card) return;
        
        // Добавляем класс анимации
        let animationClass = '';
        if (action === 'like') {
            animationClass = 'swipe-right';
        } else if (action === 'dislike') {
            animationClass = 'swipe-left';
        } else if (action === 'super_like') {
            animationClass = 'swipe-up';
        }
        
        card.classList.add(animationClass);
        
        // Удаляем класс после анимации
        setTimeout(() => {
            card.classList.remove(animationClass);
        }, 500);
    }

    nextCharacter() {
        this.currentIndex++;
        
        if (this.currentIndex >= this.characters.length) {
            // Показать сообщение "больше нет персонажей"
            this.showNoCharacters();
            
            // Показать кнопку загрузки еще
            if (this.loadMoreBtn) {
                this.loadMoreBtn.style.display = 'block';
            }
        } else {
            this.displayCharacter();
        }
    }

    showNoCharacters() {
        this.cardElement.innerHTML = `
            <div class="no-characters">
                <div class="no-characters-icon">😢</div>
                <h3>Персонажи закончились!</h3>
                <p>Вы посмотрели всех доступных персонажей.</p>
                <button id="loadMoreBtn" class="btn-primary">Загрузить еще</button>
                <p class="small-text">Или попробуйте изменить фильтры поиска</p>
            </div>
        `;
        
        // Обновляем ссылку на кнопку
        this.loadMoreBtn = document.getElementById('loadMoreBtn');
        if (this.loadMoreBtn) {
            this.loadMoreBtn.addEventListener('click', () => this.loadCharacters());
        }
    }

    showError() {
        if (this.cardElement) {
            this.cardElement.innerHTML = `
                <div class="error-message">
                    <div class="error-icon">⚠️</div>
                    <h3>Ошибка загрузки</h3>
                    <p>Не удалось загрузить персонажей. Попробуйте позже.</p>
                    <button onclick="location.reload()" class="btn-secondary">Обновить</button>
                </div>
            `;
        }
    }

    async checkForMatch(characterId) {
        try {
            const response = await fetch(`${this.API_BASE}/matches/check/${characterId}/`, {
                headers: {
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.is_match) {
                    this.showMatchNotification(data);
                }
            }
        } catch (error) {
            console.error('Error checking match:', error);
        }
    }

    showMatchNotification(matchData) {
        // Создаем попап мэтча
        const matchPopup = document.createElement('div');
        matchPopup.className = 'match-popup';
        matchPopup.innerHTML = `
            <div class="match-content">
                <div class="match-icon">💖</div>
                <h3>Это МЭТЧ!</h3>
                <p>Вы и ${matchData.character_name} понравились друг другу!</p>
                <div class="match-actions">
                    <button class="btn-primary" onclick="window.location.href='/chat/${matchData.character_id}/'">
                        Написать сообщение
                    </button>
                    <button class="btn-secondary" onclick="this.parentElement.parentElement.parentElement.remove()">
                        Продолжить
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(matchPopup);
        
        // Автоматически скрыть через 5 секунд
        setTimeout(() => {
            if (matchPopup.parentElement) {
                matchPopup.remove();
            }
        }, 5000);
    }

    updateStats() {
        if (!this.statsElement) return;
        
        const total = this.currentIndex + this.swipeHistory.length;
        const likes = this.swipeHistory.filter(s => s.action === 'like').length;
        const superLikes = this.swipeHistory.filter(s => s.action === 'super_like').length;
        const dislikes = this.swipeHistory.filter(s => s.action === 'dislike').length;
        
        this.statsElement.innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-number">${total}</span>
                    <span class="stat-label">Просмотрено</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">${likes}</span>
                    <span class="stat-label">Лайков</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">${superLikes}</span>
                    <span class="stat-label">Суперлайков</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">${dislikes}</span>
                    <span class="stat-label">Дизлайков</span>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        if (this.likeButton) {
            this.likeButton.addEventListener('click', () => this.swipe('like'));
        }
        
        if (this.dislikeButton) {
            this.dislikeButton.addEventListener('click', () => this.swipe('dislike'));
        }
        
        if (this.superLikeButton) {
            this.superLikeButton.addEventListener('click', () => this.swipe('super_like'));
        }
        
        if (this.skipButton) {
            this.skipButton.addEventListener('click', () => this.nextCharacter());
        }
        
        // Добавляем свайпы мышью/тачем
        this.setupTouchEvents();
    }

    setupTouchEvents() {
        if (!this.cardElement) return;
        
        let startX, startY;
        let isDragging = false;
        
        this.cardElement.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isDragging = true;
        });
        
        this.cardElement.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            
            const currentX = e.touches[0].clientX;
            const currentY = e.touches[0].clientY;
            const diffX = currentX - startX;
            const diffY = currentY - startY;
            
            // Поворот карточки при движении
            const rotate = diffX * 0.1;
            this.cardElement.style.transform = `translateX(${diffX}px) rotate(${rotate}deg)`;
        });
        
        this.cardElement.addEventListener('touchend', (e) => {
            if (!isDragging) return;
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const diffX = endX - startX;
            const diffY = endY - startY;
            
            // Сброс позиции
            this.cardElement.style.transform = '';
            
            // Определяем направление свайпа
            if (Math.abs(diffX) > 100) {
                if (diffX > 0) {
                    this.swipe('like'); // Свайп вправо
                } else {
                    this.swipe('dislike'); // Свайп влево
                }
            } else if (diffY < -100) {
                this.swipe('super_like'); // Свайп вверх
            }
            
            isDragging = false;
        });
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Проверка авторизации
});

// Глобальные функции для кнопок
function swipeLike() {
    if (window.swipeSystem) window.swipeSystem.swipe('like');
}

function swipeDislike() {
    if (window.swipeSystem) window.swipeSystem.swipe('dislike');
}

function swipeSuperLike() {
    if (window.swipeSystem) window.swipeSystem.swipe('super_like');
}

function swipeSkip() {
    if (window.swipeSystem) window.swipeSystem.nextCharacter();
}
