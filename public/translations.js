// Translation data

// Inject theme styles immediately before anything else
(function() {
  ensureThemeStyles();
  const KEY = 'siteSettings';
  const data = JSON.parse(localStorage.getItem(KEY) || '{}');
  if (data.theme) {
    applyTheme(data.theme);
  }
})();


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
    test: 'Туршилт',
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
// Load language preference and apply translations
function initializeLanguage() {
  const KEY = 'siteSettings';
  const data = JSON.parse(localStorage.getItem(KEY) || '{}');
  const language = data.language || 'en';
  
  document.documentElement.lang = language;
  applyTranslations(language);
  
  // Apply saved theme preference if present
  // Use requestAnimationFrame to ensure DOM is ready
  if (data.theme) {
    requestAnimationFrame(() => {
      applyTheme(data.theme);
    });
  } else {
    // Apply default theme if none saved
    requestAnimationFrame(() => {
      applyTheme('cyan');
    });
  }
}
// Apply a named theme by setting CSS variables used for gradients.
function applyTheme(name) {
  const themes = {
    cyan: { colors: ['#06b6d4', '#8b5cf6', '#ec4899'], bg: '#0a1f24' },
    purple: { colors: ['#7c3aed', '#6d28d9', '#a78bfa'], bg: '#1f0a2e' },
    green: { colors: ['#10b981', '#34d399', '#86efac'], bg: '#0a1f15' },
    orange: { colors: ['#f97316', '#fb923c', '#fca5a5'], bg: '#2a1810' }
  };
  const theme = themes[name] || themes['cyan'];
  const colors = theme.colors;
  const root = document.documentElement;
  root.style.setProperty('--theme-from', colors[0]);
  root.style.setProperty('--theme-via', colors[1]);
  root.style.setProperty('--theme-to', colors[2]);
  // additional accent vars
  root.style.setProperty('--accent', colors[0]);
  root.style.setProperty('--accent-2', colors[1]);
  root.style.setProperty('--accent-3', colors[2]);
  // 20% alpha for shadow using 8-digit hex
  root.style.setProperty('--accent-shadow', colors[2] + '33');
  root.style.setProperty('--border', colors[1]);
  root.style.setProperty('--bg-theme', theme.bg);
  ensureThemeStyles();
}

function ensureThemeStyles() {
  if (document.getElementById('theme-vars-styles')) return;
  const css = `
    :root { --bg-theme: #000; }
    body { background-color: var(--bg-theme) !important; transition: background-color 0.3s ease; }
    .theme-accent { color: var(--accent) !important; }
    .theme-bg-accent { background-color: var(--accent) !important; }
    .theme-border { border-color: var(--border) !important; }
    .theme-shadow { box-shadow: 0 20px 40px var(--accent-shadow) !important; }
    nav.mobileNav a:hover { color: var(--accent) !important; }
    .hamburgerButton, .cross { color: var(--accent) !important; }
    .hamburgerButton:hover, .cross:hover { background-color: var(--accent) !important; color: black !important; }
    header.theme-border { border-bottom: 1px solid var(--border) !important; }
    footer { border-top-color: var(--border) !important; }
    .status-item:hover { border-color: var(--accent) !important; }
    /* Responsive: hide header lang toggle on small screens and show mobile toggle inside nav */
    #langToggle { display: inline-flex; }
    .mobile-lang-toggle { display: none; }
    @media (max-width: 767px) {
      #langToggle { display: none !important; }
      /* show mobile toggle only when mobile nav is opened */
      nav.mobileNav.shown .mobile-lang-toggle { display: block !important; padding: 12px 18px; }
      nav.mobileNav { padding-top: 3.5rem; }
    }
    /* Ensure mobile-only toggle is hidden on larger screens even if nav links are forced visible */
    @media (min-width: 768px) {
      nav.mobileNav a.mobile-lang-toggle { display: none !important; }
    }
  `;
  const el = document.createElement('style');
  el.id = 'theme-vars-styles';
  el.appendChild(document.createTextNode(css));
  document.head.appendChild(el);
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

// Helper function to switch language and save preference
window.switchLanguage = function(lang) {
  const KEY = 'siteSettings';
  const current = JSON.parse(localStorage.getItem(KEY) || '{}');
  const updated = { ...current, language: lang };
  localStorage.setItem(KEY, JSON.stringify(updated));
  document.documentElement.lang = lang;
  applyTranslations(lang);
  // Update lang toggle UI if it exists
  const langToggle = document.getElementById('langToggle');
  if (langToggle) {
    langToggle.innerHTML = lang === 'en' 
      ? '<span class="text-cyan-400">En</span> | Mn' 
      : 'En | <span class="text-cyan-400">Mn</span>';
  }
};
