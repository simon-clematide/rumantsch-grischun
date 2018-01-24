#!/usr/bin/perl

# University of Zurich - Institute of Computational Linguistics
# Morphology anlysis for Romansh: Tokenizer
# Author: Reto Baumgartner
# Date: June 2013

#use: perl tokenizer.pl infile outfile

#use warnings;
use utf8;
use strict;

my @tokens;
my $text;
chomp @ARGV;

open (INFILE, '<:encoding(UTF-8)', "$ARGV[0]") || die "kann $ARGV[0] nicht öffnen.";
while (<INFILE>){
    $text .= "$_";
}
close (INFILE);

# Satzzeichen abtrennen:
$text =~ s/([;:?!])/ \1/g;
#
$text =~ s/(\D)\,/\1 \,/g;
$text =~ s/(\d)\,(\s)/\1 \,\2/g;
#
#$text =~ s/([a-zäöüàèìòùâêîôûáéíóú»"“‘›])(\.)\s(?[])?([A-ZÄÖÜÀÈÌÒÙÂÊÎÔÛÁÉÍÓÚ])/\1 \. \3/g;
$text =~ s/([a-zäöüàèìòùâêîôûáéíóú»"“‘›])([.:])(?=\s?[«"„»]?\s?(?:[A-ZÄÖÜÀÈÌÒÙÂÊÎÔÛÁÉÍÓÚ]|$))/\1 \2/g;
$text =~ s/([a-zäöüàèìòùâêîôûáéíóú»"“‘›])([.:])\n/\1 \2 \3/g;
# Vier Ziffern sind meistens Jahresangaben.
$text =~ s/(\d\d\d\d)(\.)/\1 \2/g;
# Apostrophierung behandeln
## Es wird nur abgetrennt, wenn der Apostroph zum ersten Teil gehoert. 
## Ist ein Vokal vom nachfolgenden Teil elidiert, gilt dies als Endung.
$text =~ s/([a-zäöüàèìòùâêîôûáéíóúA-ZÄÖÜÀÈÌÒÙÂÊÎÔÛÁÉÍÓÚ])('|’)(h?[aeiouyäöüàèìòùâêîôûáéíóú])/\1\2 \3/ig;
# Klammern einzeln stehen lassen:
$text =~ s/([({\[])/ \1 /g;
$text =~ s/([)}\]])/ \1 /g;
# Anfuehrungszeichen abtrennen
$text =~ s/([^a-zäöüàèìòùâêîôûáéíóúA-ZÄÖÜÀÈÌÒÙÂÊÎÔÛÁÉÍÓÚ])([«"„‚‹])([a-zäöüàèìòùâêîôûáéíóúA-ZÄÖÜÀÈÌÒÙÂÊÎÔÛÁÉÍÓÚ])()/\1 \2 \3/g;
$text =~ s/([«"„‚‹])([a-zäöüàèìòùâêîôûáéíóúA-ZÄÖÜÀÈÌÒÙÂÊÎÔÛÁÉÍÓÚ])()/\1 \2/g;
$text =~ s/([a-zäöüàèìòùâêîôûáéíóúA-ZÄÖÜÀÈÌÒÙÂÊÎÔÛÁÉÍÓÚ?!.])([»"“‘›])([^a-zäöüàèìòùâêîôûáéíóúA-ZÄÖÜÀÈÌÒÙÂÊÎÔÛÁÉÍÓÚ])/\1 \2 \3/g;
# Abkürzungen behandeln
$text =~ s/(usw|etc) \./\1\./g;
$text =~ s/\s+/ /g;
$text =~ s/\n+/ /g;


@tokens = split(/\s/, $text); 

open (OUTFILE, '>:encoding(UTF-8)', "$ARGV[1]") || die "kann $ARGV[1] nicht öffnen.";
foreach (@tokens) {print OUTFILE "$_\n";}
close (OUTFILE);
