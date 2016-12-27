__author__ = "Horea Christian"

import argh
from pipelines.nipype_based.quick import diagnostic
from pipelines.nipype_based.diagnostics import diagnose

def main():
	argh.dispatch_commands([diagnostic, diagnose])

if __name__ == '__main__':
	main()
