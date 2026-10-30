# check.pl: Perl's own math (which calls the C library) against glibc's results in vec.txt
use strict; no warnings; use POSIX ();
my (%bad, %n);
open(my $f, '<', $ARGV[0]) or die;
sub d { unpack('d', pack('Q', hex($_[0]))) }
sub h { sprintf('%016x', unpack('Q', pack('d', $_[0]))) }
while (<$f>) {
  my ($fn, $x, $y, $r) = split;
  my ($a, $b) = (d($x), d($y)); my $v;
  if    ($fn eq 'pow')   { $v = $a ** $b }
  elsif ($fn eq 'exp')   { $v = exp($a) }
  elsif ($fn eq 'log')   { $v = log($a) }
  elsif ($fn eq 'log10') { $v = POSIX::log10($a) }
  elsif ($fn eq 'sin')   { $v = sin($a) }
  elsif ($fn eq 'cos')   { $v = cos($a) }
  $n{$fn}++; $bad{$fn}++ if h($v) ne $r;
}
printf("%-6s %7d of %d differ\n", $_, $bad{$_} // 0, $n{$_}) for qw(pow exp log log10 sin cos);
