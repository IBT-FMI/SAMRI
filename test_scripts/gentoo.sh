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
ls -lah /etc/portage/repos.conf
echo "PWD:"
pwd

echo ""
echo "Preparing Environment:"
echo "~~~~~~~~~~~~~~~~~~~~~~"
eselect profile set 1
export FEATURES="-news"
emerge dev-vcs/git >> /dev/null
cp "test_scripts/gentoo_files/science" "/etc/portage/repos.conf/"
emerge --sync >> .debug/emerge_sync.txt
emerge wgetpaste >> /dev/null
echo "PWD:"
pwd

#Link to the workaroud we reproduce in this section : https://wiki.gentoo.org/wiki/User_talk:Houseofsuns#Migration_to_science_overlay_from_main_tree
#Efforts to more permanently address the issue: https://github.com/gentoo/sci/issues/805
echo ""
echo "Setting Up Eselect for Gentoo Science:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
cp "${HOME}/SAMRI/test_scripts/gentoo_files/sci-lapack" "/etc/portage/package.mask/"
ls "${HOME}/SAMRI/test_scripts/gentoo_files" -lah
ls "${HOME}/SAMRI/test_scripts/" -lah
ls "${HOME}/SAMRI/" -lah
ls "${HOME}" -lah
echo "PWD:"
pwd

echo ""
echo "Environment Ready, Emerging:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~"


echo ""
echo ""
echo "Pastebinning Large Logs:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~"
echo "emerge_sync.txt : "
wgetpaste .debug/emerge_sync.txt
