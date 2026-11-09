#!/usr/bin/env node
// Streaming AES-256-GCM. Preserves the OCBACK01 on-disk format used by older checkpoints.
import {createCipheriv, createDecipheriv, randomBytes, scryptSync} from 'node:crypto';
import {createReadStream, createWriteStream, openSync, readSync, statSync, unlinkSync, closeSync} from 'node:fs';
import {once} from 'node:events';

const [action, input, output] = process.argv.slice(2);
const password = process.env.OPENCODE_BACKUP_KEY || '';
if (!['encrypt', 'decrypt'].includes(action) || !input || !output) {
  console.error('Usage: node opencode-crypto.mjs encrypt|decrypt INPUT OUTPUT');
  process.exit(2);
}
if (password.length < 32) {
  console.error('OPENCODE_BACKUP_KEY must have at least 32 characters.');
  process.exit(2);
}
const magic = Buffer.from('OCBACK01');
let writer;
async function write(data) {
  if (data.length && !writer.write(data)) await once(writer, 'drain');
}
try {
  const bytes = statSync(input).size;
  let cipher, stream;
  if (action === 'encrypt') {
    const salt = randomBytes(16);
    const nonce = randomBytes(12);
    cipher = createCipheriv('aes-256-gcm', scryptSync(password, salt, 32), nonce);
    stream = createReadStream(input, {highWaterMark: 1024 * 1024});
    writer = createWriteStream(output, {flags:'w', mode:0o600});
    await write(Buffer.concat([magic, salt, nonce]));
    for await (const chunk of stream) await write(cipher.update(chunk));
    await write(cipher.final());
    await write(cipher.getAuthTag());
  } else {
    if (bytes < 52) throw Error('Invalid encrypted file length');
    const fd = openSync(input, 'r');
    const header = Buffer.alloc(36);
    const tag = Buffer.alloc(16);
    try {
      if (readSync(fd, header, 0, 36, 0) !== 36 ||
          readSync(fd, tag, 0, 16, bytes - 16) !== 16 ||
          !header.subarray(0, 8).equals(magic)) {
        throw Error('Invalid encrypted checkpoint header');
      }
    } finally {closeSync(fd);}
    cipher = createDecipheriv('aes-256-gcm', scryptSync(password, header.subarray(8,24), 32), header.subarray(24,36));
    cipher.setAuthTag(tag);
    writer = createWriteStream(output, {flags:'w', mode:0o600});
    if (bytes > 52) {
      stream = createReadStream(input, {start:36, end:bytes-17, highWaterMark:1024*1024});
      for await (const chunk of stream) await write(cipher.update(chunk));
    }
    await write(cipher.final());
  }
  writer.end();
  await once(writer, 'finish');
} catch (error) {
  writer?.destroy();
  try {unlinkSync(output);} catch {}
  console.error('Encrypted checkpoint operation failed:', error.message);
  process.exit(1);
}
