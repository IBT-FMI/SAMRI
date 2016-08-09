from setuptools import setup, find_packages

setup(
	name="chyMRI",
	version="",
	description = "Animal fMRI pipelines",
	author = "Horea Christian",
	author_email = "h.chr@mail.ru",
	url = "https://github.com/TheChymera/chyMRI",
	keywords = ["fMRI", "pipelines", "data analysis"],
	classifiers = [],
	install_requires = [],
	provides = ["chyMRI"],
	packages = ["chyMRI"],
	include_package_data=True,
	entry_points = {'console_scripts' : \
			['chyMRI = chyMRI.cli:main']
		}
	)
