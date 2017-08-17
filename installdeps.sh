#!/usr/bin/env bash

echo ""
echo "======================"
echo "This is installdeps.sh"
echo "======================"
echo ""
echo "Contents of"
pwd
echo "are:"
ls
echo ""
echo "Contents of"
echo "/home" 
echo "are:"
ls "/home" 
echo ""

emerge --sync >> _emerge_sync.txt

echo "======================="
echo "That was installdeps.sh"
echo "======================="
echo ""
