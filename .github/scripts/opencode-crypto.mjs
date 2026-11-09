#!/usr/bin/env node
// Versioned authenticated encryption for snapshots stored in a public repository.
import { createCipheriv, createDecipheriv, randomBytes, scryptSync } from 'node:crypto';
import { readFileSync, writeFileSync, rmSync } from 'node:fs';

const [action, input, output] = process.argv.slice(2);
const passphrase = process.env.OPENCODE_BACKUP_KEY || '';
if (!['encrypt', 'decrypt'].includes(action) || !input || !output) {
  console.error('Usage: node opencode-crypto.mjs encrypt|decrypt INPUT OUTPUT');
  process.exit(2);
}
if (passphrase.length < 32) {
  console.error('OPENCODE_BACKUP_KEY must be at least 32 characters.');
  process.exit(2);
}
const MAGIC = Buffer.from('OCBACK01');
const MAX_BYTES = 90 * 1024 * 1024;
try {
  const raw = readFileSync(input);
  if (raw.byteLength > MAX_BYTES + 64) throw new Error('Snapshot exceeds 90 MiB cap');
  let outputBytes;
  if (action === 'encrypt') {
    const salt = randomBytes(16);
    const nonce = randomBytes(12);
    const cipher = createCipheriv('aes-256-gcm', scryptSync(passphrase, salt, 32), nonce);
    const encrypted = Buffer.concat([cipher.update(raw), cipher.final()]);
    outputBytes = Buffer.concat([MAGIC, salt, nonce, encrypted, cipher.getAuthTag()]);
  } else {
    if (raw.length < 52 || !raw.subarray(0, 8).equals(MAGIC)) throw new Error('Invalid snapshot header');
    const salt = raw.subarray(8, 24);
    const nonce = raw.subarray(24, 36);
    const ciphertext = raw.subarray(36, -16);
    const authTag = raw.subarray(-16);
    const decipher = createDecipheriv('aes-256-gcm', scryptSync(passphrase, salt, 32), nonce);
    decipher.setAuthTag(authTag);
    outputBytes = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  }
  writeFileSync(output, outputBytes, { mode: 0o600, flag: 'w' });
} catch (error) {
  try { rmSync(output, { force: true }); } catch {}
  console.error('Encrypted snapshot operation failed:', error.message);
  process.exit(1);
}
