#!/usr/bin/perl

binmode STDOUT, ":utf8";
binmode STDIN, ":utf8";
use File::Spec;
my ($volume, $CGIDIR, $file) = File::Spec->splitpath(__FILE__);
print STDERR "$volume $CGIDIR $file\n";
use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use Encode qw(decode encode);

$tmpdatei = "/tmp/$file.$$";

$Rohtext = param('rohtext');

$Rohtext = decode("utf-8", $Rohtext);
die "Could not create file\n" unless open(TMPFILE,"> $tmpdatei");
$Rohtext =~ tr/\r/\n/s;
die "Sorry, aber der Input war zu lang!\n" if (length($Rohtext)>25000);
print TMPFILE $Rohtext;
close(TMPFILE);
$ENV{'PATH'} = "$CGIDIR:$CGIDIR/ppdiag/backend:/opt/bin:$ENV{PATH}";
undef $/ ;
die "Keine Datei $CGIDIR/ vorhanden\n" unless -x "$CGIDIR/$file";
die "cannot fork: $!" unless defined($pid = open(SICHERES_KIND, "-|"));
if ($pid == 0) {
  exec("flookup -x data/GrischunGuessing.fst <$tmpdatei")
	or die "Kann $! $?  nicht ausfuehren: $!";
} else {
  undef $/ ;
#die "Verarbeitet\n";
  print "Content-Type: text/plain

";
  while (<SICHERES_KIND>) { print };

  close(SICHERES_KIND);
}
#unlink $tmpdatei;
