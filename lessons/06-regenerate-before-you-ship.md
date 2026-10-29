Regenerate every generated file from the shipped translator before the final gate, and diff it.

The Fortran translator avoids every name the runtime modules define. The printf/scanf module grew a
variable called `last` after the engine had been generated and gated, so regenerating in the clean
repository copy renamed SWMM's toposort global `Last` to `Last_c`. Harmless, but the shipped generated
file was no longer what the shipped translator produces. The fix was procedural: regenerate all three
engines from the final translator, compare byte for byte with what was gated (C# and Python identical,
Fortran differing only in that rename), rebuild and re-gate Fortran. A generated file is only as current
as everything the generator reads.

The same check for TypeScript and Java (29 October): `emit_ts.py` and `emit_java.py` were rerun from the
shipped translator before the repositories were laid out, and `ts/src/engine.ts` and all 54 generated Java
files came out byte-identical to the ones the final gate ran.
