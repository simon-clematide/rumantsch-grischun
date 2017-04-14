#!/usr/bin/perl -w
# $Id: split-train-test.perl,v 1.17 2005-12-08 08:46:32 siclemat Exp $
# Simon Clematide
my $TR='train-data';
my $TE='test-data';
my $DV='dev-data';
my $RAND;
my $CONT;
my $NTH;
my $DELIM;
my $HELP;
my $SEED;
my $USAGE =<<EOFUSAGE;
usage: $0 <options> <datafile>
# split lines of datafile into a training and a test part
# datafile must be a real file
options are:
-tr file  # Specify output file for training data ($TR)
-te file  # Specify output file for test data ($TE)
Splitting options:
-cont n/m # Split the datafile in continuous chunks taking the mth (>0!) part as
          # testfile; if -nthd is active, use the m+1 split as dev (or 0 if m=n)
-rand n   # Take randomly 1/nth of each n+1 lines as testdata
-seed n   # Use n as a seed for random generator
-nth spec # Take the nth line as testdata
-nthd     # Randomly take the same amount as test data line as dev data from train (only in combination with -nth or -cont)
-delim s] # Lines befor the line consisting string s are training data
          # Lines after are test data.
EOFUSAGE

use Getopt::Long; # Standardbibliothek fuer Optionenverarbeitung laden

&GetOptions
	(
	 "rand=i" => \$RAND,
	 "tr=s" => \$TR,
	 "te=s" => \$TE,
	 "dv=s" => \$DV,
	 "cont=s" => \$CONT,
	 "delim=s" => \$DELIM,
	 "nth=i" => \$NTH,
	 "nthd" => \$NTHD,
	 "h|help" => \$HELP,
	  "seed=i" => \$SEED
	 );


if (defined $DELIM) {
    $DELIM =~ s/\W//g;
}
if ($HELP) {
  warn $USAGE;
  exit(0);
}


die "# Error: $0\n# usage:\n# $0 <option> datafilestem\n"
	unless defined $ARGV[0];

my $DATAFILE = shift;
open(DF,"<$DATAFILE") or die "Could not open $DATAFILE: $!\n";
my $DFL = int(`wc -l <$DATAFILE`) unless (defined $DELIM);


open(TRAINF,">$TR") or die "$0 error: $@";
open(TESTF,">$TE") or die "$0 error: $@";
if ($DV) {
open(DVF,">$DV") or die "$0 error: $@";
}
my $trlen=0;
my $telen=0;
my $dvlen=0;
if ($RAND) {
  my $RandParts = $RAND + 1;
  for (my $i = 0; $i < int($DFL / $RandParts);$i++) {
	my $test = int(rand($RandParts));
	for (my $j = 0; $j < $RandParts; $j++) {
	  my $l = <DF>;
	  if($test == $j ) {
		print TESTF $l;
		$telen++;
	  } else {
		print TRAINF $l;
		$trlen++;
	  }
	}
  }
}

if (defined $DELIM) {
  my $in_test_section = 0;
  my $l;
  while($l= <DF>){
	chomp $l;
	if(! $in_test_section){
	  if ($l eq $DELIM) {
		$in_test_section = 1;
		print STDERR "# Delimiter $DELIM found on $.\n";
		next;
	  }
	}
	if( $in_test_section == 1) {
	  print TESTF $l, "\n";	$telen++;
	} else {
	  print TRAINF $l, "\n";	$trlen++;
	}
  }
}
if ($NTH && ! $NTHD) {
  my $NthParts = $NTH + 1;
  for (my $i = 0; $i < int($DFL / $NthParts);$i++) {
	for (my $j = 0; $j < $NthParts; $j++) {
	  my $l = <DF>;
	  if($NTH == $j ) {
		print TESTF $l;	$telen++; }
	  else {
		print TRAINF $l;	$trlen++;
	  }
	}
  }
}
if ($NTH && $NTHD) {
  my $NthParts = $NTH + 1;
  for (my $i = 0; $i < int($DFL / $NthParts);$i++) {
	for (my $j = 0; $j < $NthParts; $j++) {
	  my $l = <DF>;
	  if($NTH == $j ) {
		print TESTF $l;	$telen++; }
	  else {
		if ($NTH == (($j+1) % $NthParts)) {
		  print DVF $l;	$dvlen++;
		  
	  	} else {
		  print TRAINF $l;	$trlen++;
		}
	  }
	}
  }
  while (<DF>) {
	print TRAINF $_ ;
	$residuals++;
  }
  print STDERR "# Residual lines added to training data: $residuals\n";
  
}


if($CONT && ! $NTHD) {
  if ( my($Parts,$ThePart) = ( $CONT =~ m|(\d+)/(\d+)|)) {
	die $USAGE if ($Parts > $DFL or $ThePart > $Parts);
	my $PartSize = int($DFL / $Parts);
	my $PartStart = ($PartSize * $ThePart)-$PartSize;
	my $PartEnd = $PartStart + $PartSize;
	my $line = 0;
	my $lastline = $PartSize * $Parts;
	while ($line < $lastline) {
	  $_ = <DF>;
	  if (($line >= $PartStart) and ($line < $PartEnd)) {
		print TESTF $_; 	$telen++;}
	  else {
	      print TRAINF $_;	$trlen++;
	  }
	  $line++;
	}
	# print out residual lines
	# need to determine first which filehandle to write to
	
	# if lastline == PartEnd => TESTF
	if ( $lastline == $PartEnd ) {
	    my $residuals= 0;
	    while (<DF>) {
		print TESTF $_ ;
		$residuals++;
	    } 
	    print STDERR "# Residual lines added to test data: $residuals\n";
	} else
	{
	    while (<DF>) {
		print TRAINF $_ ;
		$residuals++;
		$trlen++;
	    }
	    print STDERR "# Residual lines added to training data: $residuals\n";
	}
  } else {
	die $USAGE;
}
}
if($CONT &&  $NTHD) {
  if ( my($Parts,$ThePart) = ( $CONT =~ m|(\d+)/(\d+)|)) {
	die $USAGE if ($Parts > $DFL or $ThePart > $Parts);
	my $PartSize = int($DFL / $Parts);
	my $TheDevPart = $ThePart+1;
	$TheDevPart = 0 if ($ThePart + 1) > $Parts;
	my $DevPartStart = ($PartSize * $TheDevPart)-$PartSize;
	$DevPartStart = 0 if $DevPartStart < 0;
	my $DevPartEnd = $DevPartStart + $PartSize;
	my $PartStart = ($PartSize * $ThePart)-$PartSize;
	my $PartEnd = $PartStart + $PartSize;
	my $line = 0;
	my $lastline = $PartSize * $Parts;
	while ($line < $lastline) {
	  $_ = <DF>;
	  if (($line >= $PartStart) and ($line < $PartEnd)) {
		print TESTF $_; 	$telen++;
		}
		elsif (($line >= $DevPartStart) and ($line < $DevPartEnd)) {
			 print DVF $_;	$dvlen++;
		}
	  else {
	      print TRAINF $_;	$trlen++;
	  }
	  $line++;
	}
	{
	    while (<DF>) {
		print TRAINF $_ ;
		$trlen++;
		$residuals++;
	    }
	    print STDERR "# Residual lines added to training data: $residuals\n";
	}
  } else {
	die $USAGE;
}
}

close(TESTF);
close(TRAINF);
if ($DV) {
close(DVF);
print STDERR "# training set size: $trlen\n# test set size: $telen\n# dev set size: $dvlen;\n";

}
else{
print STDERR "# Training size: $trlen\n# Test size: $telen\n";

}



