from setuptools import setup, find_packages

packages = find_packages(exclude=('samri.tests*', 'samri.*.tests*'))

setup(
	name="SAMRI",
	version="9999",
	description = "Small animal magnetic resonance imaging via Python.",
	author = "Horea Christian",
	author_email = "chr@chymera.eu",
	url = "https://github.com/IBT-FMI/SAMRI",
	keywords = ["fMRI", "pipelines", "data analysis", "bruker"],
	classifiers = [],
	install_requires = [],
	provides = ["samri"],
	packages = packages,
	include_package_data=True,
	extras_require = {
		},
	entry_points = {'console_scripts' : \
			['SAMRI = samri.cli:main']
		},
	)
