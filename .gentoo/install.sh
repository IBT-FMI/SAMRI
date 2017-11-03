#!/bin/bash

ROOT="$(realpath "$(dirname "$0")")"

function localmerge(){
	PORTDIR_OVERLAY="$ROOT" DOTGENTOO_PACKAGE_ROOT="$ROOT/../" emerge $*
}

EBUILD="$(find . -name "*.ebuild" | head -n1)"

echo "Installing ebuild $EBUILD"

localmerge "$@" "$EBUILD"
