#!/bin/sh
# \
exec expect -f "$0" ${1+"$@"}
set branch [lindex $argv 1]
spawn sadm init [lindex $argv 0]
sleep 1
expect "Add it (plus missing dependencies)?"
sleep 1
send "y\r"
expect "Where would you like to branch from:"
send "trunk\r"
sleep 1
expect "Remove incomplete sandbox:"
sleep 1
send "n\r"
expect eof

