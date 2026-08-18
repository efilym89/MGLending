const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector(".main-nav");

if (menuButton && navigation) {
  menuButton.addEventListener("click", () => {
    const isOpen = navigation.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
  });

  navigation.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest("a")) {
      navigation.classList.remove("is-open");
      menuButton.setAttribute("aria-expanded", "false");
    }
  });
}

const reviewCards = Array.from(document.querySelectorAll(".review-card"));
const reviewDots = Array.from(document.querySelectorAll(".dots span"));
const reviewPrev = document.querySelector(".review-prev");
const reviewNext = document.querySelector(".review-next");
let activeReview = 0;

function showReview(index) {
  if (!reviewCards.length) return;

  activeReview = (index + reviewCards.length) % reviewCards.length;

  reviewCards.forEach((card, cardIndex) => {
    const isActive = cardIndex === activeReview;
    card.classList.toggle("is-active", isActive);
    card.setAttribute("aria-hidden", String(!isActive));
  });

  reviewDots.forEach((dot, dotIndex) => {
    dot.classList.toggle("is-active", dotIndex === activeReview);
  });
}

if (reviewCards.length) {
  showReview(0);
  reviewPrev?.addEventListener("click", () => showReview(activeReview - 1));
  reviewNext?.addEventListener("click", () => showReview(activeReview + 1));
  reviewDots.forEach((dot, dotIndex) => {
    dot.addEventListener("click", () => showReview(dotIndex));
  });
}

const leadForm = document.querySelector("#client-lead-form");
const formStatus = document.querySelector("#form-status");
const translate = (value) => window.annaelleI18n?.t(value) || value;

if (leadForm) {
  const searchParams = new URLSearchParams(window.location.search);

  ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"].forEach((name) => {
    const field = leadForm.elements.namedItem(name);
    const value = searchParams.get(name);

    if (field instanceof HTMLInputElement && value) {
      field.value = value;
    }
  });

  leadForm.addEventListener("input", (event) => {
    if (event.target instanceof HTMLElement) {
      event.target.removeAttribute("aria-invalid");
    }

    if (formStatus) {
      formStatus.textContent = "";
    }
  });

  leadForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const requiredFields = Array.from(leadForm.querySelectorAll("[required]"));
    const phoneField = leadForm.elements.namedItem("phone");
    let isValid = true;

    requiredFields.forEach((field) => {
      field.removeAttribute("aria-invalid");

      if (!field.checkValidity()) {
        field.setAttribute("aria-invalid", "true");
        isValid = false;
      }
    });

    if (phoneField instanceof HTMLInputElement) {
      const digits = phoneField.value.replace(/\D/g, "");

      if (digits.length < 9) {
        phoneField.setAttribute("aria-invalid", "true");
        isValid = false;
      }
    }

    if (!isValid) {
      if (formStatus) {
        formStatus.textContent = translate("Пожалуйста, заполните обязательные поля и проверьте номер телефона.");
      }

      leadForm.querySelector('[aria-invalid="true"]')?.focus();
      return;
    }

    if (formStatus) {
      formStatus.textContent = translate("Форма заполнена. Подключение отправки выполним после утверждения лендинга.");
    }
  });
}

const mobileApply = document.querySelector(".mobile-apply");
const leadSection = document.querySelector("#lead-form");

if (mobileApply && leadSection && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    ([entry]) => {
      mobileApply.classList.toggle("is-hidden", entry.isIntersecting);
    },
    { threshold: 0.08 }
  );

  observer.observe(leadSection);
}
