const telegramMessage = "Здравствуйте! Хочу узнать подробнее про первый визит с максимальной выгодой";
const telegramUrl = `https://telegram.me/annaellelaser?text=${encodeURIComponent(telegramMessage)}`;

document.querySelectorAll("[data-telegram-message]").forEach((link) => {
  link.setAttribute("href", telegramUrl);
});

const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector(".main-nav");

if (menuButton && navigation) {
  menuButton.addEventListener("click", () => {
    const isOpen = navigation.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
  });

  navigation.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) {
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
