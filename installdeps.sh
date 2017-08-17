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

mkdir .debug
emerge --sync >> .debug/emerge_sync.txt
emerge wgetpaste
wgetpaste .debug/emerge_sync.txt

echo ""
echo ""
echo "======================="
echo "That was installdeps.sh"
echo "======================="
echo ""
