__author__ = "Horea Christian"

import argh
from samri.pipelines.diagnostics import diagnose
from samri.pipelines.reposit import bru2bids
from samri.pipelines.glm import l1

def main():
	argh.dispatch_commands([diagnose, bru2bids, l1])

if __name__ == '__main__':
	main()
