__author__ = "Horea Christian"

import argh
from quick import diagnostic

def main():
	argh.dispatch_commands([diagnostic])

if __name__ == '__main__':
	main()
