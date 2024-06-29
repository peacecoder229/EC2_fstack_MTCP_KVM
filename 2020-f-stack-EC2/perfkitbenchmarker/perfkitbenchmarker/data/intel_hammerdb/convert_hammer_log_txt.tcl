#!/usr/bin/tclsh
set tmpdir /tmp
set filenames [glob -nocomplain -tails -directory $tmpdir hammer*.log]
foreach filename [ split $filenames ] {
set excelfile [ join [ file rootname $filename ].txt ]
puts "Converting $filename to $excelfile"
set fp [ open [ join $tmpdir/$filename ] r ] 
set op [ open [ join $tmpdir/$excelfile ] w ] 
set file_data [ read $fp ]
 set data [split $file_data "\n"]
 foreach line $data {
 if {[ string match *PERCENTILES* $line ]} {
 set timeval "[ lindex [ split $line ] 3 ]"
 append xaxis "$timeval\t"
         }
     }
 puts $op "TIME INTERVALS"
 puts $op "\t$xaxis"
 foreach storedproc {neword payment delivery slev ostat} {
 puts $op [ string toupper $storedproc ]
 foreach line $data {
 if {[ string match *PROCNAME* $line ]} { break }
 if {[ string match *$storedproc* $line ]} {
 regexp {MIN-[0-9.]+} $line min
 regsub {MIN-} $min "" min
 append minlist "$min\t"
 regexp {P50%-[0-9.]+} $line p50
 regsub {P50%-} $p50 "" p50
 append p50list "$p50\t"
 regexp {P95%-[0-9.]+} $line p95
 regsub {P95%-} $p95 "" p95
 append p95list "$p95\t"
 regexp {P99%-[0-9.]+} $line p99
 regsub {P99%-} $p99 "" p99
 append p99list "$p99\t"
 regexp {MAX-[0-9.]+} $line max
 regsub {MAX-} $max "" max
 append maxlist "$max\t"
     }
       }
 puts -nonewline $op "MIN\t"
 puts $op $minlist
 unset -nocomplain minlist
 puts -nonewline $op "P50\t"
 puts $op $p50list 
 unset -nocomplain p50list
 puts -nonewline $op "P95\t"
 puts $op $p95list 
 unset -nocomplain p95list
 puts -nonewline $op "P99\t"
 puts $op $p99list
 unset -nocomplain p99list
 puts -nonewline $op "MAX\t"
 puts $op $maxlist
 unset -nocomplain maxlist
     }
 close $fp
 close $op
}
