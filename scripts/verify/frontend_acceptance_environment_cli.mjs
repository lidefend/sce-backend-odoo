#!/usr/bin/env node
import { redactedEnvironmentEvidence, resolveAcceptanceEnvironment } from './lib/frontend_acceptance_environment.mjs';

const args = process.argv.slice(2);
let tool = '';
let operation = '';
const forwarded = [];
for (let index = 0; index < args.length; index += 1) {
  if (args[index] === '--tool') { tool = args[index += 1] || ''; continue; }
  if (args[index] === '--operation') { operation = args[index + 1] || ''; forwarded.push(args[index], args[index += 1]); continue; }
  forwarded.push(args[index]);
}
try {
  const environment = resolveAcceptanceEnvironment({ tool, operation, argv: forwarded });
  process.stdout.write(`${JSON.stringify(redactedEnvironmentEvidence(environment))}\n`);
} catch (error) {
  process.stderr.write(`[frontend_acceptance_environment] FAIL ${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 2;
}
