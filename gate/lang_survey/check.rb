# check.rb: Ruby's own math against glibc's results in vec.txt
bad = Hash.new(0); n = Hash.new(0)
d = ->(h) { [h].pack('H*').unpack1('G') }
File.foreach(ARGV[0]) do |line|
  fn, x, y, r = line.split
  a = d.(x); b = d.(y)
  v = case fn
      when 'pow' then a ** b
      when 'exp' then Math.exp(a)
      when 'log' then Math.log(a)
      when 'log10' then Math.log10(a)
      when 'sin' then Math.sin(a)
      when 'cos' then Math.cos(a)
      end
  n[fn] += 1
  bad[fn] += 1 if [v].pack('G').unpack1('H*') != r
end
%w[pow exp log log10 sin cos].each { |k| printf("%-6s %7d of %d differ\n", k, bad[k], n[k]) }
