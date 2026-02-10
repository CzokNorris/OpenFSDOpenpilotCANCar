#!/usr/bin/env perl
use strict;
use warnings;

my $file = "openpilot/system/ui/lib/application.py";
open my $in, "<", $file or die "Can't read $file: $!\n";
my $txt = do { local $/; <$in> };
close $in;

my $changed = 0;

# Ensure ctypes import exists
if ($txt !~ /^\s*import\s+ctypes\s*$/m) {
  # insert after first block of imports
  if ($txt =~ s/^((?:from\s+\S+\s+import\s+.*\n|import\s+\S+.*\n)+)/$1import ctypes\n/m) {
    $changed++;
  } else {
    # fallback: prepend
    $txt = "import ctypes\n" . $txt;
    $changed++;
  }
}

# Ensure helper exists
if ($txt !~ /def\s+_i32\(/) {
  # place helper after imports
  $txt =~ s/^((?:from\s+\S+\s+import\s+.*\n|import\s+\S+.*\n)+)\n/$1\n\ndef _i32(x: int) -> int:\n  return ctypes.c_int32(int(x)).value\n\n/m
    or die "Couldn't insert _i32 helper\n";
  $changed++;
}

# Wrap gui_set_style(..., rl.color_to_int(...)) arguments with _i32(...)
# Only touch lines that call gui_set_style and contain rl.color_to_int(
my @lines = split(/\n/, $txt, -1);
for my $l (@lines) {
  if ($l =~ /gui_set_style\(/ && $l =~ /rl\.color_to_int\(/ && $l !~ /_i32\s*\(\s*rl\.color_to_int\(/) {
    $l =~ s/rl\.color_to_int\(([^)]+)\)/_i32(rl.color_to_int($1))/g;
    $changed++;
  }
}
$txt = join("\n", @lines);

open my $out, ">", $file or die "Can't write $file: $!\n";
print $out $txt;
close $out;

print "Patched $file (changes: $changed)\n";
