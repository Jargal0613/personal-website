const MENU_BUTTON_ID = "menuButton";
const NAV_ID = "siteNav";
const LANG_TOGGLE_ID = "langToggle";
const LIGHTBOX_ID = "lightbox";
const LIGHTBOX_IMAGE_ID = "lightboxImage";
const LIGHTBOX_CLOSE_ID = "lightboxClose";
const MOBILE_BREAKPOINT = 760;

function getMenuElements() {
  return {
    header: document.querySelector(".site-header"),
    button: document.getElementById(MENU_BUTTON_ID),
    nav: document.getElementById(NAV_ID)
  };
}

function setMenuState(isOpen) {
  const { header, button, nav } = getMenuElements();

  if (!button || !nav || !header) {
    return;
  }

  button.setAttribute("aria-expanded", isOpen ? "true" : "false");
  nav.classList.toggle("open", isOpen);
  header.classList.toggle("menu-open-mobile", isOpen);
  document.body.classList.toggle("menu-open", isOpen && window.innerWidth <= MOBILE_BREAKPOINT);
}

function toggleMenu() {
  const { button } = getMenuElements();

  if (!button) {
    return;
  }

  setMenuState(button.getAttribute("aria-expanded") !== "true");
}

function closeMenuOnDesktop() {
  if (window.innerWidth > MOBILE_BREAKPOINT) {
    setMenuState(false);
  }
}

function updateLanguageToggle(language) {
  const toggle = document.getElementById(LANG_TOGGLE_ID);

  if (!toggle) {
    return;
  }

  toggle.innerHTML =
    language === "en"
      ? '<span class="lang-pill active">EN</span><span class="lang-pill">MN</span>'
      : '<span class="lang-pill">EN</span><span class="lang-pill active">MN</span>';
}

function handleLanguageToggle() {
  const nextLanguage = document.documentElement.lang === "en" ? "mn" : "en";

  if (typeof window.switchLanguage === "function") {
    window.switchLanguage(nextLanguage);
  }
}

function applyCurrentYear() {
  document.querySelectorAll("[data-year]").forEach((node) => {
    node.textContent = `© ${new Date().getFullYear()}`;
  });
}

function openLightbox(image) {
  const lightbox = document.getElementById(LIGHTBOX_ID);
  const lightboxImage = document.getElementById(LIGHTBOX_IMAGE_ID);

  if (!lightbox || !lightboxImage) {
    return;
  }

  lightboxImage.src = image.currentSrc || image.src;
  lightboxImage.alt = image.alt;
  lightbox.classList.add("active");
  lightbox.setAttribute("aria-hidden", "false");
  document.body.classList.add("menu-open");
}

function closeLightbox() {
  const lightbox = document.getElementById(LIGHTBOX_ID);

  if (!lightbox) {
    return;
  }

  lightbox.classList.remove("active");
  lightbox.setAttribute("aria-hidden", "true");
  document.body.classList.remove("menu-open");
}

function setupRevealAnimations() {
  const revealNodes = document.querySelectorAll(".reveal");

  if (!("IntersectionObserver" in window)) {
    revealNodes.forEach((node) => node.classList.add("visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.18 }
  );

  revealNodes.forEach((node) => observer.observe(node));
}

function addEventListeners() {
  const { button, nav } = getMenuElements();
  const langToggle = document.getElementById(LANG_TOGGLE_ID);
  const lightbox = document.getElementById(LIGHTBOX_ID);
  const lightboxClose = document.getElementById(LIGHTBOX_CLOSE_ID);

  if (button) {
    button.addEventListener("click", toggleMenu);
  }

  if (nav) {
    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        if (window.innerWidth <= MOBILE_BREAKPOINT) {
          setMenuState(false);
        }
      });
    });
  }

  if (langToggle) {
    langToggle.addEventListener("click", handleLanguageToggle);
  }

  document.querySelectorAll("[data-lightbox]").forEach((image) => {
    image.addEventListener("click", () => openLightbox(image));
  });

  if (lightboxClose) {
    lightboxClose.addEventListener("click", closeLightbox);
  }

  if (lightbox) {
    lightbox.addEventListener("click", (event) => {
      if (event.target === lightbox) {
        closeLightbox();
      }
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeLightbox();
      setMenuState(false);
    }
  });

  window.addEventListener("resize", closeMenuOnDesktop);
  window.updateLanguageToggle = updateLanguageToggle;
}

document.addEventListener("DOMContentLoaded", () => {
  applyCurrentYear();
  addEventListeners();
  setupRevealAnimations();

  if (document.documentElement.lang) {
    updateLanguageToggle(document.documentElement.lang);
  }
});
