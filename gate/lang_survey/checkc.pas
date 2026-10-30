{ checkc.pas: Free Pascal calling glibc's libm directly, against glibc's results in vec.txt }
program checkc;
{$mode objfpc}{$H+}
uses SysUtils, Math;
function c_pow(x, y: Double): Double; cdecl; external 'm' name 'pow';
function c_exp(x: Double): Double; cdecl; external 'm' name 'exp';
function c_log(x: Double): Double; cdecl; external 'm' name 'log';
function c_log10(x: Double): Double; cdecl; external 'm' name 'log10';
function c_sin(x: Double): Double; cdecl; external 'm' name 'sin';
function c_cos(x: Double): Double; cdecl; external 'm' name 'cos';
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
    if fn = 'pow' then v := c_pow(x.d, y.d)
    else if fn = 'exp' then v := c_exp(x.d)
    else if fn = 'log' then v := c_log(x.d)
    else if fn = 'log10' then v := c_log10(x.d)
    else if fn = 'sin' then v := c_sin(x.d)
    else v := c_cos(x.d);
    for i := 0 to 5 do if names[i] = fn then k := i;
    Inc(n[k]); y.d := v; if y.q <> r.q then Inc(bad[k]);
  end;
  for i := 0 to 5 do WriteLn(Format('%-6s %7d of %d differ', [names[i], bad[i], n[i]]));
end.
