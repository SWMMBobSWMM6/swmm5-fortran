STDIN.each_line { |l| f, x = l.split; printf("%s %s -> [%s]\n", f, x, format(f, Float(x))) }
