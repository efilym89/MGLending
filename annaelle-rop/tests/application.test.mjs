import assert from 'node:assert/strict';
import test from 'node:test';
import {
  createApplicationMessage,
  createTelegramUrl,
  isResumeFile,
  isResumeUrl,
  normalizePhone
} from '../application.mjs';

test('remote candidates can use Uzbekistan and international phone numbers', () => {
  assert.equal(normalizePhone('+998 (90) 123-45-67'), '+998901234567');
  assert.equal(normalizePhone('+7 (999) 123-45-67'), '+79991234567');
  assert.equal(normalizePhone('12345'), '');
  assert.equal(normalizePhone('000000000'), '');
  assert.equal(normalizePhone('+99890letters1234567'), '');
  assert.equal(normalizePhone('+1234567890123456'), '');
});

test('resume accepts web links and document files, not executable URLs or other formats', () => {
  assert.equal(isResumeUrl('https://example.com/резюме.pdf'), true);
  assert.equal(isResumeUrl('javascript:alert(1)'), false);
  assert.equal(isResumeUrl('file:///resume.pdf'), false);
  assert.equal(isResumeFile({name:'CV.PDF',size:100}), true);
  assert.equal(isResumeFile({name:'CV.docx',size:100}), true);
  assert.equal(isResumeFile({name:'photo.jpg',size:100}), false);
  assert.equal(isResumeFile({name:'empty.pdf',size:0}), false);
});

test('the prepared application includes ROP answers and an explicit manual resume attachment', () => {
  const message = createApplicationMessage({
    name:'Тестовый кандидат',phone:'+7 (999) 123-45-67',experience:'3–5 лет',
    team_experience:'Обучал команду продаж.',systems:'Altegio и CRM.',
    case:'Конверсия: 20% → 30%.',resume_filename:'Резюме & опыт.docx'
  }, {utm_source:'test',utm_campaign:'роль РОП'});
  assert.match(message, /руководителя отдела продаж/);
  assert.match(message, /Телефон: \+79991234567/);
  assert.match(message, /Резюме прикреплю файлом: Резюме & опыт.docx/);
  assert.match(message, /Конверсия: 20% → 30%/);
  assert.match(message, /Кампания: роль РОП/);
  const url = new URL(createTelegramUrl(message));
  assert.equal(url.hostname, 'telegram.me');
  assert.equal(url.pathname, '/annaellelaser');
  assert.equal(url.searchParams.get('text'), message);
  assert.equal(url.searchParams.size, 1);
});

test('maximum allowed form content fits one Telegram message', () => {
  const message = createApplicationMessage({
    name:'Н'.repeat(100),phone:'+998901234567',telegram:'т'.repeat(64),experience:'Более 5 лет',
    resume_url:'https://example.com/'+'a'.repeat(480),resume_filename:'x'.repeat(250)+'.pdf',
    team_experience:'У'.repeat(700),systems:'С'.repeat(700),case:'К'.repeat(700)
  }, {utm_source:'s'.repeat(1000),utm_campaign:'c'.repeat(1000),utm_content:'t'.repeat(1000)});
  assert.ok(message.length < 4096);
  assert.match(createTelegramUrl(message,'invalid/user'), /^https:\/\/telegram\.me\/annaellelaser\?/);
});
