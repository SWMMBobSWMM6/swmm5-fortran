{ check.pas: Free Pascal's own math against glibc's results in vec.txt }
program check;
{$mode objfpc}{$H+}
uses SysUtils, Math;
type TBits = record case Integer of 0: (d: Double); 1: (q: QWord); end;
var f: TextFile; line, fn: string; parts: TStringArray; x, y, r: TBits; v: Double;
    names: array[0..5] of string = ('pow', 'exp', 'log', 'log10', 'sin', 'cos');
    bad, n: array[0..5] of Integer; k, i: Integer;
function hx(const s: string): QWord; begin Result := StrToQWord('$' + s); end;
begin
  SetExceptionMask([exInvalidOp, exDenormalized, exZeroDivide, exOverflow, exUnderflow, exPrecision]);
  for i := 0 to 5 do begin bad[i] := 0; n[i] := 0; end;
  AssignFile(f, ParamStr(1)); Reset(f);
  while not Eof(f) do begin
    ReadLn(f, line); parts := line.Split([' ']); fn := parts[0];
    x.q := hx(parts[1]); y.q := hx(parts[2]); r.q := hx(parts[3]);
    if fn = 'pow' then v := Power(x.d, y.d)
    else if fn = 'exp' then v := Exp(x.d)
    else if fn = 'log' then v := Ln(x.d)
    else if fn = 'log10' then v := Log10(x.d)
    else if fn = 'sin' then v := Sin(x.d)
    else v := Cos(x.d);
    for i := 0 to 5 do if names[i] = fn then k := i;
    Inc(n[k]); y.d := v; if y.q <> r.q then Inc(bad[k]);
  end;
  for i := 0 to 5 do WriteLn(Format('%-6s %7d of %d differ', [names[i], bad[i], n[i]]));
end.
