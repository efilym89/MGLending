import {
  createApplicationMessage,
  createTelegramUrl,
  isResumeFile,
  isResumeUrl,
  normalizePhone
} from './application.mjs?v=20261012-1';

const params = new URLSearchParams(window.location.search);
const isPreview = params.get('preview') === '1';
const isEmbedded = params.get('embed') === '1' && window.self !== window.top;
const menu = document.querySelector('.menu-toggle');
const nav = document.querySelector('.main-nav');
const form = document.querySelector('#rop-form');
const formStatus = document.querySelector('#form-status');
const result = document.querySelector('#application-result');
const messageField = document.querySelector('#application-message');
const telegramLink = document.querySelector('#telegram-application');
const copyStatus = document.querySelector('#copy-status');

function setMenu(open) {
  nav.classList.toggle('is-open', open);
  menu.setAttribute('aria-expanded', String(open));
  menu.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
}

menu.addEventListener('click', () => setMenu(menu.getAttribute('aria-expanded') !== 'true'));
nav.addEventListener('click', event => {
  if (event.target.closest('a')) setMenu(false);
});
document.addEventListener('pointerdown', event => {
  if (!nav.contains(event.target) && !menu.contains(event.target)) setMenu(false);
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && nav.classList.contains('is-open')) {
    setMenu(false);
    menu.focus();
  }
});

function clearFormState(event) {
  if (!event.target.name) return;
  form.querySelectorAll('[aria-invalid="true"]').forEach(field => field.removeAttribute('aria-invalid'));
  formStatus.textContent = '';
  result.hidden = true;
  telegramLink.removeAttribute('href');
  copyStatus.textContent = '';
}

form.addEventListener('input', clearFormState);
form.addEventListener('change', clearFormState);

function focusField(field) {
  if (isEmbedded) sendScroll(field);
  field.focus({ preventScroll: isEmbedded });
}

form.addEventListener('submit', event => {
  event.preventDefault();
  formStatus.textContent = '';
  form.querySelectorAll('[aria-invalid="true"]').forEach(field => field.removeAttribute('aria-invalid'));

  const invalid = [...form.querySelectorAll('[required]')].filter(field => {
    return !field.checkValidity() || (field.type !== 'checkbox' && !field.value.trim());
  });
  const phone = form.elements.namedItem('phone');
  if (!normalizePhone(phone.value)) invalid.push(phone);
  const resumeUrl = form.elements.namedItem('resume_url');
  const resumeInput = form.elements.namedItem('resume_file');
  const resumeFile = resumeInput.files[0];
  let resumeError = '';

  if (resumeUrl.value.trim() && !isResumeUrl(resumeUrl.value)) {
    invalid.push(resumeUrl);
    resumeError = 'Проверьте ссылку на резюме: она должна начинаться с https:// или http://.';
  }
  if (resumeFile && !isResumeFile(resumeFile)) {
    invalid.push(resumeInput);
    resumeError = 'Выберите резюме в формате PDF, DOC или DOCX.';
  }
  if (!resumeUrl.value.trim() && !resumeFile) {
    invalid.push(resumeUrl, resumeInput);
    resumeError = 'Добавьте ссылку на резюме или выберите файл, который приложите в Telegram.';
  }

  if (invalid.length) {
    new Set(invalid).forEach(field => field.setAttribute('aria-invalid', 'true'));
    formStatus.textContent = resumeError || 'Заполните обязательные поля, проверьте телефон с кодом страны и согласие на обработку данных.';
    focusField(invalid[0]);
    return;
  }

  const fields = Object.fromEntries(new FormData(form));
  fields.resume_filename = resumeFile?.name || '';
  const source = Object.fromEntries(['utm_source', 'utm_campaign', 'utm_content'].map(key => [key, params.get(key) || '']));
  const message = createApplicationMessage(fields, source);
  if (message.length > 4096) {
    formStatus.textContent = 'Отклик слишком длинный для готового сообщения. Сократите ответы или ссылку на резюме.';
    return;
  }

  messageField.value = message;
  result.hidden = false;
  copyStatus.textContent = '';
  const resultNote = document.querySelector('#result-note');
  if (isPreview) {
    telegramLink.hidden = true;
    resultNote.textContent = 'Предпросмотр: текст подготовлен, Telegram не открывается. Отклик можно проверить и отредактировать.';
    formStatus.textContent = 'Отклик подготовлен для проверки.';
    return;
  }

  const telegramUrl = createTelegramUrl(message, form.dataset.telegramUsername);
  telegramLink.href = telegramUrl;
  telegramLink.hidden = false;
  resultNote.textContent = resumeFile
    ? `Отправьте текст в Telegram и приложите выбранный файл «${resumeFile.name}». Файл автоматически не передаётся.`
    : 'Отправьте готовый текст в Telegram. Ссылка на резюме уже включена в отклик.';
  formStatus.textContent = 'Отклик подготовлен. Проверьте текст и отправьте сообщение в Telegram.';
  window.open(telegramUrl, '_blank', 'noopener,noreferrer');
});

document.querySelector('#copy-application').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(messageField.value);
    copyStatus.textContent = 'Текст скопирован.';
  } catch {
    messageField.focus();
    messageField.select();
    copyStatus.textContent = 'Выделили текст. Скопируйте его и вставьте в Telegram.';
  }
});

const sticky = document.querySelector('.mobile-apply');
if (!isEmbedded && 'IntersectionObserver' in window) {
  const visible = new Set();
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.isIntersecting) visible.add(entry.target);
      else visible.delete(entry.target);
    }
    sticky.classList.toggle('is-hidden', visible.size > 0);
  }, { rootMargin: '-80px 0px 0px 0px' });
  observer.observe(document.querySelector('.rop-hero-actions'));
  observer.observe(document.querySelector('#application'));
}

// The Tilda wrapper handles scrolling and its own fixed mobile CTA.
let parentOrigin = 'https://annaelle.uz';
try {
  const referrer = new URL(document.referrer);
  const isTildaPreview = referrer.protocol === 'https:' &&
    (referrer.hostname === 'tilda.cc' || referrer.hostname.endsWith('.tilda.cc') || referrer.hostname.endsWith('.tilda.ws'));
  if (['https://annaelle.uz', 'https://www.annaelle.uz', window.location.origin].includes(referrer.origin) || isTildaPreview) {
    parentOrigin = referrer.origin;
  }
} catch {
  // Direct visits have no referrer.
}

function sendScroll(target) {
  window.parent.postMessage({
    type: 'annaelle-rop-scroll',
    targetTop: Math.round(target.getBoundingClientRect().top + window.scrollY)
  }, parentOrigin);
}

if (isEmbedded) {
  document.documentElement.classList.add('is-embedded');
  let layoutFrame = 0;
  let lastLayout = '';
  const absoluteRect = selector => {
    const rect = document.querySelector(selector).getBoundingClientRect();
    return { top: Math.round(rect.top + window.scrollY), height: Math.round(rect.height) };
  };
  const sendLayout = () => {
    layoutFrame = 0;
    const application = absoluteRect('#application');
    const heroActions = absoluteRect('.rop-hero-actions');
    const payload = {
      type: 'annaelle-rop-layout',
      height: Math.ceil(document.body.scrollHeight),
      applicationTop: application.top,
      applicationHeight: application.height,
      heroActionsTop: heroActions.top,
      heroActionsHeight: heroActions.height
    };
    const serialized = JSON.stringify(payload);
    if (serialized === lastLayout) return;
    lastLayout = serialized;
    window.parent.postMessage(payload, parentOrigin);
  };
  const scheduleLayout = () => {
    if (!layoutFrame) layoutFrame = window.requestAnimationFrame(sendLayout);
  };

  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest('a[href^="#"]');
    const target = link && document.getElementById(link.getAttribute('href').slice(1));
    if (!target) return;
    event.preventDefault();
    sendScroll(target);
  });
  window.addEventListener('load', scheduleLayout);
  window.addEventListener('resize', scheduleLayout);
  if ('ResizeObserver' in window) new ResizeObserver(scheduleLayout).observe(document.body);
  document.fonts?.ready.then(scheduleLayout);
  scheduleLayout();
}
