cat > fix_raylib_uint.pl <<'PL'
#!/usr/bin/env perl
use strict;
use warnings;

my $file = "openpilot/system/ui/lib/application.py";

open my $in, "<", $file or die "Can't read $file: $!\n";
my @lines = <$in>;
close $in;

my $changed = 0;

for (@lines) {
  # Only touch gui_set_style calls that pass rl.color_to_int(...)
  # Example:
  # rl.gui_set_style(..., rl.color_to_int(DEFAULT_TEXT_COLOR))
  # -> rl.gui_set_style(..., (rl.color_to_int(DEFAULT_TEXT_COLOR) & 0xFFFFFFFF))
  if (/gui_set_style\(/ && /rl\.color_to_int\(/ && !/\&\s*0xFFFFFFFF/) {
    s/rl\.color_to_int\(([^)]+)\)/\(rl\.color_to_int($1) \& 0xFFFFFFFF\)/g;
    $changed++;
  }
}

if ($changed == 0) {
  print "No changes needed (already patched?)\n";
  exit 0;
}

# Write back
open my $out, ">", $file or die "Can't write $file: $!\n";
print $out @lines;
close $out;

print "Patched $file ($changed line(s) updated)\n";
PL

chmod +x fix_raylib_uint.pl
