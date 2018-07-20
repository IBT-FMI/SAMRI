__author__ = "Horea Christian"

import argh
from samri.pipelines.diagnostics import diagnose
from samri.pipelines.reposit import bru2bids
from samri.pipelines.preprocess import generic, legacy
from samri.pipelines.glm import l1

def main():
	# Adapting function names to 1-level hierarchy
	full.__name__ = 'full-prep'
	argh.dispatch_commands([diagnose, bru2bids, l1, full])

if __name__ == '__main__':
	main()
