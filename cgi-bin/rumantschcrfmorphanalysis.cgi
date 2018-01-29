#!/usr/bin/perl -CSD
use File::Spec;
my ($volume, $CGIDIR, $file) = File::Spec->splitpath(__FILE__);
print STDERR "$volume $CGIDIR $file\n";
use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use Encode qw(decode encode);

# Some Variables
$contenttype = "Content-Type: text/plain; charset=utf-8\n\n";
$characterlimit = 1000000;
$Rawtext = param('rohtext');

$tmpdatei = "/tmp/$file.$$";
$Program = $CGIDIR . 'tools/parse.sh';

@Arguments =  ( $tmpdatei,  $Mode) ;
$ENV{'PATH'} = "$CGIDIR:$CGIDIR/tools:/mnt/storage/clfiles/resources/bin/:$ENV{PATH}";

$Rawtext = decode("utf-8", $Rawtext);
$Rawtext =~ tr/\r/\n/s;

$rawtextlength = length($Rawtext);
if ($rawtextlength>$characterlimit) {
print $contenttype;
print "Sorry, input is limited to $characterlimit characters!\n";
exit(0);
};

if ($rawtextlength < 1) {
	print $contenttype;
	print  "ERROR: Sorry, not enough input!\n" ;
	exit;
}
;

$Rawtext =~ s/\r//g;
# simple tokenizer
if ($Rawtext =~ /\b \b/) {
	#$Rawtext =~ s/([.,:;!?])/ \1/g;
	$Rawtext =~ s/([’'])/\1 /g;
	$Rawtext =~ s/ +/\n/g;

};

die "Could not create file\n" unless open(TMPFILE,"> $tmpdatei");
print TMPFILE $Rawtext;
close(TMPFILE);


undef $/ ;
die "Keine Datei $CGIDIR/ vorhanden\n" unless -x "$CGIDIR/$file";
die "cannot fork: $!" unless defined($pid = open(SICHERES_KIND, "-|"));
if ($pid == 0) {
  exec("python $CGIDIR/tools/analyse.py -a data/GrischunGuessing.fst -m data/crf-morphpos-model -d $tmpdatei ")
	or die "Kann $! $?  nicht ausfuehren: $!";
} else {
  undef $/ ;
#die "Verarbeitet\n";
  print "Content-Type: text/plain; charset=utf-8

";
  while (<SICHERES_KIND>) { print };

  close(SICHERES_KIND);
}
unlink $tmpdatei;
