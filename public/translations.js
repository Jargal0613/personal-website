/* =================================================================
   TRANSLATIONS MODULE
   Handles internationalization (i18n) for English and Mongolian
   ================================================================= */

/**
 * Translation dictionary
 * Contains all translatable strings for the website
 */
const translations = {
  en: {
    // Navigation
    home: 'Home',
    aboutMe: 'About Me',
    settings: 'Settings',
    
    // Homepage
    jargal: 'Jargal',
    intro: "Hey, I'm Jargal.",
    learning: "I'm currently learning web development",
    requiredContent: 'I am required to add more content to this page because I have to check what happens when scrolling down',
    developing: 'Developing website is actually interesting and challenging.',
    learned: 'I learned a lot about HTML and CSS. Main thing is studying coding with full of enjoy.',
    building: 'Building and developing my own website while learning web development this was a really good idea. I am so happy that come this far.',
    
    // About page
    sophomore: 'I am a sophomore mechatronics student at GMIT. I started learning coding because I believe this skill is essential for reaching my goals. This website is my first coding project, and I created it to practice, learn, and share my journey.',
    
    // Settings page
    settingsHeader: 'Settings',
    languageLabel: 'Language',
    languageSet: 'Language set to',
    settingsSaved: 'Settings saved',
    settingsReset: 'Settings reset',
    
    // Footer
    copyright: '© 2025 Jargal. All rights reserved.'
  },
  
  mn: {
    // Navigation
    home: 'Нүүр',
    aboutMe: 'Миний тухай',
    settings: 'Тохиргоо',
    
    // Homepage
    jargal: 'Жаргал',
    intro: "Сайн байна, би Жаргал.",
    learning: 'Одоо вэб хөгжүүлэлт сурч байна',
    requiredContent: 'Доош гүйлгэхэд юу болохыг шалгахаар энэ хуудсанд илүү их контент нэмэх шаардлагатай',
    developing: 'Вэбсайт хөгжүүлэх нь үнэн хэрэгтээ сонирхолтой, хүнд цаг байна.',
    learned: 'HTML, CSS-ийн талаар маш их суралцсан. Гол зүйл бол кодлогыг бүрэн хайрлаж сурах явдал юм.',
    building: 'Вэб хөгжүүлэлт сурч байхад өөрийн вэбсайтыг хөгжүүлэх нь үнэхээр сайн санаа байсан. Би энд хүрсэнд маш сайн сэтгэл санаатай.',
    
    // About page
    sophomore: 'Би GMIT-ийн хоёрдугаар курсын мехатроникс оюутан. Би кодлохыг сурахыг эхэлсэн нь энэ ур чадвар нь миний зорилгод хүрэхэд чухал гэж итгэдэг учраас юм. Энэ вэбсайт бол миний анхны кодлох төсөл бөгөөд би үүнийг дадлага хийх, сурах, аялалаа хуваалцах зорилгоор бүтээсэн.',
    
    // Settings page
    settingsHeader: 'Тохиргоо',
    languageLabel: 'Хэл',
    languageSet: 'Хэл тохирууллаа',
    settingsSaved: 'Тохиргоо хадгалагдсан',
    settingsReset: 'Тохиргоо анхны байдалд сэргээгдсэн',
    
    // Footer
    copyright: '© 2025 Жаргал. Бүх эрх хуулиар хамгаалагдсан.'
  }
};

/* =================================================================
   TRANSLATION FUNCTIONS
   ================================================================= */

/**
 * Apply translations to all elements with data-i18n attribute
 * @param {string} language - Language code ('en' or 'mn')
 */
function applyTranslations(language) {
  document.querySelectorAll('[data-i18n]').forEach(element => {
    const key = element.getAttribute('data-i18n');
    if (translations[language] && translations[language][key]) {
      element.textContent = translations[language][key];
    }
  });
}

/**
 * Initialize language on page load
 * Loads saved language preference from localStorage
 */
function initializeLanguage() {
  const KEY = 'siteSettings';
  const data = JSON.parse(localStorage.getItem(KEY) || '{}');
  const language = data.language || 'en';
  
  document.documentElement.lang = language;
  applyTranslations(language);
  
  // Update language toggle UI
  updateLanguageToggle(language);
}

/**
 * Update the language toggle display
 * @param {string} language - Current language code
 */
function updateLanguageToggle(language) {
  const langToggle = document.getElementById('langToggle');
  if (langToggle) {
    langToggle.innerHTML = language === 'en' 
      ? '<span class="text-cyan-400 theme-accent">En</span> | Mn' 
      : 'En | <span class="text-cyan-400 theme-accent">Mn</span>';
  }
}

/**
 * Switch language and save preference
 * @param {string} lang - Target language code ('en' or 'mn')
 */
window.switchLanguage = function(lang) {
  const KEY = 'siteSettings';
  const current = JSON.parse(localStorage.getItem(KEY) || '{}');
  const updated = { ...current, language: lang };
  
  localStorage.setItem(KEY, JSON.stringify(updated));
  document.documentElement.lang = lang;
  applyTranslations(lang);
  updateLanguageToggle(lang);
};

/* =================================================================
   INITIALIZATION
   ================================================================= */

// Initialize language when DOM is ready
document.addEventListener('DOMContentLoaded', initializeLanguage);

// Expose functions for use in other scripts
window.applyTranslations = applyTranslations;