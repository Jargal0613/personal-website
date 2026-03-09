/*
   translations.js
   
   Simple internationalization helper for English/Mongolian toggling.
   The module maintains a dictionary of strings and updates all elements
   marked with `data-i18n`.  The public API is intentionally exposed on
   the global window so that other scripts can call it easily.
*/

/* --------------------------------------------------------------------------
   CONSTANTS
   -------------------------------------------------------------------------- */
const LOCAL_STORAGE_KEY = 'siteSettings';

/* --------------------------------------------------------------------------
   DICTIONARY
   -------------------------------------------------------------------------- */
const translations = {
  en: {
    home: 'Home',
    aboutMe: 'About Me',
    settings: 'Settings',
    jargal: 'Jargal',
    intro: "Hey, I'm Jargal.",
    learning: "I'm currently learning web development",
    requiredContent:
      'I am required to add more content to this page because I have to check what happens when scrolling down',
    developing: 'Developing website is actually interesting and challenging.',
    learned:
      'I learned a lot about HTML and CSS. Main thing is studying coding with full of enjoy.',
    building:
      'Building and developing my own website while learning web development this was a really good idea. I am so happy that come this far.',
    testTitle: 'Test Content',
    testContent: 'This is a test page to experiment something new. I am adding some text because my new changes didn\'t work as expected. test 2 it has been a few hours',
    sophomore:
      'I am a sophomore mechatronics student at GMIT. I started learning coding because I believe this skill is essential for reaching my goals. This website is my first coding project, and I created it to practice, learn, and share my journey.',
    settingsHeader: 'Settings',
    languageLabel: 'Language',
    languageSet: 'Language set to',
    settingsSaved: 'Settings saved',
    settingsReset: 'Settings reset',
    copyright: '© 2025 Jargal. All rights reserved.'
  },
  mn: {
    home: 'Нүүр',
    aboutMe: 'Миний тухай',
    settings: 'Тохиргоо',
    jargal: 'Жаргал',
    intro: 'Сайн байна, би Жаргал.',
    learning: 'Одоо вэб хөгжүүлэлт сурч байна',
    requiredContent:
      'Доош гүйлгэхэд юу болохыг шалгахаар энэ хуудсанд илүү их контент нэмэх шаардлагатай',
    developing:
      'Вэбсайт хөгжүүлэх нь үнэн хэрэгтээ сонирхолтой, хүнд цаг байна.',
    learned:
      'HTML, CSS-ийн талаар маш их суралцсан. Гол зүйл бол кодлогыг бүрэн хайрлаж сурах явдал юм.',
    building:
      'Вэб хөгжүүлэлт сурч байхад өөрийн вэбсайтыг хөгжүүлэх нь үнэхээр сайн санаа байсан. Би энд хүрсэнд маш сайн сэтгэл санаатай.',
    testTitle: 'Туршилтын хуудас',
    testContent: 'Энэ бол шинэ зүйл турших тест хуудас. Шинэ өөрчлөлт ажиллахгүй байгаа тул би зарим текст нэмэж байна. 2 дахь туршилт, хэдэн цаг болж байна.',
    sophomore:
      'Би GMIT-ийн хоёрдугаар курсын мехатроникс оюутан. Би кодлохыг сурахыг эхэлсэн нь энэ ур чадвар нь миний зорилгод хүрэхэд чухал гэж итгэдэг учраас юм. Энэ вэбсайт бол миний анхны кодлох төсөл бөгөөд би үүнийг дадлага хийх, сурах, аялалаа хуваалцах зорилгоор бүтээсэн.',
    settingsHeader: 'Тохиргоо',
    languageLabel: 'Хэл',
    languageSet: 'Хэл тохирууллаа',
    settingsSaved: 'Тохиргоо хадгалагдсан',
    settingsReset: 'Тохиргоо анхны байдалд сэргээгдсэн',
    copyright: '© 2025 Жаргал. Бүх эрх хуулиар хамгаалагдсан.'
  }
};

/* --------------------------------------------------------------------------
   HELPER FUNCTIONS
   -------------------------------------------------------------------------- */

/**
 * Populate all elements tagged with `data-i18n` using the given language.
 *
 * @param {string} language - 'en' or 'mn'
 */
function applyTranslations(language) {
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (translations[language] && translations[language][key]) {
      el.textContent = translations[language][key];
    }
  });
}

/**
 * Update the small language toggle widgets (desktop and mobile).
 *
 * @param {string} language
 */
function updateLanguageToggle(language) {
  const langToggle = document.getElementById('langToggle');
  if (!langToggle) return;
  langToggle.innerHTML =
    language === 'en'
      ? '<span class="text-cyan-400 theme-accent">En</span> | Mn'
      : 'En | <span class="text-cyan-400 theme-accent">Mn</span>';
}

/**
 * Save a language preference and re-render the page.
 *
 * @param {string} lang
 */
function setLanguage(lang) {
  const current = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || '{}');
  localStorage.setItem(
    LOCAL_STORAGE_KEY,
    JSON.stringify({ ...current, language: lang })
  );
  document.documentElement.lang = lang;
  applyTranslations(lang);
  updateLanguageToggle(lang);
}

/* expose for other modules */
window.switchLanguage = setLanguage;
window.applyTranslations = applyTranslations;

/* --------------------------------------------------------------------------
   INITIALIZATION
   -------------------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  const data = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || '{}');
  const lang = data.language || 'en';
  setLanguage(lang);
});