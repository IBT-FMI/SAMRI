__author__ = "Horea Christian"

import argh
try:
	from pipelines.diagnostics import diagnose
except ImportError:
	from .pipelines.diagnostics import diagnose


def main():
	argh.dispatch_commands([diagnose])

if __name__ == '__main__':
	main()
