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

document.addEventListener("annaelle:lead:success", (event) => {
  if (!(event instanceof CustomEvent) || typeof window.fbq !== "function") return;

  const eventId = String(event.detail?.eventId || "").trim();
  if (!eventId) return;

  window.fbq("track", "Lead", {}, { eventID: eventId });
});

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
const leadSuccess = document.querySelector("#lead-success");
const leadSuccessKicker = leadSuccess?.querySelector("[data-success-kicker]");
const leadSuccessTitle = leadSuccess?.querySelector("[data-success-title]");
const leadSuccessMessage = leadSuccess?.querySelector("[data-success-message]");
const leadSuccessTelegram = leadSuccess?.querySelector("[data-success-telegram]");
const leadSuccessNote = leadSuccess?.querySelector("[data-success-note]");
const translate = (value) => window.annaelleI18n?.t(value) || value;

const attributionFields = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
  "fbclid",
  "campaign_id",
  "adset_id",
  "ad_id",
  "placement",
];
const attributionStorageKey = "annaelle-lead-attribution";
const lastSubmissionStorageKey = "annaelle-last-lead-submission";
const leadSuccessStorageKey = "annaelle-lead-success";
const leadSuccessLifetime = 30 * 60 * 1000;

function getUzbekPhoneDigits(value) {
  const digits = String(value || "").replace(/\D/g, "");
  const localDigits = digits.startsWith("998") ? digits.slice(3) : digits;
  return localDigits.slice(0, 9);
}

function formatUzbekPhone(value) {
  const digits = getUzbekPhoneDigits(value);
  if (!digits) return "";

  const groups = [digits.slice(0, 2), digits.slice(2, 5), digits.slice(5, 7), digits.slice(7, 9)]
    .filter(Boolean);

  return `+998 ${groups.join(" ")}`;
}

function normalizeUzbekPhone(value) {
  const digits = getUzbekPhoneDigits(value);
  return digits.length === 9 ? `+998${digits}` : "";
}

function readCookie(name) {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));

  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
}

function readStoredAttribution() {
  try {
    const value = window.sessionStorage.getItem(attributionStorageKey);
    return value ? JSON.parse(value) : {};
  } catch {
    return {};
  }
}

function storeAttribution(value) {
  try {
    window.sessionStorage.setItem(attributionStorageKey, JSON.stringify(value));
  } catch {
    // The form still works when storage is unavailable or blocked.
  }
}

function createSubmissionId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }

  return `annaelle-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function setFormStatus(message, state = "") {
  if (!formStatus) return;

  formStatus.textContent = translate(message);
  formStatus.dataset.state = state;
}

function setFormBusy(form, isBusy) {
  const submitButton = form.querySelector('button[type="submit"]');
  const submitLabel = form.querySelector("[data-submit-label]");

  form.setAttribute("aria-busy", String(isBusy));

  if (submitButton instanceof HTMLButtonElement) {
    submitButton.disabled = isBusy;
  }

  if (submitLabel instanceof HTMLElement) {
    if (!submitLabel.dataset.defaultLabel) {
      submitLabel.dataset.defaultLabel = submitLabel.textContent?.trim() || "Получить скидку";
    }

    submitLabel.textContent = isBusy
      ? translate("Отправляем заявку...")
      : translate(submitLabel.dataset.defaultLabel);
  }
}

function getSelectedOptionLabel(fieldName, fallback = "") {
  const field = leadForm?.elements.namedItem(fieldName);

  if (field instanceof HTMLSelectElement) {
    const label = field.selectedOptions[0]?.textContent?.trim();
    if (label && field.value) return label;
  }

  return translate(String(fallback || "").trim());
}

function buildTelegramMessage(payload) {
  const language = document.documentElement.lang || "ru";
  const name = String(payload.name || "").trim();
  const phone = formatUzbekPhone(payload.phone);
  const offer = getSelectedOptionLabel("offer", payload.offer);
  const studio = getSelectedOptionLabel("studio", payload.studio);
  const copy = {
    ru: {
      greeting: "Здравствуйте, команда Annaelle!",
      name: (value) => `Меня зовут ${value}.`,
      phone: (value) => `Телефон для связи: ${value}.`,
      offer: (value) => `Мне интересно предложение «${value}».`,
      noOffer: "Мне нужна консультация по выбору предложения.",
      studio: (value) => `Удобный филиал: ${value}.`,
      submission: (value) => `Код заявки: ${value}`,
    },
    uz: {
      greeting: "Assalomu alaykum, Annaelle jamoasi!",
      name: (value) => `Mening ismim ${value}.`,
      phone: (value) => `Bog'lanish uchun telefon: ${value}.`,
      offer: (value) => `Menga «${value}» taklifi qiziq.`,
      noOffer: "Menga mos taklifni tanlash bo'yicha maslahat kerak.",
      studio: (value) => `Qulay filial: ${value}.`,
      submission: (value) => `Ariza kodi: ${value}`,
    },
    en: {
      greeting: "Hello, Annaelle team!",
      name: (value) => `My name is ${value}.`,
      phone: (value) => `Contact phone: ${value}.`,
      offer: (value) => `I am interested in the “${value}” offer.`,
      noOffer: "I would like help choosing the right offer.",
      studio: (value) => `Preferred location: ${value}.`,
      submission: (value) => `Request ID: ${value}`,
    },
  };
  const template = copy[language] || copy.ru;
  const lines = [template.greeting];

  if (name) lines.push("", template.name(name));
  lines.push(offer ? template.offer(offer) : template.noOffer);
  if (studio) lines.push(template.studio(studio));
  if (phone) lines.push(template.phone(phone));
  if (payload.submission_id) lines.push("", template.submission(payload.submission_id));
  lines.push("#META_LANDING");

  return lines.join("\n");
}

function buildTelegramUrl(payload) {
  const username = String(leadForm?.dataset.telegramUsername || "annaellelaser")
    .trim()
    .replace(/^@/, "");

  return `https://t.me/${encodeURIComponent(username)}?text=${encodeURIComponent(buildTelegramMessage(payload))}`;
}

function storeLeadSuccess(state) {
  try {
    window.sessionStorage.setItem(
      leadSuccessStorageKey,
      JSON.stringify({ ...state, createdAt: Date.now() })
    );
  } catch {
    // The success screen still works when storage is unavailable or blocked.
  }
}

function readLeadSuccess() {
  try {
    const rawValue = window.sessionStorage.getItem(leadSuccessStorageKey);
    if (!rawValue) return null;

    const state = JSON.parse(rawValue);
    if (!state?.createdAt || Date.now() - Number(state.createdAt) > leadSuccessLifetime) {
      window.sessionStorage.removeItem(leadSuccessStorageKey);
      return null;
    }

    return state;
  } catch {
    return null;
  }
}

function showLeadSuccess(options = {}) {
  if (!(leadForm instanceof HTMLFormElement) || !(leadSuccess instanceof HTMLElement)) return;

  const telegramUrl = String(options.telegramUrl || "").trim();

  leadForm.hidden = true;
  leadSuccess.hidden = false;

  if (leadSuccessKicker instanceof HTMLElement) {
    leadSuccessKicker.textContent = translate("Заявка отправлена");
  }

  if (leadSuccessTitle instanceof HTMLElement) {
    leadSuccessTitle.textContent = translate("Спасибо!");
  }

  if (leadSuccessMessage instanceof HTMLElement) {
    leadSuccessMessage.textContent = telegramUrl
      ? translate("Заявка уже сохранена, и администратор получит её в любом случае. Мы также открыли Telegram с готовым сообщением — отправьте его, чтобы продолжить общение в чате.")
      : translate("Администратор Annaelle свяжется с вами в ближайшее время и поможет выбрать удобный филиал, зоны и время визита.");
  }

  if (leadSuccessTelegram instanceof HTMLAnchorElement) {
    leadSuccessTelegram.hidden = !telegramUrl;
    if (telegramUrl) leadSuccessTelegram.href = telegramUrl;
  }

  if (leadSuccessNote instanceof HTMLElement) {
    leadSuccessNote.hidden = !telegramUrl;
  }

  leadSuccess.focus({ preventScroll: true });
  leadSuccess.scrollIntoView({ behavior: "smooth", block: "center" });
}

function openTelegram(telegramUrl) {
  window.setTimeout(() => {
    window.location.assign(telegramUrl);
  }, 650);
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json().catch(() => ({}));
  }

  return response.text().catch(() => "");
}

if (leadForm) {
  const searchParams = new URLSearchParams(window.location.search);
  const storedAttribution = readStoredAttribution();
  const hasCurrentAttribution = attributionFields.some((name) => searchParams.has(name));
  const currentAttribution = hasCurrentAttribution ? {} : { ...storedAttribution };

  attributionFields.forEach((name) => {
    const field = leadForm.elements.namedItem(name);
    const value = searchParams.get(name) || currentAttribution[name] || "";

    if (field instanceof HTMLInputElement && value) {
      field.value = value;
      currentAttribution[name] = value;
    }
  });

  const fbpField = leadForm.elements.namedItem("fbp");
  const fbcField = leadForm.elements.namedItem("fbc");
  const landingUrlField = leadForm.elements.namedItem("landing_url");
  const referrerField = leadForm.elements.namedItem("page_referrer");
  const languageField = leadForm.elements.namedItem("page_language");
  const submissionIdField = leadForm.elements.namedItem("submission_id");
  const formStartedAtField = leadForm.elements.namedItem("form_started_at");
  const phoneField = leadForm.elements.namedItem("phone");
  const fbclid = currentAttribution.fbclid || "";
  const fbp = readCookie("_fbp");
  const fbc = readCookie("_fbc") || (fbclid ? `fb.1.${Date.now()}.${fbclid}` : "");

  function resetLeadForm() {
    leadForm.reset();
    if (submissionIdField instanceof HTMLInputElement) submissionIdField.value = createSubmissionId();
    if (landingUrlField instanceof HTMLInputElement) landingUrlField.value = window.location.href;
    if (referrerField instanceof HTMLInputElement) referrerField.value = document.referrer;
    if (languageField instanceof HTMLInputElement) languageField.value = document.documentElement.lang || "ru";
    if (formStartedAtField instanceof HTMLInputElement) formStartedAtField.value = new Date().toISOString();
    attributionFields.forEach((name) => {
      const field = leadForm.elements.namedItem(name);
      if (field instanceof HTMLInputElement) field.value = currentAttribution[name] || "";
    });
    if (fbpField instanceof HTMLInputElement) fbpField.value = fbp;
    if (fbcField instanceof HTMLInputElement) fbcField.value = fbc;
  }

  if (fbpField instanceof HTMLInputElement) fbpField.value = fbp;
  if (fbcField instanceof HTMLInputElement) fbcField.value = fbc;
  if (landingUrlField instanceof HTMLInputElement) landingUrlField.value = window.location.href;
  if (referrerField instanceof HTMLInputElement) referrerField.value = document.referrer;
  if (languageField instanceof HTMLInputElement) languageField.value = document.documentElement.lang || "ru";
  if (submissionIdField instanceof HTMLInputElement) submissionIdField.value = createSubmissionId();
  if (formStartedAtField instanceof HTMLInputElement) formStartedAtField.value = new Date().toISOString();

  storeAttribution(currentAttribution);

  const restoredSuccess = readLeadSuccess();
  if (restoredSuccess) {
    showLeadSuccess({ telegramUrl: restoredSuccess.telegramUrl || "" });
  }

  if (phoneField instanceof HTMLInputElement) {
    phoneField.addEventListener("focus", () => {
      if (!phoneField.value) phoneField.value = "+998 ";
    });

    phoneField.addEventListener("input", () => {
      phoneField.value = formatUzbekPhone(phoneField.value);
      phoneField.setCustomValidity("");
    });

    phoneField.addEventListener("blur", () => {
      if (!getUzbekPhoneDigits(phoneField.value)) phoneField.value = "";
    });
  }

  leadForm.addEventListener("input", (event) => {
    if (event.target instanceof HTMLElement) {
      event.target.removeAttribute("aria-invalid");
    }

    setFormStatus("");
  });

  leadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (leadForm.getAttribute("aria-busy") === "true") return;

    const requiredFields = Array.from(leadForm.querySelectorAll("[required]"));
    const honeypotField = leadForm.elements.namedItem("website");
    let isValid = true;

    requiredFields.forEach((field) => {
      field.removeAttribute("aria-invalid");

      if (!field.checkValidity()) {
        field.setAttribute("aria-invalid", "true");
        isValid = false;
      }
    });

    if (phoneField instanceof HTMLInputElement) {
      const normalizedPhone = normalizeUzbekPhone(phoneField.value);

      if (!/^\+998\d{9}$/.test(normalizedPhone)) {
        phoneField.setCustomValidity(translate("Введите номер в формате +998 XX XXX XX XX"));
        phoneField.setAttribute("aria-invalid", "true");
        isValid = false;
      } else {
        phoneField.setCustomValidity("");
      }
    }

    if (!isValid) {
      setFormStatus("Пожалуйста, заполните обязательные поля и проверьте номер телефона.", "error");

      const firstInvalidField = leadForm.querySelector('[aria-invalid="true"]');

      if (
        firstInvalidField instanceof HTMLInputElement ||
        firstInvalidField instanceof HTMLSelectElement ||
        firstInvalidField instanceof HTMLTextAreaElement
      ) {
        firstInvalidField.focus();
        firstInvalidField.reportValidity();
      }

      return;
    }

    if (honeypotField instanceof HTMLInputElement && honeypotField.value.trim()) {
      showLeadSuccess();
      return;
    }

    const minimumInterval = Math.max(0, Number(leadForm.dataset.minSubmitInterval) || 10) * 1000;
    let lastSubmissionAt = 0;

    try {
      lastSubmissionAt = Number(window.sessionStorage.getItem(lastSubmissionStorageKey)) || 0;
    } catch {
      lastSubmissionAt = 0;
    }

    if (lastSubmissionAt && Date.now() - lastSubmissionAt < minimumInterval) {
      setFormStatus("Заявка уже отправляется. Пожалуйста, не нажимайте кнопку повторно.", "error");
      return;
    }

    if (languageField instanceof HTMLInputElement) {
      languageField.value = document.documentElement.lang || "ru";
    }

    if (landingUrlField instanceof HTMLInputElement) {
      landingUrlField.value = window.location.href;
    }

    const formData = new FormData(leadForm);
    const payload = Object.fromEntries(formData.entries());
    payload.phone = normalizeUzbekPhone(payload.phone);
    payload.consent = payload.consent === "on";
    payload.submitted_at = new Date().toISOString();
    payload.form_elapsed_ms = formStartedAtField instanceof HTMLInputElement
      ? Math.max(0, Date.now() - Date.parse(formStartedAtField.value || payload.submitted_at))
      : 0;

    const telegramUrl = payload.contact_method === "Telegram"
      ? buildTelegramUrl(payload)
      : "";

    const configuredEndpoint =
      leadForm.dataset.leadEndpoint?.trim() ||
      leadForm.getAttribute("action")?.trim() ||
      String(window.ANNAELLE_LEAD_ENDPOINT || "").trim();

    if (!configuredEndpoint || configuredEndpoint === window.location.href) {
      setFormStatus("Отправка формы пока не подключена. Пожалуйста, свяжитесь с нами напрямую.", "error");
      return;
    }

    try {
      window.sessionStorage.setItem(lastSubmissionStorageKey, String(Date.now()));
    } catch {
      // The busy state still prevents repeated clicks when storage is unavailable.
    }

    setFormBusy(leadForm, true);
    setFormStatus("Отправляем заявку...", "loading");

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);

    try {
      const response = await fetch(configuredEndpoint, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-Submission-Id": String(payload.submission_id || ""),
          "Idempotency-Key": String(payload.submission_id || ""),
        },
        body: JSON.stringify(payload),
        credentials: "omit",
        signal: controller.signal,
      });
      const responseBody = await parseResponse(response);

      if (response.status === 429) {
        throw new Error("RATE_LIMITED");
      }

      if (!response.ok) {
        throw new Error(`Lead endpoint returned ${response.status}`);
      }

      setFormStatus(
        telegramUrl
          ? "Заявка сохранена. Открываем Telegram с готовым сообщением..."
          : "Спасибо! Заявка отправлена. Администратор свяжется с вами.",
        "success"
      );
      leadForm.dispatchEvent(
        new CustomEvent("annaelle:lead:success", {
          bubbles: true,
          detail: {
            eventId: payload.submission_id,
            status: response.status,
          },
        })
      );

      storeLeadSuccess({ telegramUrl });
      resetLeadForm();
      showLeadSuccess({ telegramUrl });

      if (telegramUrl) {
        openTelegram(telegramUrl);
      }

      void responseBody;
    } catch (error) {
      const message =
        error instanceof DOMException && error.name === "AbortError"
          ? "Сервер долго не отвечает. Попробуйте отправить заявку ещё раз."
          : error instanceof Error && error.message === "RATE_LIMITED"
            ? "Слишком много попыток. Подождите немного и отправьте заявку ещё раз."
          : "Не удалось отправить заявку. Попробуйте ещё раз или свяжитесь с нами по телефону.";

      setFormStatus(message, "error");
    } finally {
      window.clearTimeout(timeout);
      setFormBusy(leadForm, false);
    }
  });

}

const privacyPolicy = document.querySelector("#privacy-policy");
if (privacyPolicy instanceof HTMLDetailsElement) {
  document.querySelectorAll('a[href="#privacy-policy"]').forEach((link) => {
    link.addEventListener("click", () => {
      privacyPolicy.open = true;
    });
  });

  if (window.location.hash === "#privacy-policy") {
    privacyPolicy.open = true;
  }
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
