`set -o pipefail` plus `cmd | head -1` can kill a script with status 141 (SIGPIPE) at random.

The formatter's run_tests.sh printed tool versions with `gcc --version | head -1`. When head exits before
gcc finishes writing, gcc dies of SIGPIPE, pipefail turns that into a failure and `set -e` stops the
script before any test runs. It passed for the subagent and failed on the rerun. Use `sed -n 1p`, which
reads its whole input. Two more from the same work: libgfortran treats a short read() from a pipe as end
of file (feed test data through a regular file), and glibc's sscanf behaves differently for C17 and C23
callers (`%i` and `0b`), so a reference generator must be compiled like the engine it stands in for.
