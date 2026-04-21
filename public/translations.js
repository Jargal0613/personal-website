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
    jargal: 'Jargal',
    welcome: "I'm an engineering student at GMIT University with an interest in automation, robotics, and entrepreneurship.",
    learning: "This website showcases my projects, skills, and learning journey. I built this website while learning web development and coding.",
    intro: "My name is Jargal Boldbaatar. I was born on June 13, 2005. I grew up in the countryside, where I spent much of my childhood surrounded by nature, especially during holidays.",
    learn: "2009 - My educational journey began at Kherlen 4th Kindergarten. In 2011, I continued my studies at Kherlen 4th School in Khentii Province.",
    bolovsrolComplex: "2018 - I moved to Baganuur, a district of Ulaanbaatar, where I attended Bolovsrol Complex School and completed my high school education.",
    GMIT: "2023 - I began my undergraduate studies at GMIT University, pursuing a degree in engineering. My interests focus on industrial automation, robotics, and innovation-driven entrepreneurship.",
    commentOnImages:'These images represent where I come from. From my school life in Khentii and Baganuur to the countryside, where I was raised in a nomadic family.',
    copyright: '© 2025 Jargal. All rights reserved.'
  },
  mn: {
    home: 'Нүүр',
    aboutMe: 'Миний тухай',
    jargal: 'Жаргал',
    welcome: "I'm an engineering student at GMIT University with an interest in automation, robotics, and entrepreneurship.",
    learning: "This website showcases my projects, skills, and learning journey. I built this website while learning web development and coding.",
    intro: "My name is Jargal Boldbaatar. I was born on June 13, 2005. I grew up in the countryside, where I spent much of my childhood surrounded by nature, especially during holidays.",
    learn: "2009 - My educational journey began at Kherlen 4th Kindergarten. In 2011, I continued my studies at Kherlen 4th School in Khentii Province.",
    bolovsrolComplex: "2018 - I moved to Baganuur, a district of Ulaanbaatar, where I attended Bolovsrol Complex School and completed my high school education.",
    GMIT: "2023 - I began my undergraduate studies at GMIT University, pursuing a degree in engineering. My interests focus on industrial automation, robotics, and innovation-driven entrepreneurship.",
    commentOnImages:'These images represent where I come from. From my school life in Khentii and Baganuur to the countryside, where I was raised in a nomadic family.',
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