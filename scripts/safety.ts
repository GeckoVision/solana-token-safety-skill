#!/usr/bin/env -S node --experimental-strip-types
/**
 * Reference client for the Gecko token-safety oracle — zero dependencies.
 *
 * Copy-paste-able example of gating a Solana token from any TS/JS runtime
 * (uses the built-in fetch — no axios/node-fetch). Prints the verdict and exits
 * non-zero on `block` so it composes in scripts/CI.
 *
 * Usage:
 *   node --experimental-strip-types scripts/safety.ts <SPL_MINT>
 *   npx tsx scripts/safety.ts JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN
 *
 * Exit codes: 0 = ok | 10 = caution | 20 = block | 30 = unknown
 */

const ENDPOINT = "https://api.geckovision.tech/safety";
const TIMEOUT_MS = 8000;
const EXIT: Record<string, number> = { ok: 0, caution: 10, block: 20, unknown: 30 };

type Block = { reasons?: string[] };
type Verdict = {
  gate?: string;
  information_mev?: Block;
  wash_risk?: Block | null;
  rug_flags?: string[];
};

async function check(mint: string): Promise<Verdict> {
  try {
    const r = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mint }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!r.ok) return { gate: "unknown" };
    return (await r.json()) as Verdict;
  } catch {
    return { gate: "unknown" }; // fail-OPEN: degrade, never throw into the trade loop
  }
}

function reasons(v: Verdict): string[] {
  const out = [...(v.information_mev?.reasons ?? []), ...(v.wash_risk?.reasons ?? [])];
  return out.length ? out : v.rug_flags ?? [];
}

const mint = process.argv[2];
if (!mint) {
  console.error("usage: scripts/safety.ts <SPL_MINT>");
  process.exit(2);
}
const v = await check(mint);
const gate = v.gate ?? "unknown";
const icon = ({ ok: "✅", caution: "⚠️", block: "❌", unknown: "❓" } as Record<string, string>)[gate] ?? "❓";
console.log(`${icon}  gate = ${gate.toUpperCase()}  (${mint})`);
for (const r of reasons(v).slice(0, 4)) console.log(`    - ${r}`);
if (gate === "unknown") console.error("    note: 'unknown' is NOT safe (the check could not run).");
process.exit(EXIT[gate] ?? 30);
