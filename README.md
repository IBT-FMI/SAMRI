# SAMRI

SAMRI (Small Animal Magnetic Resonance Imaging) - pronounced "Sam-rye" - provides fMRI preprocessing, metadata parsing, and data analysis functions and pipelines.
SAMRI integrates functionalities from a number of other packages (listed under the dependencies section below) to create higher-level tools.
The resulting interfaces aim to maximize reproducibility, simplify batch processing, and minimize the number of function calls required to generate figures and statistical summaries from the raw data.

The package is compatible with small rodent data acquired via Bruker systems.

## Installation

### Gentoo Linux
SAMRI is available for Portage (the package manager of Gentoo Linux, derivative distributions, as well as BSD) via the [Chymeric Overlay](https://github.com/TheChymera/overlay).
Upon enabling the overlay, the package can be emerged:

````
emerge samri
````

### Python Package Manager (Users)
Python's `setuptools` allows you to install Python packages independently of your distribution (or operating system, even).
This approach cannot manage any of our numerous non-Python dependencies (by design) and at the moment will not even manage Python dependencies;
as such, given any other alternative, **we do not recommend this approach**:

````
git clone git@github.com:IBT-FMI/SAMRI.git
cd SAMRI
python setup.py install --user
````

### Python Package Manager (Developers)
Python's `setuptools` allows you to install Python packages independently of your distribution (or operating system, even);
it also allows you to install a "live" version of the package - dynamically linking back to the source code.
This permits you to test code (with real module functionality) as you develop it.
This method is sub-par for dependency management (see above notice), but - as a developer - you should be able to manually ensure that your package manager provides the needed packages.

````
git clone git@github.com:IBT-FMI/SAMRI.git
cd SAMRI
mkdir ~/.python_develop
python setup.py develop --install-dir ~/.python_develop/
echo "export PYTHONPATH=\$HOME/.python_develop:\$PYTHONPATH" >> ~/.bashrc
echo "export PATH=\$HOME/.python_develop:\$PATH" >> ~/.bashrc
source ~/.bashrc
````

## Dependencies:

* [argh](https://github.com/neithere/argh) - in Portage as dev-python/argh
* [Bru2Nii](https://github.com/neurolabusc/Bru2Nii) - in Portage as sci-biology/bru2nii
* [FSL](http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/) - in Portage as sci-biology/fsl
* [nipy](https://github.com/nipy/nipy) - in Portage as sci-libs/nipy
* [nipype](https://github.com/nipy/nipype) - in Portage as sci-libs/nipype
* [scipy](https://www.scipy.org) - thealt LinuxDays test
