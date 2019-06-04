#
# Visualize graph information from dataserver
#
#   The grasp server (running on QNX) reads the UDP stream from
# the arduino board and places each data sample into the dataserver (ess_ds).
# The samples are stored in a data point called "grasp:data",
# which can be read directly:
#
#  qpcs::dsGetData server grasp:data
#
# This will return a data string, whose datavalues can be converted
# into a byte string in the following way:
#
#  set data [qpcs::dsGetData server grasp:data]
#  dl_local vals [qpcs::dsData $data]
#  vals:0 -> left channel
#  vals:1*256+vals:2 -> left timestamp
#  vals:3-vals:14 -> values for left 12 channels
#  vals:15 -> right channel
#  vals:16*256+vals:17 -> right timestamp
#  vals:18-vals:30 -> values for right 12 channels
#
# This program uses dsRegister/dsAddMatch/dsAddCallback
#

package require Tk
package require qpcs
package require sqlite3
package require dlsh
package require stimctrl
load_Stats

#reads shape information from database and puts it into useful array shape
proc get_shape_coords { dbcmd obj_id w h } {
    # read x, y, and pad numbers from database
    set x [$dbcmd eval "SELECT x FROM shapeTable${obj_id}"]
    set y [$dbcmd eval "SELECT y FROM shapeTable${obj_id}"]
    set pad [$dbcmd eval "SELECT pad FROM shapeTable${obj_id}"]

    #convert points into list
    dl_local xvals [eval dl_flist $x]
    dl_local yvals [eval dl_flist $y]

    #scale and shift for plotting
    dl_local x0 [dl_mult [dl_add $xvals 0.5] [expr $w/1]]
    dl_local y0 [dl_sub $h [dl_mult [dl_add $yvals 0.5] [expr $h/1]]]

    #reshape the array for convenience with create line
    dl_local xy [dl_transpose [dl_llist $x0 $y0]]
    dl_local sorted_by_pad [dl_deepUnpack [dl_sortByList $xy $pad]]
    
    return [dl_tcllist $sorted_by_pad]
}




namespace eval gview {
    set connected 0
    set datahub beast.neuro.brown.edu
    set leftChanBox 0
    set rightChanBox 0

    set current_count 0
    set currentLeft -1
    set currentRight -1
    set max_count 5

    set cycleCount 8

    set test_timing 0
    set status(left_canvas_width) 250
    set status(left_canvas_height) 250
    set widgets(left_canvas) ""
    set status(right_canvas_width) 250
    set status(right_canvas_height) 250
    set widgets(right_canvas) ""

    set valuesdg sensor_dg

    # Establish connection to database, set to readonly and a 500ms period to wait in case database is locked.
    set dbfile l:/stimuli/grasp/objects.db
    sqlite3 ::gview::dbcmd $dbfile -readonly 1
    dbcmd timeout 500

    
    #initialize time dynamic group table for holding timing
    proc init_time_dg {} {
	set g [dg_create]
	dl_set $g:ds_times [dl_flist]
	dl_set $g:gleft_times [dl_ilist]
	dl_set $g:gright_times [dl_ilist]
	return $g
    }

    if { $gview::test_timing } {
	set timedg [init_time_dg]
	set start_time 0
    }

    proc init_values_dg {} {
	dg_create sensor_dg
	reset_values_dg
    }
    proc reset_values_dg {} {
	set g sensor_dg
	set gview::current_count 0
	dl_set $g:gleft_vals [dl_llist]
	dl_set $g:gright_vals [dl_llist]

	if { [winfo exists .cl] } {
	    .cl delete all
	    .cr delete all
	}

	set ::gview::need_left_mapping 1
	set ::gview::need_right_mapping 1
		

    }
    

    init_values_dg

    proc init_db_dg {} {
	dg_create db_dg
    }

    init_db_dg



    proc read_all_calibs_from_db {} {
    	set gdb db_dg   
    
	dl_set $gdb:ids [dl_ilist]
	dl_set $gdb:calNums [dl_ilist]
	dl_set $gdb:pads [dl_llist]
	dl_set $gdb:channels [dl_llist]
	dl_set $gdb:maxVals [dl_llist]
	
	# Establish connection to database, set to readonly and a 500ms period to wait in case database is locked.
	#set dbfile l:/stimuli/grasp/objects.db
	#sqlite3 dbcmd $dbfile -readonly 1
	#dbcmd timeout 500
	
	# Find id numbers for objects in database
	set ids [::gview::dbcmd eval {SELECT blobID FROM objectsTable}]
	
	#Step through calibration tables, grab data, put into dg
	foreach i $ids {	    
	    # read everything from this objects calibration table
	    set calNum [::gview::dbcmd eval "SELECT calNum FROM calTable${i}"]
	    set pad [::gview::dbcmd eval "SELECT pad FROM calTable${i}"]
	    set channel [::gview::dbcmd eval "SELECT channel FROM calTable${i}"]
	    set maxVal [::gview::dbcmd eval "SELECT maxVal FROM calTable${i}"]

	    # if there isnt a calibration entered yet for this object, skip it
	    if { ![llength $calNum] } continue

	    # not sure exactly
	    dl_local calNums [eval dl_ilist $calNum]
	    dl_local pads [dl_sortByList [eval dl_flist $pad] $calNums]
	    dl_local channels [dl_sortByList [eval dl_flist $channel] $calNums]
	    dl_local maxVals [dl_sortByList [eval dl_flist $maxVal] $calNums]

	    # add to gdb (aka, db_dg)
	    for { set j 0 } { $j < [dl_length $pads] } { incr j }  {
		dl_append $gdb:ids $i
		dl_append $gdb:calNums [expr $j+1]
		dl_append $gdb:pads $pads:$j
		dl_append $gdb:channels $channels:$j
		dl_append $gdb:maxVals $maxVals:$j
	    }
	}
	#dbcmd close
	return $gdb
    }

    proc find_match { vals db } {

	#vals is reading of current sensor
	#db is database of ids, calNums, pads, channels, values
	
	# Get correlations between given vals and all entries in db
	dl_local corrs [dl_pearson [dl_llist $vals] $db:maxVals]

	#corrs is list, size calibrations x 2, with corr coef and confidence
#	puts [dl_tcllist $corrs]

	# Find maxIndex of first values for each correlation pair (pearson corr)
	set ::match [dl_maxIndex [dl_collapse [dl_choose $corrs [dl_llist 0]]]]
	#match is index where best correlation is found
	puts "find_match match index $::match"

	#matchCorrPrint is actual correlation value at max
	set maxCorrPrint [dl_tcllist [dl_choose [dl_get $corrs $::match] 0]]
	puts "corr: $maxCorrPrint"

	puts "find_match values input to match [dl_tcllist [dl_int $vals]]"
	puts "find_match values of match [dl_tcllist [dl_int [dl_get $db:maxVals $::match]]]"
	
	if { $maxCorrPrint > 0.95 } {
	    return [dl_get $db:ids $::match]
	} else {
	    return 0
	}
    }

    proc check_for_chan_map {object db} {
	#grab pad column from this calTable and see if there is an 11. if so, mapping was completed.
	
	# Establish connection to database, set to readonly and a 500ms period to wait in case database is locked.
	#set dbfile l:/stimuli/grasp/objects.db
	#sqlite3 dbcmd $dbfile -readonly 1
	#dbcmd timeout 500
	set pads [::gview::dbcmd eval "SELECT pad FROM calTable${object}"]
	#dbcmd close

	set twelves [dl_find $pads "12"]

	return $twelves
    }
    

    #parse the 30 byte packet coming from the arduino, update the bar graph, 
    proc process_data { ev args } {
	set name [lindex $args 0]
	set val [lindex $args 4]
	switch -glob $name {
	    grasp:data {
		dl_local c [qpcs::dsData $args]
		set gview::status(left,channel) [dl_get $c 0]
		set gview::status(right,channel) [dl_get $c 15]
		set gview::status(left,time) [expr 256*[dl_get $c 1]+[dl_get $c 2]]
		set gview::status(right,time) [expr 256*[dl_get $c 16]+[dl_get $c 17]]
		set gview::status(left,vals) [dl_tcllist [dl_choose $c [dl_fromto 3 15]]]
		set gview::status(right,vals) [dl_tcllist [dl_choose $c [dl_fromto 18 30]]]
		adjust_markers $::gview::widgets(left_canvas) left
		adjust_markers $::gview::widgets(right_canvas) right


		
		##  check to see if the channel has been changed
		
		if {$gview::status(left,channel) != $gview::currentLeft} {
		    set gview::currentLeft $gview::status(left,channel)
		    set gview::current_count 0
		}
		if {$gview::status(right,channel) != $gview::currentRight} {
		    set gview::currentRight $gview::status(right,channel)
		    set gview::current_count 0
		}
		




		#handle channels with no data (presumably getting zeros because of absent channel)
		if {[dl_get $gview::status(left,vals) 11] == 0} {
		    set skipLeft 1
		} else { set skipLeft 0 }
		if {[dl_get $gview::status(right,vals) 11] == 0} {
		    set skipRight 1
		} else { set skipRight 0 }
		if {$skipLeft & $skipRight} {
		    set $gview::current_count $gview::max_count
		}
		


		# collect some readings and identify the two objects
		if { $gview::current_count  < $gview::max_count } {
		    
		    set requestedChans [qpcs::dsGet $gview::datahub grasp:control:channels]

		    set leftChoice [dl_get $requestedChans 0]
		    set rightChoice [dl_get $requestedChans 1]

		    #make sure we're getting info from the correct channel. if so, append.
		    if { $gview::status(left,channel) == $leftChoice & $gview::status(right,channel) == $rightChoice } {
			incr gview::current_count

			dl_append ${gview::valuesdg}:gleft_vals  $gview::status(left,vals)
			dl_append ${gview::valuesdg}:gright_vals $gview::status(right,vals)
		    }

		    #if we're filled up, identify the object
		    if { $gview::current_count == $gview::max_count } {

			if {$gview::datahub == "beast.neuro.brown.edu"} { set MyPCName BEAUTY }
			if {$gview::datahub == "qnx1.neuro.brown.edu" } { set MyPCName STIM1 }
			
		#	set MyPCName $::env(COMPUTERNAME)
		#	if {$MyPCName == "PATRICK" } { set MyPCName BEAUTY }
		#	if {$MyPCName == "SHEINB-DEV-10" } { set MyPCName STIM1 }

			#find max value for all sensors
			set leftCalib  [dl_float [dl_maxs [dl_transpose sensor_dg:gleft_vals]]]
			set rightCalib [dl_float [dl_maxs [dl_transpose sensor_dg:gright_vals]]]

			set leftCalibPrint [dl_tcllist $leftCalib]
			set rightCalibPrint [dl_tcllist $rightCalib]

			#get all calibrations from database
			set gdb [read_all_calibs_from_db]

			######   match left
			#check for match from database
			# Establish connection to database, set to readonly and a 500ms period to wait in case database is locked.
			#set dbfile l:/stimuli/grasp/objects.db
			#sqlite3 dbcmd $dbfile -readonly 1
			#dbcmd timeout 500


			if {!$skipLeft} {

			    puts "matching left"
			    
			    #set dbfile l:/stimuli/grasp/objects.db
			    #sqlite3 dbcmd $dbfile
			    set matchLeft [::gview::dbcmd eval "SELECT ID FROM locationTable WHERE Room = '$MyPCName' AND Side = 0 AND Port = $leftChoice"]
			    set ::leftCalibDB [::gview::dbcmd eval "SELECT maxVal FROM calTable$matchLeft WHERE calNum = 1"]
			    #dbcmd close			    
			    
			    if {[expr {$matchLeft eq ""}]} {
				set matchLeft 0
			    }
			    
			    puts $matchLeft

			    if {$matchLeft > 0} {
				puts "match found with object $matchLeft"
				#set ::leftCalibDB [dl_tcllist [dl_int [dl_get $gdb:maxVals $matchLeft]]]
				#puts [dl_tcllist [dl_get $gdb:maxVals $::match]]
			    } else {
				puts "nothing found left"
				set ::calData $leftCalibPrint
				set ::leftCalibDB $leftCalibPrint
			    }
			} else {set matchLeft 0}
			# store this for other procs
			set ::gview::leftObject $matchLeft

			######   match right
			#check for match from database


			if {!$skipRight} {

			    puts "matching right"
			    
			    #set dbfile l:/stimuli/grasp/objects.db
			    #sqlite3 dbcmd $dbfile
			    set matchRight [::gview::dbcmd eval "SELECT ID FROM locationTable WHERE Room = '$MyPCName' AND Side = 1 AND Port = $rightChoice"]
			    set ::rightCalibDB [::gview::dbcmd eval "SELECT maxVal FROM calTable$matchRight WHERE calNum = 1"]
			    #dbcmd close
			    
			    
			    if {[expr {$matchRight eq ""}]} {
				set matchRight 0
			    }
			    
			    puts $matchRight

			    if {$matchRight > 0} {
				puts "match found with object $matchRight"
			    } else {
				puts "nothing found right"
				set ::calData $rightCalibPrint
				set ::rightCalibDB $rightCalibPrint
			    }
			} else {set matchRight 0}
			# store this for other procs
			set ::gview::rightObject $matchRight

			######    draw the blobs
			puts "drawing_blobs $matchLeft $matchRight"
			draw_blobs $matchLeft $matchRight

			#####   check to see if these objects have had a mapping done yet and update global variables
			if {!$skipLeft} {
			    set mapLeftCheck [check_for_chan_map $matchLeft $gdb]
			} else { set mapLeftCheck -1}
			if {!$skipRight} {
			    set mapRightCheck [check_for_chan_map $matchRight $gdb]
 			} else { set mapRightCheck -1}

			if {$mapLeftCheck == -1} {
			    puts "Left mapping not yet complete"
			    set ::gview::need_left_mapping 1
			    .cl create text 190 10 -text "Pad mapping required" -fill red
			} else {
			    set ::gview::need_left_mapping 0
			}

			if {$mapRightCheck == -1} {
			    puts "Right mapping not yet complete"
			    set ::gview::need_right_mapping 1
			    .cr create text 190 10 -text "Pad mapping required" -fill red
			} else {
			    set ::gview::need_right_mapping 0
			}


			if { !$::gview::need_left_mapping } {
			    # get pad mapping
			    #set dbfile l:/stimuli/grasp/objects.db
			    #sqlite3 dbcmd $dbfile
			    set chansLeft [::gview::dbcmd eval "SELECT channel FROM calTable${matchLeft} WHERE calNum = 1"]
			    set ::padsLeft [::gview::dbcmd eval "SELECT pad FROM calTable${matchLeft} WHERE calNum = 1"]
			    #dbcmd close
			} 

			if { !$::gview::need_right_mapping } {
			    # get pad mapping
			    #set dbfile l:/stimuli/grasp/objects.db
			    #sqlite3 dbcmd $dbfile
			    set chansRight [::gview::dbcmd eval "SELECT channel FROM calTable${matchRight} WHERE calNum = 1"]
			    set ::padsRight [::gview::dbcmd eval "SELECT pad FROM calTable${matchRight} WHERE calNum = 1"]
			    #dbcmd close
			}



			######    draw calibration and min markers
			if {!$skipLeft} {adjust_calibration_markers $::gview::widgets(left_canvas) left $::leftCalibDB}
			if {!$skipRight} {adjust_calibration_markers $::gview::widgets(right_canvas) right $::rightCalibDB}

			#set dbfile l:/stimuli/grasp/objects.db
			#sqlite3 dbcmd $dbfile
			if {!$skipLeft} {set minsLeft [::gview::dbcmd eval "SELECT minVal FROM calTable${matchLeft} WHERE calNum = 1"]}
			if {!$skipRight} {set minsRight [::gview::dbcmd eval "SELECT minVal FROM calTable${matchRight} WHERE calNum = 1"]}
			#dbcmd close
			
			if {!$skipLeft} {adjust_min_markers $::gview::widgets(left_canvas) left $minsLeft}
			if {!$skipRight} {adjust_min_markers $::gview::widgets(right_canvas) right  $minsRight}


			##### tell server min and max for each channel
			if {0} {
			    if {!$skipLeft} {
				qpcs::dsSet $gview::datahub grasp:control:min "0 $gview::status(left,channel) $minsLeft"
				qpcs::dsSet $gview::datahub grasp:control:max "0 $gview::status(left,channel) [dl_tcllist [dl_int $leftCalib]]"
			    }
			    if {!$skipRight} {
				qpcs::dsSet $gview::datahub grasp:control:min "1 $gview::status(right,channel) $minsRight"
				qpcs::dsSet $gview::datahub grasp:control:max "1 $gview::status(right,channel) [dl_tcllist [dl_int $rightCalib]]"
			    }
			}

			#dbcmd close
		    }
		}
	    }
	    
	    grasp:pct:*:* {
		#grab first asterisk value as side, second as channel
		set side [lindex [split $name :] 2]
		set chan [lindex [split $name :] 3]

		#make sure we've done the mapping for this object
		if { $side == 0 && $::gview::need_left_mapping } { return }
		if { $side == 1 && $::gview::need_right_mapping } { return }

		#set appropriate canvas
		set canv [lindex ".cl .cr" $side]

		#set appropriate pad global
		if {$side} {
		    set pads $::padsRight
		} else {
		    set pads $::padsLeft
		}
		
		#convert args to a list
		set pct [dl_tcllist [qpcs::dsData $args]]

#		if {$side} {puts $pct}

		#hex code for grey
		set grey [format %X 100]

		#for each pad, get value from list, convert it to hex
		for {set i 0} {$i < 12} {incr i} {
		    set thisPct [dl_get $pct $i]
		    set green [format %X [expr { int([expr 100 + $thisPct * 1.5]) }]]
		    set thisPad [dl_get $pads $i]

		    $canv itemconfigure pad$thisPad -fill #${grey}${green}${grey}
		}
	    }
	}
    }

    #initialize variables
    proc initialize_vars { server } {
	set data [qpcs::dsGetData $server grasp:data]
	dl_local c [qpcs::dsData $data]
	set gview::status(left,channel) [dl_get $c 0]
	set gview::status(right,channel) [dl_get $c 15]
	set gview::status(left,time) [expr 256*[dl_get $c 1]+[dl_get $c 2]]
	set gview::status(right,time) [expr 256*[dl_get $c 16]+[dl_get $c 17]]
	set gview::status(left,vals) [dl_tcllist [dl_choose $c [dl_fromto 3 15]]]
	set gview::status(right,vals) [dl_tcllist [dl_choose $c [dl_fromto 18 30]]]
    }

    #connect to server
    proc connect_to_server { server { port 4502 } } {
	if { [qpcs::dsRegister $server] != 1 } {
	    error "unable to register with $server"
	}

	qpcs::dsSet $gview::datahub grasp:control:status reset
	qpcs::dsSet $gview::datahub grasp:control:status streaming
	

	#Make sure server status is set to streaming. If not, start it up.	
	set status [qpcs::dsGet $server grasp:control:status]
	if {$status == "streaming"} {
	    puts "we've got the stream"
	} else {
	    puts "we've got no stream! restarting..."
	    qpcs::dsSet $gview::datahub grasp:control:status streaming
	}

	qpcs::dsAddCallback gview::process_data
	qpcs::dsAddMatch $server grasp:data
	qpcs::dsAddMatch $server grasp:pct:*

	set gview::connected 1
    }

    proc disconnect_from_server {} {
	qpcs::dsUnregister 
    }

    proc reconnect {} {
	disconnect_from_server
	connect_to_server $gview::datahub
    }

    #resize the canvas when resizing window
    proc resize { canvas w h } {
	set gview::status(${canvas}_width) $w 
	set gview::status(${canvas}_height) $h
#	gview::update_eye_marker $gview::status(eye_hor) $gview::status(eye_ver)	
    }

    # Create markers for representing values of each of the 12 channels
    proc add_markers { c l } {
	for { set i 0 } { $i < 12 } { incr i } {
	    set j [expr $i + 12]
	    set k [expr $j + 12]
	    $c create rectangle 0 0 10 100 -tag ${l}_${i} -outline white
	    $c create line 500 500 600 600 -tag ${l}_${j} -fill green
	    $c create line 500 500 600 600 -tag ${l}_${k} -fill green 
	}
	$c create line 0 [expr 256-100] 250 [expr 256-100] -fill grey -dash {2 4} 
	$c create line 0 [expr 256-120] 250 [expr 256-120] -fill grey -dash {2 4} 
	$c create line 0 [expr 256-140] 250 [expr 256-140] -fill grey -dash {2 4} 
	$c create line 0 [expr 256-160] 250 [expr 256-160] -fill grey -dash {2 4} 
	$c create line 0 [expr 256-180] 250 [expr 256-180] -fill grey -dash {2 4} 
	$c create line 0 [expr 256-200] 250 [expr 256-200] -fill grey -dash {2 4}
    }

    #Update the height of the bar graph rectangles
    proc adjust_markers { c l } {
	set w $::gview::status(${l}_canvas_width)
	set h $::gview::status(${l}_canvas_height)
	set y0 [expr int($h*0.95)]
	set yscale [expr ($h*0.9)/256.]
	set xstart [expr int($w*0.05)]
	set xwidth [expr int(($w*.9)/12)]
	for { set i 0 } { $i < 12 } { incr i } {
	    set x0 [expr $xstart+($i*$xwidth)]
	    set x1 [expr $x0+$xwidth]
	    set y1 [expr $y0-([lindex $::gview::status($l,vals) $i]*$yscale)]
	    $c coords ${l}_${i} $x0 $y0 $x1 $y1
	}
    }

    proc adjust_calibration_markers { c l calib } {
	set w $::gview::status(${l}_canvas_width)
	set h $::gview::status(${l}_canvas_height)
	set y0 [expr int($h*0.95)]
	set yscale [expr ($h*0.9)/256.]
	set xstart [expr int($w*0.05)]
	set xwidth [expr int(($w*.9)/12)]
	for { set i 0 } { $i < 12 } { incr i } {
	    set j [expr $i + 12]
	    set top [lindex $calib $i]
	    set x0 [expr $xstart+($i*$xwidth)]
	    set x1 [expr $x0+$xwidth]
	    set y1 [expr $y0-($top*$yscale)]
	    $c coords ${l}_${j} $x0 $y1 $x1 $y1
	}
    }

    proc adjust_min_markers { c l min } {
	set w $::gview::status(${l}_canvas_width)
	set h $::gview::status(${l}_canvas_height)
	set y0 [expr int($h*0.95)]
	set yscale [expr ($h*0.9)/256.]
	set xstart [expr int($w*0.05)]
	set xwidth [expr int(($w*.9)/12)]
	for { set i 0 } { $i < 12 } { incr i } {
	    set j [expr $i + 24]
	    set top [lindex $min $i]
	    set x0 [expr $xstart+($i*$xwidth)]
	    set x1 [expr $x0+$xwidth]
	    set y1 [expr $y0-($top*$yscale)]
	    $c coords ${l}_${j} $x0 $y1 $x1 $y1
	}
    }


    
    proc setup_view {} {
	#window title
	wm title . "Sensor Vals"

	set toplevel ""


	#make label and dropdown box containing optional datahubs and add to grid
	labelframe .lfconn -text "Connection"
	set lf .lfconn
	label $lf.datahublabel -text Datahub: -anchor e -width 8
	ttk::combobox $lf.datahub -textvariable gview::datahub -width 24
	$lf.datahub configure -values [list clifford.neuro.brown.edu beast.neuro.brown.edu \
					   qnx1.neuro.brown.edu qnx2.neuro.brown.edu qnx3.neuro.brown.edu]
	grid $lf.datahublabel $lf.datahub -padx 3
	grid $lf -sticky new -columnspan 1

	#if you select something in this box, call reconnect proc to drop connection and connect to new one
	bind $lf.datahub <<ComboboxSelected>> { gview::reconnect }





	##### bar plots


	

	#define canvas for left barplot
	set gview::widgets(left_canvas) \
	    [canvas .ldispc \
		 -width $::gview::status(left_canvas_width) \
		 -height $::gview::status(left_canvas_height) -background black]

	#create bars and adjust them according to current data
	add_markers .ldispc left
	adjust_markers .ldispc left

	#not sure, has to do with resizing left canvas when window is resized?
	bind .ldispc <Configure> { gview::resize left_canvas %w %h } 

	#define canvas for right bar plot
	set gview::widgets(right_canvas) \
	    [canvas .rdispc \
		 -width $::gview::status(right_canvas_width) \
		 -height $::gview::status(right_canvas_height) -background black]

	#create bars and adjust them according to current data
	add_markers .rdispc right
	adjust_markers .rdispc right
	
	bind .rdispc <Configure> { gview::resize right_canvas %w %h } 

	#Add two bar plots
	grid .ldispc .rdispc -sticky nsew




	#### object plots



	
	#define canvas for left object plot
	set gview::widgets(left_objectcanvas) \
	    [canvas .lobjectc \
		 -width $::gview::status(left_canvas_width) \
		 -height $::gview::status(left_canvas_height) -background black]

	$::gview::widgets(left_objectcanvas) create text 100 100 -text "Pad mapping required" -fill white -tag left_tex



	#not sure, has to do with resizing left canvas when window is resized?
	bind .lobjectc <Configure> { gview::resize left_canvas %w %h } 

	#define canvas for right object  plot
	set gview::widgets(right_objectcanvas) \
	    [canvas .robjectc \
		 -width $::gview::status(right_canvas_width) \
		 -height $::gview::status(right_canvas_height) -background black]

	$::gview::widgets(right_objectcanvas) create text 100 100 -text "Pad mapping required" -fill white -tag right_tex

	
	bind .robjectc <Configure> { gview::resize right_canvas %w %h } 

	#not sure what these three lines do. related to resizing behavior
	grid columnconfigure . 0 -weight 1
	grid columnconfigure . 1 -weight 1
	grid rowconfigure . 2 -weight 1
	
	bind . <Control-h> {console show}


    }


    proc draw_blobs { shape_id_l shape_id_r } {

	#open database
	#set dbfile l:/stimuli/grasp/objects.db
	#sqlite3 dbcmd $dbfile
		# Establish connection to database, set to readonly and a 500ms period to wait in case database is locked.
	#set dbfile l:/stimuli/grasp/objects.db
	#sqlite3 dbcmd $dbfile -readonly 1
	#dbcmd timeout 500

	#get the points for specified object
	if {$shape_id_l} {set coords_l [get_shape_coords ::gview::dbcmd $shape_id_l 250 250]}
	if {$shape_id_r} {set coords_r [get_shape_coords ::gview::dbcmd $shape_id_r 250 250]}
	
	#close database
	#dbcmd close

	if { [winfo exists .cl] } {
	    .cl delete all
	    .cr delete all
	} else {	    
	    #start a canvas and put it in a grid
	    canvas .cl -width 250 -height 250 -background black
	    canvas .cr -width 250 -height 250 -background black
	    grid .cl .cr
	}
	
	#for each pad, draw it and give it a mouse binding to change color when you mouse over
	if {$shape_id_l} {
	    set pad_id 0
	    foreach padlist $coords_l {
		incr pad_id
		.cl create line $padlist -tag padback${pad_id} -fill black -width 20
	    }
	    
	    set pad_id 0
	    foreach padlist $coords_l {
		incr pad_id
		.cl create line $padlist -tag pad${pad_id} -fill grey -width 3
		
		.cl bind padback${pad_id} <Enter> ".cl itemconfigure pad${pad_id} -fill green"
		.cl bind padback${pad_id} <Leave> ".cl itemconfigure pad${pad_id} -fill grey"
	    }
	}
	#for each pad, draw it and give it a mouse binding to change color when you mouse over
	if {$shape_id_r} {
	    set pad_id 0
	    foreach padlist $coords_r {
		incr pad_id
		.cr create line $padlist -tag padback${pad_id} -fill black -width 20
	    }
	    
	    set pad_id 0
	    foreach padlist $coords_r {
		incr pad_id
		.cr create line $padlist -tag pad${pad_id} -fill grey -width 3
		
		.cr bind padback${pad_id} <Enter> ".cr itemconfigure pad${pad_id} -fill green"
		.cr bind padback${pad_id} <Leave> ".cr itemconfigure pad${pad_id} -fill grey"
	    }
	}
    }
}

if { $argc > 0 } { set ::gview::datahub [lindex $argv 0] }

gview::initialize_vars $gview::datahub
gview::setup_view
gview::connect_to_server $gview::datahub





