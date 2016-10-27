__author__ = "Horea Christian"

import argh
from pipelines.nipype_based.quick import diagnostic

def main():
	argh.dispatch_commands([diagnostic])

if __name__ == '__main__':
	main()
