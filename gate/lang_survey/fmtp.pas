program fmtp; {$mode objfpc}{$H+}
uses SysUtils, Math;
var line, f, xs, fs: string; parts: TStringArray; x: Double; code: Integer;
begin
  SetExceptionMask([exInvalidOp, exDenormalized, exZeroDivide, exOverflow, exUnderflow, exPrecision]);
  while not Eof(Input) do begin
    ReadLn(line); parts := line.Split([' ']); f := parts[0]; xs := parts[1]; Val(xs, x, code);
    fs := f; if Pos('%10', fs) = 1 then fs := '%10' + Copy(fs, 4, 99);
    try WriteLn(f, ' ', xs, ' -> [', Format(fs, [x]), ']');
    except on E: Exception do WriteLn(f, ' ', xs, ' -> [error: ', E.Message, ']'); end;
  end;
end.
