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
cat /etc/portage/package.mask
mkdir /etc/portage/package.mask

echo ""
echo "Preparing Environment:"
echo "~~~~~~~~~~~~~~~~~~~~~~"
export FEATURES="-news"
cp "test_scripts/gentoo_files/science" "/etc/portage/repos.conf/"

#Link to the workaroud we reproduce in this section : https://wiki.gentoo.org/wiki/User_talk:Houseofsuns#Migration_to_science_overlay_from_main_tree
#Efforts to more permanently address the issue: https://github.com/gentoo/sci/issues/805
echo ""
echo "Setting Up Eselect for Gentoo Science:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
cp "${HOME}/SAMRI/test_scripts/gentoo_files/sci-lapack" "/etc/portage/package.mask/"


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
