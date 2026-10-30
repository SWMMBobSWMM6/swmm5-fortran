while (<STDIN>) { my ($f, $x) = split; printf("%s %s -> [%s]\n", $f, $x, sprintf($f, $x)); }
