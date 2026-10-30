# AI use

This repository was made with Claude, Anthropic's AI model (Claude Opus 5.5), in Claude Code sessions on
28 and 29 October 2026, under the direction of Robert (Bob) Dickinson. He asked for Fortran, C# and Python
engines, then TypeScript and Java ones, and then Go after a survey of the languages in his Code Rosetta
Stone app; he chose byte-identical ports over bindings, chose one repository per
language and the engines app, and supplied the model corpus. Responsibility for publishing the work is his.

**What Claude did.** It wrote the translator (`tools/c2x/`: the libclang front end and the Fortran back end),
the hand-written runtime and overrides, the gate, benchmark and data scripts, ran every test and control,
diagnosed and fixed every mismatch, built the nine-engine app, and wrote the essay, this README and the
lessons. A Claude subagent wrote `f90/runtime/crt_format.f90` (printf, sscanf and strtod in pure Fortran) and its glibc test suite; the main session reran that suite before using the module.

**How the results were checked.** The checks are mechanical: byte comparison of every `.out` and `.rpt` with EPA
5.2.4 built from the tag, a null control (EPA run twice) and a positive control (a build that fuses
multiply-adds). No person has yet reviewed the generated code or the runtime line by line, or rerun the gate
on another machine. swmm5-cplus and swmm5-rust, shown in the app, were made in earlier Claude sessions for Bob and are only built and gated here.
