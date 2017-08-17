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

echo ""
echo "Preparing Environment:"
echo "~~~~~~~~~~~~~~~~~~~~~~"
mkdir .debug
export FEATURES="-news"

echo ""
echo "Environment Ready, Emerging:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

emerge --sync >> .debug/emerge_sync.txt
emerge wgetpaste >> /dev/null

echo ""
echo ""
echo "Pastebinning Large Logs:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~"
echo "emerge_sync.txt : "
wgetpaste .debug/emerge_sync.txt

echo ""
echo ""
echo "======================="
echo "That was installdeps.sh"
echo "======================="
echo ""
