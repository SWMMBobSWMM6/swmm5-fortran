# Stored gate runs for the TypeScript and Java engines: what ran, and how

`gate/gate.py` does not record the engine command in its JSON, so this file does. Commands marked *recorded* are
copied from the session transcript of 29 October 2026; the ones marked *from the session's account* predate the
part of the transcript that survives, and rest on the author's (Claude's) record of the work, not on a stored
log. All runs: `python3 gate/gate.py NAME "ENGINE" --ids IDS -j 1 --timeout 1800`, from `gate/`.

| Run (results/NAME.json) | Engine command | Models | Result | Source |
|---|---|---|---|---|
| ts1 | `node ts/dist/runswmm.js`, an earlier build whose `pow` was the full GIMPLE translation (no fast path) | all 480 | 480 PASS | from the session's account |
| ts_final1_q1..q4 | `node ts/dist/runswmm.js`, final build | quarters 1-4 | 480 PASS | recorded (first final run; JSON copied from ts_final_q1..q4 before the rerun overwrote them) |
| ts_final_q1..q4 | `node ts/dist/runswmm.js`, final build (`overrides.js` differs from the first final run in one header comment only) | quarters 1-4 | 480 PASS | recorded (second final run, outputs kept for the app's re-check; lesson 15) |
| java_a, java_b | `java -jar java/swmm5.jar` (no heap flags) | halves A and B | 479 PASS, 1 CRASH (OutOfMemoryError on Hydrology/sewer_rdii_problem.inp) | from the session's account; `results/peak_memory.txt` repeats the plain-jar run on that model |
| java_final1_a, java_final1_b | `java/runswmm` (launcher: `-XX:+UseParallelGC -XX:MaxRAMPercentage=75`) | halves A and B | 480 PASS | recorded (first final run; `java_final1_run_b.txt` is that run's log and still names itself java_final_b; half A's log was overwritten by the rerun) |
| java_final_a, java_final_b | `java/runswmm` | halves A and B | 480 PASS | recorded (second final run, outputs kept) |
| ctl_ts_native | `gate/run_ts_native_control.sh` (V8's Math in place of the translations) | smoke40.txt | 34 PASS, 6 differ | recorded |
| ctl_java_native, ctl_java_native_all | `gate/run_java_native_control.sh [ids_all.txt ctl_java_native_all]` (Java's Math) | smoke40.txt / all 480 | 39 PASS, 1 differs / 442 PASS, 38 differ | recorded |

The final TypeScript and Java builds were also rebuilt from a clean copy of each repository layout
(`npm install && npm run build`, `java/build.sh`); the JavaScript files and Java class files came out
byte-identical to the ones the gate ran.

Written by Claude (Anthropic); see AI-USE.md.
