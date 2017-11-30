__author__ = "Horea Christian"

import argh
from samri.pipelines.diagnostics import diagnose


def main():
	argh.dispatch_commands([diagnose])

if __name__ == '__main__':
	main()
