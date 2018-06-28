#!/bin/bash

ROOT="$(realpath "$(dirname "$0")")"

function localexec(){
	prog="$1"
	shift
	PORTDIR_OVERLAY="$ROOT" DOTGENTOO_PACKAGE_ROOT="$ROOT/../" $prog "$@"
}

EBUILD="$(find . -name "*.ebuild" | head -n1)"

echo "Installing ebuild $EBUILD"

localexec ebuild "$EBUILD" manifest
localexec emerge "$@" "$EBUILD" --autounmask-continue
FEATURES="test" localexec emerge "$@" "$EBUILD" --autounmask-continue --onlydeps
