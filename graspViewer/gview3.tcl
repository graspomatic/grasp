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


    proc cycle {start} {
	set MyPCName $::env(COMPUTERNAME)
	if {$MyPCName == "PATRICK" } { set MyPCName BEAUTY }
	if {$MyPCName == "SHEINB-DEV-10" } { set MyPCName STIM1 }

	if {$start} {
	    puts "Cycling through objects to update database"
	    set gview::cycleCount 0

	    # clear out all location data for this rooms objects
	    set dbfile l:/stimuli/grasp/objects2.db
	    sqlite3 dbcmd $dbfile

	    dbcmd eval "UPDATE locationTable Set Side=-1 WHERE Room='$MyPCName'"
	    dbcmd eval "UPDATE locationTable Set Port=-1 WHERE Room='$MyPCName'"
	    dbcmd close

	} else {
	    #if we're here, it means object(s) have been mapped
	    if {$gview::cycleCount > 7} {
            return
	    }
	    #if we're here, it means we've mapped objects while we're cycling through
	    puts "objects are 0 $gview::cycleCount $::gview::leftObject and 1 $gview::cycleCount $::gview::rightObject"
	    #add to database

	    set dbfile l:/stimuli/grasp/objects2.db
	    sqlite3 dbcmd $dbfile



	    if {$gview::leftObject} {
    		if { [llength [dbcmd eval "SELECT Room FROM locationTable WHERE ID = $gview::leftObject"]] > 0} {
    		    dbcmd eval "UPDATE locationTable Set Room='$MyPCName', Side=0, Port=$gview::cycleCount WHERE ID = $gview::leftObject"
    		} else {
    		    dbcmd eval "INSERT INTO locationTable (ID, Room, Side, Port) VALUES ($gview::leftObject, '$MyPCName', 0, $gview::cycleCount)"
    		}

	    }
	    if {$gview::rightObject} {
    		if { [llength [dbcmd eval "SELECT Room FROM locationTable WHERE ID = $gview::rightObject"]] > 0} {
    		    dbcmd eval "UPDATE locationTable Set Room='$MyPCName', Side=1, Port=$gview::cycleCount WHERE ID = $gview::rightObject"
    		} else {
    		    dbcmd eval "INSERT INTO locationTable (ID, Room, Side, Port) VALUES ($gview::rightObject, '$MyPCName', 1, $gview::cycleCount)"
    		}
	    }
	    dbcmd close

	    incr gview::cycleCount
	}




	### change channels
	puts "round $gview::cycleCount"
	set ::gview::leftChanBox $gview::cycleCount
	set ::gview::rightChanBox $gview::cycleCount
	choose_chans
    }





    proc add_calib_to_db {} {

	puts $::entryBoxValue

	# find highest value calNumber entered for this object so far
	set dbfile l:/stimuli/grasp/objects2.db
	sqlite3 dbcmd $dbfile
	set calNum [dbcmd eval "SELECT calNum FROM calTable${::entryBoxValue}"]
	dbcmd close
	if { [llength $calNum] > 0 } {
	    set calSorted [lsort -decreasing $calNum]
	    set calMax [lindex $calSorted 0]
	} else {
	    set calMax 0
	}
	set ::calNum [expr $calMax + 1]


	#now we know objectID (::entryBoxValue), calNum (::calNum), and calibration data (::calData)
	# put calibration data into
	sqlite3 dbcmd $dbfile
	for {set i 0} {$i<12} {incr i} {
	    set pad [expr $i + 1]
	    dbcmd eval "INSERT INTO calTable${::entryBoxValue} VALUES ($::calNum, 0, $pad ,0, [lindex $::calData $i] , 0 )"
	}
	dbcmd close
    }



    proc get_user_input { request } {

	if { [winfo exists .guiEntry] } {
	    destroy .guiEntry
	}

	set w .guiEntry

	toplevel $w
	wm title $w $request

	pack [label $w.request -text $request]
	pack [entry $w.xmpl -text "This is an example" -textvariable ::entryBoxValue]
	#pack [button $w.ok -text OK -command [list destroy $w]]

	bind $w <Return> {
	    destroy .guiEntry
	    gview::add_calib_to_db
	}

	focus -force .guiEntry
	if {$gview::cycleCount > 7} {
	    tkwait window .guiEntry
	    if {$::entryBoxValue} {
		return $::entryBoxValue
	    } else {
		return 0
	    }
	} else {
	    destroy .guiEntry
	    return 0
	}
    }




    proc read_all_calibs_from_db {} {
    	set gdb db_dg

	dl_set $gdb:ids [dl_ilist]
	dl_set $gdb:calNums [dl_ilist]
	dl_set $gdb:pads [dl_llist]
	dl_set $gdb:channels [dl_llist]
	dl_set $gdb:maxVals [dl_llist]

	set dbfile l:/stimuli/grasp/objects2.db
	sqlite3 dbcmd $dbfile

	# Find id numbers for objects in database
	set ids [dbcmd eval {SELECT objectID FROM objectsTable}]

	#Step through calibration tables, grab data, put into dg
	foreach i $ids {
	    # read everything from this objects calibration table
	    set calNum [dbcmd eval "SELECT calNum FROM calTable${i}"]
	    set pad [dbcmd eval "SELECT pad FROM calTable${i}"]
	    set channel [dbcmd eval "SELECT channel FROM calTable${i}"]
	    set maxVal [dbcmd eval "SELECT maxVal FROM calTable${i}"]

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
	dbcmd close
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

	if { $maxCorrPrint > 0.991 } {
	    return [dl_get $db:ids $::match]
	} else {
	    return 0
	}
    }

    proc check_for_chan_map {object db} {
	#grab pad column from this calTable and see if there is an 11. if so, mapping was completed.

	set dbfile l:/stimuli/grasp/objects2.db
	sqlite3 dbcmd $dbfile
	set pads [dbcmd eval "SELECT pad FROM calTable${object}"]
	dbcmd close

	set twelves [dl_find $pads "12"]

	return $twelves
    }


    proc ask_user_to_touch {chan} {

	if { [winfo exists .guiGrasp] } {
	    destroy .guiGrasp
	}

	set wg .guiGrasp

	toplevel $wg
	wm title $wg "touch $chan"
	wm geometry $wg +200+200

	pack [label $wg.request -text "touch $chan"]

	bind $wg <Return> {
	    destroy .guiGrasp
	}

	focus -force .guiGrasp

	tkwait window .guiGrasp
    }


    proc  map_chans_to_pads { side  id } {

        dl_local padList [dl_create int]
	set complete 0
	while {!$complete} {
	    puts $complete
	    if { $side == 0 } {
		puts "mapping left channels with object $id"

		#ask user to touch this pad and press enter
		ask_user_to_touch nothing

		set baseline $gview::status(left,vals)

		for {set i 1} {$i <= 12} {incr i} {
		    #highlight this pad
		    .cl itemconfigure pad$i -fill green

		    #ask user to touch this pad and press enter
		    ask_user_to_touch left$i

		    #grab the values
		    set sample $gview::status(left,vals)

		    #un-highlight this pad
		    .cl itemconfigure pad$i -fill grey

		    #attempt to identify channel which corresponds to the pad user touched
		    set difference [dl_sub $baseline $sample]
		    puts [dl_tcllist $difference]
		    set pad [dl_maxIndex $difference]
		    puts $pad

		    #add to list
		    dl_concat $padList $pad
		}
	    } else {
		puts "mapping right channels with object $id"

		#ask user to touch this pad and press enter
		ask_user_to_touch nothing

		set baseline $gview::status(right,vals)

		for {set i 1} {$i <= 12} {incr i} {
		    #highlight this pad
		    .cr itemconfigure pad$i -fill green

		    #ask user to touch this pad and press enter
		    ask_user_to_touch right$i

		    #grab the values
		    set sample $gview::status(right,vals)

		    #un-highlight this pad
		    .cr itemconfigure pad$i -fill grey

		    #attempt to identify channel which corresponds to the pad user touched
		    set difference [dl_sub $baseline $sample]
		    puts [dl_tcllist $difference]
		    set pad [dl_maxIndex $difference]
		    puts $pad

		    #add to list
		    dl_concat $padList $pad
		}
	    }

	    # make sure we have 12 uniques
	    puts [dl_tcllist $padList]

	    set uniques [dl_length [dl_unique $padList]]
	    puts  "number unique: $uniques"
	    if {$uniques < 12} {
#		set complete 1
		puts "agh we need to redo this"
	    } else {
		set complete 1
	    }



	}

	puts "mapping succesful, adding pad map to database"

	set dbfile l:/stimuli/grasp/objects2.db
	sqlite3 dbcmd $dbfile
	for { set i 1 } {$i <= 12} { incr i } {
	    set thisChan [dl_get $padList [expr $i-1]]
	    set thisChan [expr $thisChan + 1]
	    dbcmd eval "UPDATE calTable${id} SET pad = $i WHERE calNum = 1 AND channel = $thisChan"
	}
	dbcmd close

	puts "adding min values to database"
	#figure out active channel
	set full30 [dl_tcllist [qpcs::dsData [qpcs::dsGetData $gview::datahub grasp:data]]]

	if {!$side} {
	    set chan [lindex $full30 0]
	} else {
	    set chan [lindex $full30 15]
	}

	qpcs::dsSet $gview::datahub grasp:control:reset "$side $chan"
	ask_user_to_touch everything
	set mins [dl_tcllist [qpcs::dsData [qpcs::dsGetData $gview::datahub grasp:min:$side:$chan]]]
	puts $mins
	sqlite3 dbcmd $dbfile
	for { set i 0 } {$i < 12} { incr i } {
	    set thisChan [expr $i + 1]
	    set thisVal [lindex $mins $i]
	    dbcmd eval "UPDATE calTable${id} SET minVal = $thisVal WHERE calNum = 1 AND channel = $thisChan"
	}
	dbcmd close


	#have user stop touching so we can reset and find calibration for this object
	ask_user_to_touch nothing
	reset_values_dg
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

		    #set requestedChans [qpcs::dsGet $gview::datahub grasp:control:channels]

		    #puts $requestedChans

		   # puts [llength $requestedChans]

		    #if { [llength $requestedChans] == 0 } { return }

		    #set leftChoice [dl_get $requestedChans 0]
		    #set rightChoice [dl_get $requestedChans 1]

		    set leftChoice $gview::leftChanBox
		    set rightChoice $gview::rightChanBox





		    #make sure we're getting info from the correct channel. if so, append.
		    if { $gview::status(left,channel) == $leftChoice & $gview::status(right,channel) == $rightChoice } {
			incr gview::current_count

			dl_append ${gview::valuesdg}:gleft_vals  $gview::status(left,vals)
			dl_append ${gview::valuesdg}:gright_vals $gview::status(right,vals)
		    }

		    #if we're filled up, identify the object
		    if { $gview::current_count == $gview::max_count } {

			#find max value for all sensors
			set leftCalib  [dl_float [dl_maxs [dl_transpose sensor_dg:gleft_vals]]]
			set rightCalib [dl_float [dl_maxs [dl_transpose sensor_dg:gright_vals]]]

			set leftCalibPrint [dl_tcllist $leftCalib]
			set rightCalibPrint [dl_tcllist $rightCalib]

			#get all calibrations from database
			set gdb [read_all_calibs_from_db]

			######   match left
			#check for match from database
			if {!$skipLeft} {
			    puts "matching left"
			    puts [dl_tcllist $leftCalib]
			    set matchLeft [find_match $leftCalib $gdb]
			    puts $matchLeft

			    if {$matchLeft > 0} {
				puts "match found with object $matchLeft"
				set ::leftCalibDB [dl_tcllist [dl_int [dl_get $gdb:maxVals $::match]]]
				#puts [dl_tcllist [dl_get $gdb:maxVals $::match]]
			    } else {
				puts "nothing found left"
				set ::calData $leftCalibPrint
				set ::leftCalibDB $leftCalibPrint
				set matchLeft [get_user_input "What is the left object's ID?"]
			    }
			} else {set matchLeft 0}
			# store this for other procs
			set ::gview::leftObject $matchLeft

			######    match right
			if {!$skipRight} {
			    puts "matching right"

			    #check for match from database
			    set matchRight [find_match $rightCalib $gdb]

			    if {$matchRight > 0} {
				puts "match found object $matchRight"
				set ::rightCalibDB [dl_tcllist [dl_int [dl_get $gdb:maxVals $::match]]]
			    } else {
				puts "nothing found right"
				set ::calData $rightCalibPrint
				set ::rightCalibDB $rightCalibPrint
				set matchRight [get_user_input "What is the right object's ID?"]
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
			    set dbfile l:/stimuli/grasp/objects2.db
			    sqlite3 dbcmd $dbfile
			    set chansLeft [dbcmd eval "SELECT channel FROM calTable${matchLeft} WHERE calNum = 1"]
			    set ::padsLeft [dbcmd eval "SELECT pad FROM calTable${matchLeft} WHERE calNum = 1"]
			    dbcmd close
			}

			if { !$::gview::need_right_mapping } {
			    # get pad mapping
			    set dbfile l:/stimuli/grasp/objects2.db
			    sqlite3 dbcmd $dbfile
			    set chansRight [dbcmd eval "SELECT channel FROM calTable${matchRight} WHERE calNum = 1"]
			    set ::padsRight [dbcmd eval "SELECT pad FROM calTable${matchRight} WHERE calNum = 1"]
			    dbcmd close
			}



			######    draw calibration and min markers
			if {!$skipLeft} {adjust_calibration_markers $::gview::widgets(left_canvas) left $::leftCalibDB}
			if {!$skipRight} {adjust_calibration_markers $::gview::widgets(right_canvas) right $::rightCalibDB}

			set dbfile l:/stimuli/grasp/objects2.db
			sqlite3 dbcmd $dbfile
			if {!$skipLeft} {set minsLeft [dbcmd eval "SELECT minVal FROM calTable${matchLeft} WHERE calNum = 1"]}
			if {!$skipRight} {set minsRight [dbcmd eval "SELECT minVal FROM calTable${matchRight} WHERE calNum = 1"]}
			dbcmd close

			if {!$skipLeft} {
#			    puts "minsLeft: $minsLeft length: [llength $minsLeft]"
			    if { [llength $minsLeft] > 0 } {
				adjust_min_markers $::gview::widgets(left_canvas) left $minsLeft
			    } else {
				adjust_min_markers $::gview::widgets(left_canvas) left "0 0 0 0 0 0 0 0 0 0 0 0"
			    }

			}
			if {!$skipRight} {
			    if { [llength $minsRight] > 0 } {
				adjust_min_markers $::gview::widgets(right_canvas) right  $minsRight

			    } else {
				adjust_min_markers $::gview::widgets(left_canvas) left "0 0 0 0 0 0 0 0 0 0 0 0"
			    }
			}

			puts "past drawing calib markers"


			##### tell server min and max for each channel

			if {!$skipLeft} {
			    qpcs::dsSet $gview::datahub grasp:control:min "0 $gview::status(left,channel) $minsLeft"
			    qpcs::dsSet $gview::datahub grasp:control:max "0 $gview::status(left,channel) [dl_tcllist [dl_int $leftCalib]]"
			}
			if {!$skipRight} {
			    qpcs::dsSet $gview::datahub grasp:control:min "1 $rightChoice $minsRight"
			    qpcs::dsSet $gview::datahub grasp:control:max "1 $rightChoice [dl_tcllist [dl_int $rightCalib]]"
			}

			##### write information to database table
			cycle 0
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
	if { [qpcs::dsGet $server grasp:status] == "streaming" } {
	    set data [qpcs::dsGetData $server grasp:data]
	    dl_local c [qpcs::dsData $data]
	    set gview::status(left,channel) [dl_get $c 0]
	    set gview::status(right,channel) [dl_get $c 15]
	    set gview::status(left,time) [expr 256*[dl_get $c 1]+[dl_get $c 2]]
	    set gview::status(right,time) [expr 256*[dl_get $c 16]+[dl_get $c 17]]
	    set gview::status(left,vals) [dl_tcllist [dl_choose $c [dl_fromto 3 15]]]
	    set gview::status(right,vals) [dl_tcllist [dl_choose $c [dl_fromto 18 30]]]
	} else {
	    set gview::status(left,channel) 0
	    set gview::status(right,channel) 0
	    set gview::status(left,time) 0
	    set gview::status(right,time) 0
	    set gview::status(left,vals) [dl_tcllist [dl_repeat 128 12]]
	    set gview::status(right,vals) [dl_tcllist [dl_repeat 128 12]]
	}

    }

    #connect to server
    proc connect_to_server { server { port 4502 } } {
	if { [qpcs::dsRegister $server] != 1 } {
	    error "unable to register with $server"
	}

	qpcs::dsSet $gview::datahub grasp:control:status reset
	qpcs::dsSet $gview::datahub grasp:control:status streaming

	puts "Grasp Status: [qpcs::dsGet $gview::datahub grasp:status]"

	#Make sure server status is set to streaming. If not, start it up.
	set status [qpcs::dsGet $server grasp:status]
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


    proc choose_chans {} {
	set left $gview::leftChanBox
	set right $gview::rightChanBox

	puts "Chose $left and $right"

	qpcs::dsSet $gview::datahub grasp:control:channels "$left $right"
	reset_values_dg
    }



    proc setup_view {} {
	#window title
	wm title . "Grasp Viewer"

	set toplevel ""


	# A menubar with some options (server info...etc)
	set menu [menu $toplevel.menu -tearoff 0]
	. configure -menu $menu
	foreach m {File Edit View Actions Tools Help} {
	    set $m [menu $menu.menu$m -tearoff 0]
	    $menu add cascade -label $m -menu $menu.menu$m
	}

	$File add separator
	$File add command -label "Exit" -command exit \
		-accelerator (Ctrl-x)

	$View add command -label "double click dg to view" -state disable
	$View add separator
	$View add command -label "Console" -command \
		{console show} -accelerator (Ctrl-h)

# 	$Actions add command -label "Rename" -command \
# 		{dgfind::renameFilesWin} -accelerator (Ctrl-r)
# 	$Actions add command -label "Delete" -command \
# 		{dgfind::deleteFilesWin} -accelerator (Ctrl-d)

	$Help add command -label "Shortcut Commands" -command \
	    dgfind::shortcutWin
	$Help add separator
	$Help add command -label "About"


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


	labelframe .lfmap -text "Map Objects"
	set lf .lfmap
	button $lf.mapleft -text "Map Left" -width 8 -command {
	    gview::map_chans_to_pads 0 $::gview::leftObject
	}

	button $lf.mapright -text "Map Right" -width 8 -command {
	    gview::map_chans_to_pads 1 $::gview::rightObject
	}
	button $lf.scan -text "Scan objects" -width 10 -command {
	    gview::cycle 1
	}
	grid $lf.mapleft $lf.mapright $lf.scan -padx 10
	grid $lf -sticky new -column 1 -row 0


	#make label and dropdown box containing optional left channels
	labelframe .lfch_l
	set lf .lfch_l
	label $lf.leftChanLabel -text "Left Chan:" -anchor e -width 10
	ttk::combobox $lf.leftChanBox -textvariable gview::leftChanBox -width 20
	$lf.leftChanBox configure -values [list 0 1 2 3 4 5 6 7]
	grid $lf.leftChanLabel $lf.leftChanBox -padx 3
#	grid $lf -sticky new -columnspan 1

	#if you select something in this box, call reconnect proc to drop connection and connect to new one
	bind $lf.leftChanBox <<ComboboxSelected>> { gview::choose_chans }


	#make label and dropdown box containing optional right channels
	labelframe .lfch_r
	set lf .lfch_r
	label $lf.rightChanLabel -text "Right Chan:" -anchor e -width 10
	ttk::combobox $lf.rightChanBox -textvariable gview::rightChanBox -width 20
	$lf.rightChanBox configure -values [list 0 1 2 3 4 5 6 7 ]
	grid $lf.rightChanLabel $lf.rightChanBox -padx 3
#	grid $lf -sticky new -columnspan 1

	#if you select something in this box, call reconnect proc to drop connection and connect to new one
	bind $lf.rightChanBox <<ComboboxSelected>> { gview::choose_chans }

	# add left and right choice boxes
	grid .lfch_l .lfch_r -sticky new




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
	set dbfile l:/stimuli/grasp/objects2.db
	sqlite3 dbcmd $dbfile

	#get the points for specified object
	if {$shape_id_l} {set coords_l [get_shape_coords dbcmd $shape_id_l 250 250]}
	if {$shape_id_r} {set coords_r [get_shape_coords dbcmd $shape_id_r 250 250]}

	#close database
	dbcmd close

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
set ::gview::leftChanBox 0
set ::gview::rightChanBox 0

gview::initialize_vars $gview::datahub
gview::setup_view
gview::connect_to_server $gview::datahub
gview::choose_chans
