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
    sophomore: 'I am a sophomore mechatronics student at GMIT. I started learning coding because I believe this skill is essential for reaching my goals. This website is my first coding project, and I created it to practice, learn, and share my journey.',
    settingsHeader: 'Settings',
    enableDarkMode: 'Enable dark mode',
    languageLabel: 'Language',
    save: 'Save',
    reset: 'Reset',
    darkModeEnabled: 'Dark mode enabled',
    darkModeDisabled: 'Dark mode disabled',
    languageSet: 'Language set to',
    settingsSaved: 'Settings saved',
    settingsReset: 'Settings reset',
    testTitle: 'Test Content',
    testContent: "This is a test page to experiment something new. I am adding some text because my new changes didn't work as expected."
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
    sophomore: 'Би GMIT-ийн хоёрдугаар курсын мехатроникс оюутан. Би кодлохыг сурахыг эхэлсэн нь энэ ур чадвар нь миний зорилгод хүрэхэд чухал гэж итгэдэг учраас юм. Энэ вэбсайт бол миний анхны кодлох төсөл бөгөөд би үүнийг дадлага хийх, сурах, аялалаа хуваалцах зорилгоор бүтээсэн.',
    settingsHeader: 'Тохиргоо',
    enableDarkMode: 'Харанхуй горимыг идэвхжүүлэх',
    languageLabel: 'Хэл',
    save: 'Хадгалах',
    reset: 'Сэргээх',
    darkModeEnabled: 'Харанхуй горим идэвхжлээ',
    darkModeDisabled: 'Харанхуй горимын идэвхжил цуцлагдлаа',
    languageSet: 'Хэл тохирууллаа',
    settingsSaved: 'Тохиргоо хадгалагдсан',
    settingsReset: 'Тохиргоо анхны байдалд сэргээгдсэн',
    testTitle: 'Туршилтын агуулга',
    testContent: 'Энэ нь шинэ зүйлс турших туршилтын хуудас юм. Шинэ өөрчлөлтүүдээ ажиллахгүй байсан болохоор хэдэн мөр текст нэмлээ.'
  }
};

// Load language preference and apply translations
function initializeLanguage() {
  const KEY = 'siteSettings';
  const data = JSON.parse(localStorage.getItem(KEY) || '{}');
  const language = data.language || 'en';
  
  document.documentElement.lang = language;
  applyTranslations(language);
  // apply saved theme preference if present
  if (data.theme) applyTheme(data.theme);
}

// Apply a named theme by setting CSS variables used for gradients.
function applyTheme(name) {
  const themes = {
    cyan: ['#06b6d4', '#8b5cf6', '#ec4899'],
    purple: ['#7c3aed', '#6d28d9', '#a78bfa'],
    green: ['#10b981', '#34d399', '#86efac'],
    orange: ['#f97316', '#fb923c', '#fca5a5']
  };
  const colors = themes[name] || themes['cyan'];
  const root = document.documentElement;
  root.style.setProperty('--theme-from', colors[0]);
  root.style.setProperty('--theme-via', colors[1]);
  root.style.setProperty('--theme-to', colors[2]);
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

// expose for other scripts
window.applyTranslations = applyTranslations;
window.applyTheme = applyTheme;
