#!/usr/bin/env bash

echo ""
echo "=================="
echo "Gentoo Test Script"
echo "=================="

echo ""
echo "Setting up Directory Structure:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
mkdir .debug
mkdir /etc/portage/repos.conf
mkdir /etc/portage/package.mask

echo ""
echo "Preparing Environment:"
echo "~~~~~~~~~~~~~~~~~~~~~~"
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
