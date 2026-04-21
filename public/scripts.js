/*
 * scripts.js
 *
 * Shared JavaScript utilities and initialization logic used across
 * the personal website. This file is intentionally small: its job is to
 * provide interactive behavior (mobile menu toggling, language toggles, etc.)
 * and wire event listeners rather than embedding script blocks in each HTML
 * page.  The structure follows a professional order: constants, functions,
 * event listeners, and initialization.
 */

/* --------------------------------------------------------------------------
   CONSTANTS
   -------------------------------------------------------------------------- */
const MENU_ID = 'mobileNav'; // default mobile nav id used in most pages
const ALT_MENU_ID = 'list'; // legacy id present in test.html before refactor
const HAMBURGER_ID = 'hamburgerButton';
const CROSS_ID = 'cross';
const LANG_TOGGLE_ID = 'langToggle';
const MOBILE_LANG_SELECTOR = '.mobile-lang-toggle';

/* --------------------------------------------------------------------------
   FUNCTIONS
   -------------------------------------------------------------------------- */

/**
 * Generic helper: toggle the visibility of the mobile navigation menu.
 * It also swaps the hamburger/cross icons and updates aria-expanded.
 *
 * @returns {void}
 */
function toggleMenu() {
  const menu = document.getElementById(MENU_ID) || document.getElementById(ALT_MENU_ID);
  const hamburger = document.getElementById(HAMBURGER_ID);
  const cross = document.getElementById(CROSS_ID);

  if (!menu || !hamburger || !cross) {
    return; // nothing to toggle on this page
  }

  const isShown = menu.classList.toggle('shown');
  hamburger.classList.toggle('hidden');
  cross.classList.toggle('shown');
  hamburger.setAttribute('aria-expanded', isShown ? 'true' : 'false');
}

/**
 * Handler for desktop language toggle button (top corner)
 * swaps languages using the switchLanguage exported by translations.js
 * and prevents default link behavior.
 *
 * @param {Event} event - click event object
 * @returns {void}
 */
function desktopLanguageToggle(event) {
  event.preventDefault();
  const nextLang = document.documentElement.lang === 'en' ? 'mn' : 'en';
  if (typeof switchLanguage === 'function') {
    switchLanguage(nextLang);
  }
}

/**
 * Attach click handlers to elements that trigger the mobile language toggle
 * (the "En | Mn" item inside the mobile nav). Performs a similar action
 * to the desktop toggle above.
 *
 * @param {Event} event - click event object
 * @returns {void}
 */
function mobileLanguageToggle(event) {
  event.preventDefault();
  desktopLanguageToggle(event);
}

/**
 * Open the lightbox modal with the clicked image at full size with true aspect ratio.
 *
 * @param {Event} event - click event object
 * @returns {void}
 */
function openLightbox(event) {
  const img = event.target;
  if (!img.classList.contains('gallery')) return;
  
  const lightbox = document.getElementById('lightbox');
  const lightboxImage = document.getElementById('lightboxImage');
  
  if (lightbox && lightboxImage) {
    lightboxImage.src = img.src;
    lightboxImage.alt = img.alt;
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden'; /* prevent scrolling */
  }
}

/**
 * Close the lightbox modal.
 *
 * @returns {void}
 */
function closeLightbox() {
  const lightbox = document.getElementById('lightbox');
  if (lightbox) {
    lightbox.classList.remove('active');
    document.body.style.overflow = ''; /* restore scrolling */
  }
}

/* --------------------------------------------------------------------------
   EVENT LISTENERS
   -------------------------------------------------------------------------- */

function addEventListeners() {
  const hamburger = document.getElementById(HAMBURGER_ID);
  const cross = document.getElementById(CROSS_ID);
  const desktopLang = document.getElementById(LANG_TOGGLE_ID);
  const mobileLangItems = document.querySelectorAll(MOBILE_LANG_SELECTOR);
  const galleryImages = document.querySelectorAll('img.gallery');
  const lightbox = document.getElementById('lightbox');
  const lightboxClose = document.getElementById('lightboxClose');

  if (hamburger) {
    hamburger.addEventListener('click', toggleMenu);
  }
  if (cross) {
    cross.addEventListener('click', toggleMenu);
  }
  if (desktopLang) {
    desktopLang.addEventListener('click', desktopLanguageToggle);
  }
  if (mobileLangItems.length) {
    mobileLangItems.forEach((el) => el.addEventListener('click', mobileLanguageToggle));
  }
  
  /* lightbox functionality */
  if (galleryImages.length) {
    galleryImages.forEach((img) => {
      img.addEventListener('click', openLightbox);
    });
  }
  if (lightboxClose) {
    lightboxClose.addEventListener('click', closeLightbox);
  }
  if (lightbox) {
    lightbox.addEventListener('click', (event) => {
      if (event.target === lightbox) {
        closeLightbox();
      }
    });
  }
}

/* --------------------------------------------------------------------------
   INITIALIZATION
   -------------------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  addEventListeners();
});
