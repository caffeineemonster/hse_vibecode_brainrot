// В начале файла добавь:
const API_URL = window.API_BASE_URL || 'http://localhost:8000/api';

// Пример функции регистрации
async function registerUser(userData) {
    try {
        const response = await axios.post(`${API_URL}/auth/register/`, userData);
        alert('Регистрация успешна! Пройди тест.');
        return response.data;
    } catch (error) {
        console.error('Ошибка регистрации:', error.response?.data);
        alert('Ошибка: ' + (error.response?.data?.email?.[0] || 'Проверь данные'));
        return null;
    }
}

// Пример функции теста
async function submitTest(answers) {
    try {
        const token = localStorage.getItem('access_token');
        const response = await axios.post(`${API_URL}/test/submit/`, {
            answers: answers
        }, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        return response.data;
    } catch (error) {
        console.error('Ошибка теста:', error);
        return null;
    }
}

// frontend/app.js - React компонент свайпера
const { useState, useEffect } = React;
const { motion } = framerMotion;

// Простой свайп-компонент без сложных зависимостей
function TinderCard({ character, onSwipe }) {
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [startPos, setStartPos] = useState({ x: 0, y: 0 });

    const handleMouseDown = (e) => {
        setIsDragging(true);
        setStartPos({ x: e.clientX, y: e.clientY });
    };

    const handleMouseMove = (e) => {
        if (!isDragging) return;
        const deltaX = e.clientX - startPos.x;
        const deltaY = e.clientY - startPos.y;
        setPosition({ x: deltaX, y: deltaY });
    };

    const handleMouseUp = () => {
        if (!isDragging) return;
        setIsDragging(false);

        // Если свайпнули достаточно далеко
        if (Math.abs(position.x) > 100) {
            onSwipe(position.x > 0 ? 'right' : 'left');
        } else {
            // Возвращаем на место
            setPosition({ x: 0, y: 0 });
        }
    };

    useEffect(() => {
        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        }
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging]);

    return React.createElement('div', {
        className: 'card bg-white',
        style: {
            transform: `translate(${position.x}px, ${position.y}px) rotate(${position.x * 0.05}deg)`,
            transition: isDragging ? 'none' : 'transform 0.3s ease-out',
            background: 'linear-gradient(135deg, #a78bfa 0%, #ec4899 100%)',
            overflow: 'hidden'
        },
        onMouseDown: handleMouseDown
    },
        // Содержимое карточки
        React.createElement('div', { className: 'h-2/3 relative' },
            React.createElement('div', {
                className: 'absolute inset-0 flex items-center justify-center text-white text-8xl'
            }, '🎭'),
            position.x > 50 && React.createElement('div', {
                className: 'absolute top-6 left-6 bg-green-500 text-white px-4 py-2 rounded-full text-lg'
            }, '👍 ЛАЙК'),
            position.x < -50 && React.createElement('div', {
                className: 'absolute top-6 right-6 bg-red-500 text-white px-4 py-2 rounded-full text-lg'
            }, '👎 ДИЗЛАЙК')
        ),
        React.createElement('div', { className: 'p-6' },
            React.createElement('h2', { className: 'text-2xl font-bold text-white mb-2' }, character.name),
            React.createElement('p', { className: 'text-white/80 mb-4' }, character.description),
            React.createElement('div', { className: 'border-t border-white/30 pt-4' },
                React.createElement('p', { className: 'text-yellow-300 font-medium' },
                    `"${character.iconic_phrase}"`
                )
            )
        )
    );
}

// Главный компонент приложения
function App() {
    const [characters, setCharacters] = useState([
        {
            id: 1,
            name: 'Тралалело Тралала',
            description: 'Абсолютный абсурд, digital-дитя, замена мыслей на «тра-ла-ла». Цифровой карнавал в плоти.',
            iconic_phrase: 'Тра-ла-ла, всё есть loop!'
        },
        {
            id: 2,
            name: 'Бомбардиро Крокодило',
            description: 'Стратег, тактик, холодная ярость, контроль, милитари-эстетика. План — это всё.',
            iconic_phrase: 'Побеждает не сильнейший, а умнейший.'
        },
        {
            id: 3,
            name: 'Балерина Капучино',
            description: 'Драма, трагедия, театральность, одержимость, эстетика декаданса.',
            iconic_phrase: 'Разбивая фарфор, я танцую.'
        }
    ]);
    const [currentIndex, setCurrentIndex] = useState(0);

    const handleSwipe = (direction) => {
        console.log(`Свайпнули ${direction} персонажа ${characters[currentIndex].name}`);

        // Отправка на бэкенд (заглушка)
        if (direction === 'right') {
            alert(`Лайкнули ${characters[currentIndex].name}! ❤️`);
        } else {
            alert(`Дизлайкнули ${characters[currentIndex].name} 😢`);
        }

        // Следующий персонаж
        if (currentIndex < characters.length - 1) {
            setCurrentIndex(currentIndex + 1);
        } else {
            setCharacters([]);
        }
    };

    return React.createElement('div', { className: 'text-center' },
        React.createElement('h1', {
            className: 'text-4xl font-bold mb-2 text-purple-800'
        }, 'BrainRot Dating 🎭'),
        React.createElement('p', {
            className: 'text-gray-600 mb-8'
        }, 'Найди своего мэтча в мире мемов и абсурда'),

        React.createElement('div', { className: 'relative h-[550px] w-[400px] mx-auto' },
            characters.length > 0 && React.createElement(TinderCard, {
                character: characters[currentIndex],
                onSwipe: handleSwipe
            }),

            characters.length === 0 && React.createElement('div', { className: 'bg-white p-8 rounded-2xl shadow-lg' },
                React.createElement('div', { className: 'text-6xl mb-4' }, '🎉'),
                React.createElement('h2', { className: 'text-2xl font-bold mb-2' }, 'Все персонажи просмотрены!'),
                React.createElement('p', { className: 'text-gray-600 mb-4' }, 'Возвращайся позже за новыми мэтчами'),
                React.createElement('button', {
                    className: 'bg-purple-600 text-white px-6 py-3 rounded-full hover:bg-purple-700',
                    onClick: () => {
                        setCharacters([...characters]);
                        setCurrentIndex(0);
                    }
                }, 'Начать сначала')
            )
        ),

        // Кнопки свайпа
        characters.length > 0 && React.createElement('div', { className: 'flex justify-center mt-8 space-x-6' },
            React.createElement('button', {
                className: 'bg-red-500 text-white w-16 h-16 rounded-full text-2xl hover:bg-red-600',
                onClick: () => handleSwipe('left')
            }, '👎'),
            React.createElement('button', {
                className: 'bg-yellow-500 text-white w-16 h-16 rounded-full text-2xl hover:bg-yellow-600',
                onClick: () => handleSwipe('up')
            }, '⭐'),
            React.createElement('button', {
                className: 'bg-green-500 text-white w-16 h-16 rounded-full text-2xl hover:bg-green-600',
                onClick: () => handleSwipe('right')
            }, '👍')
        )
    );
}

// Рендерим приложение
ReactDOM.render(React.createElement(App), document.getElementById('root'));