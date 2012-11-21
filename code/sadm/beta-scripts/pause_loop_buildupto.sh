#!/bin/sh

sadmlistcount=`sadm list | grep "pid=" | wc -l`

echo $(ps aux | grep 'sadm.py' | grep "loop" | awk '{print $2}') | xargs kill -s SIGSTOP

#Let things settle down
sleep 2;

while [ $sadmlistcount -ne 0 ]; do
    echo "Waiting for sadm loop action to finish";
    sleep 10;
    sadmlistcount=`sadm list | grep "pid=" | wc -l`;
done

echo "sadm BuildUpTo $1"
sadm BuildUpTo $1

echo $(ps aux | grep 'sadm.py' | grep "loop" | awk '{print $2}') | xargs kill -s SIGCONT

echo "done"

