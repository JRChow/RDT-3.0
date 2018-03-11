#!/bin/sh

## Author - atctam
## Version 1.0 - tested on Ubuntu 16.04.3 LTS

# Check no. of input arguments
if [ $# -ne 3 ]
then
	echo "USAGE: $0 'filename' 'drop rate' 'error rate'"
	exit
fi

# Start the simulation
echo "Start the server"
gnome-terminal --command="bash -c \"python3 test-server2.py localhost '$2' '$3'; exec bash\" "

# Pause for 1 second
sleep 1

echo "Start the client"
gnome-terminal --command="bash -c \"python3 test-client2.py localhost '$1' '$2' '$3'; exec bash\" "
