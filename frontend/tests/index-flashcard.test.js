import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';

test('chat workspace includes a flashcard section with expandable topic details', () => {
  const source = readFileSync(new URL('../src/pages/index.astro', import.meta.url), 'utf8');

  assert.match(source, /id="flashcard-panel"/);
  assert.match(source, /id="flashcard-generate"/);
  assert.match(source, /id="flashcard-output"/);
  assert.match(source, /\/chats\/flashcard/);
  assert.match(source, /Flashcards/);
  assert.match(source, /<details[^>]*class="chat-disclosure"[^>]*>/);
  assert.match(source, /<details[^>]*class="summary-disclosure"[^>]*>/);
  assert.match(source, /<details[^>]*class="flashcard-references"[^>]*>/);
});
