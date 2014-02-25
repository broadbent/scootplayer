set term postscript eps
set output "scootplayer.ps"
set datafile separator ","
set xlabel "Time (seconds)"
set ylabel "Bits per second"
plot  "../../scootplayer.csv" using 1:3 with lines title 'Download Queue', \
	"../../scootplayer.csv" using 1:7 with lines title 'Playback Queue'