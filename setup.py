from setuptools import setup, find_packages

setup(
	name="SAMRI",
	version="",
	description = "Small animal magnetic resonance imaging via Python.",
	author = "Horea Christian",
	author_email = "horea.christ@yandex.com",
	url = "https://github.com/TheChymera/SAMRI",
	keywords = ["fMRI", "pipelines", "data analysis", "bruker"],
	classifiers = [],
	install_requires = [],
	provides = ["samri"],
	packages = ["samri"],
	include_package_data=True,
	entry_points = {'console_scripts' : \
			['SAMRI = samri.cli:main']
		}
	)
