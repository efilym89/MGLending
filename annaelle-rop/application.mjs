export const APPLICATION_TEXT_LIMIT = 700;

export function normalizePhone(value) {
  const input = String(value || '').trim();
  if (!/^\+?[\d\s().-]+$/.test(input)) return '';
  const digits = input.replace(/\D/g, '');
  return /^[1-9]\d{8,14}$/.test(digits) ? `+${digits}` : '';
}

export function isResumeUrl(value) {
  if (!String(value || '').trim()) return false;
  try {
    const url = new URL(String(value).trim());
    return ['https:', 'http:'].includes(url.protocol) && Boolean(url.hostname);
  } catch {
    return false;
  }
}

export function isResumeFile(file) {
  return Boolean(file && file.size > 0 && /\.(pdf|doc|docx)$/i.test(file.name));
}

export function createApplicationMessage(fields, source = {}) {
  const get = key => String(fields[key] || '').trim();
  return [
    'Здравствуйте! Хочу откликнуться на вакансию руководителя отдела продаж в Annaelle.',
    '',
    `Имя: ${get('name')}`,
    `Телефон: ${normalizePhone(get('phone')) || get('phone')}`,
    `Telegram: ${get('telegram') || 'Не указан'}`,
    `Опыт управления продажами: ${get('experience')}`,
    ...(get('resume_url') ? [`Резюме: ${get('resume_url')}`] : []),
    ...(get('resume_filename') ? [`Резюме прикреплю файлом: ${get('resume_filename')}`] : []),
    '',
    'Управление командой и обучение продажам:',
    get('team_experience'),
    '',
    'Опыт работы в Altegio и CRM:',
    get('systems'),
    '',
    'Пример: показатель → действия → результат:',
    get('case'),
    '',
    `Источник: ${String(source.utm_source || 'Сайт').slice(0, 80)}`,
    ...(source.utm_campaign ? [`Кампания: ${String(source.utm_campaign).slice(0, 80)}`] : []),
    ...(source.utm_content ? [`Креатив: ${String(source.utm_content).slice(0, 80)}`] : [])
  ].join('\n');
}

export function createTelegramUrl(message, username = 'annaellelaser') {
  const safeUsername = /^[A-Za-z0-9_]{5,32}$/.test(username) ? username : 'annaellelaser';
  return `https://telegram.me/${safeUsername}?text=${encodeURIComponent(message)}`;
}
