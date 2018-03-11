#!/bin/sh

## Author - atctam
## Version 1.0 - tested on macOS High Sierra version 10.13.2

CPATH="`pwd`"


# Check no. of input arguments
if [ $# -ne 3 ]
then
	echo "USAGE: $0 'filename' 'drop rate' 'error rate'"
	exit
fi

# Start the simulation
echo "Start the server"
osascript -e '
	tell application "Terminal"
		activate
		tell window 1
			do script "cd '$CPATH'; python3 test-server2.py localhost '$2' '$3'"
		end tell
	end tell'

# Pause for 1 second
sleep 1

echo "Start the client"
osascript -e '
	tell application "Terminal"
		activate
		tell window 1
			do script "cd '$CPATH'; python3 test-client2.py localhost '$1' '$2' '$3'"
		end tell
	end tell'
