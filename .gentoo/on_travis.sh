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

echo ""
echo "Preparing Environment:"
echo "~~~~~~~~~~~~~~~~~~~~~~"
export FEATURES="-news"
echo 'ACCEPT_KEYWORDS="~amd64"' >> /etc/portage/make.conf
echo 'ACCEPT_LICENSE="*"' >> /etc/portage/make.conf
echo 'EMERGE_DEFAULT_OPTS="--quiet-build"' >> /etc/portage/make.conf
emerge --sync >> .debug/emerge_sync.txt
emerge dev-vcs/git
cp ".gentoo/files/science" "/etc/portage/repos.conf/"
emaint sync --repo science
emerge wgetpaste >> /dev/null

#Link to the workaroud we reproduce in this section : https://wiki.gentoo.org/wiki/User_talk:Houseofsuns#Migration_to_science_overlay_from_main_tree
#Efforts to more permanently address the issue: https://github.com/gentoo/sci/issues/805
echo ""
echo "Setting Up Eselect for Gentoo Science:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
cp ".gentoo/files/sci-lapack" "/etc/portage/package.mask/"
emerge --oneshot --verbose app-admin/eselect::science >> /dev/null
FEATURES="-preserve-libs" emerge --oneshot --verbose sci-libs/blas-reference::science
eselect blas set reference
FEATURES="-preserve-libs" emerge --oneshot --verbose sci-libs/cblas-reference::science
eselect cblas set reference
FEATURES="-preserve-libs" emerge --oneshot --verbose sci-libs/lapack-reference::science
eselect lapack set reference
FEATURES="-preserve-libs" emerge --oneshot --verbose --exclude sci-libs/blas-reference --exclude sci-libs/cblas-reference --exclude sci-libs/lapack-reference `eix --only-names --installed --in-overlay science`
revdep-rebuild
echo ""
echo "Environment Ready, Emerging:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
emerge emerge $(<.gentoo/deps)

echo ""
echo ""
echo "Pastebinning Large Logs:"
echo "~~~~~~~~~~~~~~~~~~~~~~~~"
echo "emerge_sync.txt : "
wgetpaste .debug/emerge_sync.txt
