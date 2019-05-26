from setuptools import setup, find_packages

setup(
	name="SAMRI",
	version="9999",
	description = "Small animal magnetic resonance imaging via Python.",
	author = "Horea Christian",
	author_email = "horea.christ@yandex.com",
	url = "https://github.com/IBT-FMI/SAMRI",
	keywords = ["fMRI", "pipelines", "data analysis", "bruker"],
	classifiers = [],
	install_requires = [],
	provides = ["samri"],
	packages = [
		"samri",
		"samri.analysis",
		"samri.fetch",
		"samri.optimization",
		"samri.pipelines",
		"samri.plotting",
		"samri.report",
		],
	include_package_data=True,
	extras_require = {
		'doc': ['Sphinx>=1.4', 'numpydoc'],
		}
	entry_points = {'console_scripts' : \
			['SAMRI = samri.cli:main']
		}
	)
