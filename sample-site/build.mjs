import { cpSync, mkdirSync, rmSync } from 'node:fs';

const output = new URL('./build/', import.meta.url);
rmSync(output, { recursive: true, force: true });
mkdirSync(output, { recursive: true });
cpSync(new URL('./public/', import.meta.url), output, { recursive: true });
