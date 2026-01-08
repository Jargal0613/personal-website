// Translation data
const translations = {
  en: {
    home: 'Home',
    aboutMe: 'About Me',
    test: 'Test',
    settings: 'Settings',
    jargal: 'Jargal',
    intro: "Hey, I'm Jargal.",
    learning: 'I\'m currently learning web development',
    requiredContent: 'I am required to add more content to this page because I have to check what happens when scrolling down',
    developing: 'Developing website is actually interesting and challenging.',
    learned: 'I learned a lot about HTML and CSS. Main thing is studying coding with full of enjoy.',
    building: 'Building and developing my own website while learning web development this was a really good idea. I am so happy that come this far.',
    copyright: '© 2025 Jargal. All rights reserved.',
  },
  mn: {
    home: 'Нүүр',
    aboutMe: 'Надаар',
    test: 'Тест',
    settings: 'Тохиргоо',
    jargal: 'Жаргал',
    intro: "Сайн байна, би Жаргал.",
    learning: 'Одоо вэб хөгжүүлэлт сурч байна',
    requiredContent: 'Доош гүйлгэхэд юу болохыг шалгахаар энэ хуудсанд илүү их контент нэмэх шаардлагатай',
    developing: 'Вэбсайт хөгжүүлэх нь үнэн хэрэгтээ сонирхолтой, хүнд цаг байна.',
    learned: 'HTML, CSS-ийн талаар маш их суралцсан. Гол зүйл бол кодлогыг бүрэн хайрлаж сурах явдал юм.',
    building: 'Вэб хөгжүүлэлт сурч байхад өөрийн вэбсайтыг хөгжүүлэх нь үнэхээр сайн санаа байсан. Би энд хүрсэнд маш сайн сэтгэл санаатай.',
    copyright: '© 2025 Жаргал. Бүх эрх хуулиар хамгаалагдсан.',
  }
};

// Load language preference and apply translations
function initializeLanguage() {
  const KEY = 'siteSettings';
  const data = JSON.parse(localStorage.getItem(KEY) || '{}');
  const language = data.language || 'en';
  
  document.documentElement.lang = language;
  applyTranslations(language);
}

// Apply translations to all elements with data-i18n attribute
function applyTranslations(language) {
  document.querySelectorAll('[data-i18n]').forEach(element => {
    const key = element.getAttribute('data-i18n');
    if (translations[language] && translations[language][key]) {
      element.textContent = translations[language][key];
    }
  });
}

// Run on page load
document.addEventListener('DOMContentLoaded', initializeLanguage);
