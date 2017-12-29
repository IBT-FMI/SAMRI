__author__ = "Horea Christian"

import argh
from samri.pipelines.diagnostics import diagnose
from samri.pipelines.reposit import bru2bids


def main():
	argh.dispatch_commands([diagnose, bru2bids])

if __name__ == '__main__':
	main()
