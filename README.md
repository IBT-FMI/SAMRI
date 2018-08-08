![SAMRI](./logo.svg)

# SAMRI
[![Build Status](https://travis-ci.org/IBT-FMI/SAMRI.svg?branch=master)](https://travis-ci.org/IBT-FMI/SAMRI)

SAMRI (Small Animal Magnetic Resonance Imaging) - pronounced "Sam-rye" - provides fMRI preprocessing, metadata parsing, and data analysis functions and pipelines.
SAMRI integrates functionalities from a number of other packages (listed under the [dependencies section](#dependencies) below) to create higher-level tools.
The resulting interfaces aim to maximize reproducibility, simplify batch processing, and minimize the number of function calls required to generate figures and statistical summaries from the raw data.

The package is compatible with small rodent data acquired via Bruker ParaVision.

## Examples

To execute the examples below, actual 	small animal imaging data is required.
This section includes lines to fetch such data (starting with `wget` and `unzip`), which can however be omitted if data is already present.
If dependencies were managed via Portage (e.g. on Gentoo Linux) mouse brain atlases may already be present under `/usr/share/mouse-brain-atlases` and test data under `/usr/share/samri_bindata`.

```
wget http://chymera.eu/distfiles/mouse-brain-atlases-0.2.20180719.tar.xz
tar xf mouse-brain-atlases-0.2.20180719.tar.xz
wget http://chymera.eu/distfiles/samri_bindata-0.1.2.tar.xz
tar xf samri_bindata-0.1.2.tar.xz
```

#### Convert Bruker ParaVision raw directories to BIDS-compliant NIfTI collections:
All listed examples beyond this one necessitate a BIDS-compliant NIfTI directory tree, as produced via the following command:
```
SAMRI bru2bids -o . -f '{"acquisition":["EPI"]}' -s '{"acquisition":["TurboRARE"]}' samri_bindata
```

#### Run a spatio-temporal signal decomposition (ICA via FSL):
This executes minimal preprocessing and [FSL's MELODIC](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/MELODIC), and is very useful for fast, qualitative diagnosis of functional measurement quality and/or stimulation efficacy.
```
SAMRI diagnose bids
```

#### Run a full preprocessing pipeline (including template registration) on the BIDS input:
```
SAMRI full-prep -o preprocessing --registration-mask mouse-brain-atlases/dsurqec_200micron_mask.nii --functional-registration-method composite --negative-contrast-agent bids mouse-brain-atlases/dsurqec_200micron.nii
```

## Installation

Depending on your preferred package manager you may choose one of the following methods:

#### Portage (e.g. on Gentoo Linux):
SAMRI is available via Portage (the package manager of Gentoo Linux, derivative distributions, and installable on [any other Linux distribution](https://wiki.gentoo.org/wiki/Project:Prefix), or BSD) via the [Chymeric Overlay](https://github.com/TheChymera/overlay).
Upon enabling the overlay, the package can be emerged:

````
emerge samri
````

Alternatively, the live (i.e. latest) version of the package can be installed along with all of its dependencies without the need to enable to overlay:

```
git clone git@github.com:IBT-FMI/SAMRI.git
cd SAMRI/.gentoo
./install.sh
```

#### Python Package Manager (Users):
Python's `setuptools` allows you to install Python packages independently of your distribution (or operating system, even).
This approach cannot manage any of our numerous non-Python dependencies (by design) and at the moment will not even manage Python dependencies;
as such, given any other alternative, **we do not recommend this approach**:

````
git clone git@github.com:IBT-FMI/SAMRI.git
cd SAMRI
python setup.py install --user
````

If you are getting a `Permission denied (publickey)` error upon trying to clone, you can either:

* [Add an SSH key](https://help.github.com/articles/adding-a-new-ssh-key-to-your-github-account/) to your GitHub account.
* Pull via the HTTPS link `git clone https://github.com/IBT-FMI/SAMRI.git`.

#### Python Package Manager (Developers):
Python's `setuptools` allows you to install Python packages independently of your distribution (or operating system, even);
it also allows you to install a "live" version of the package - dynamically linking back to the source code.
This permits you to test code (with real module functionality) as you develop it.
This method is sub-par for dependency management (see above notice), but - as a developer - you should be able to manually ensure that your package manager provides the needed packages.

````
git clone git@github.com:IBT-FMI/SAMRI.git
cd SAMRI
mkdir ~/.python_develop
echo "export PYTHONPATH=\$HOME/.python_develop:\$PYTHONPATH" >> ~/.bashrc
echo "export PATH=\$HOME/.python_develop:\$PATH" >> ~/.bashrc
source ~/.bashrc
python setup.py develop --install-dir ~/.python_develop/
````

If you are getting a `Permission denied (publickey)` error upon trying to clone, you can either:

* [Add an SSH key](https://help.github.com/articles/adding-a-new-ssh-key-to-your-github-account/) to your GitHub account.
* Pull via the HTTPS link `git clone https://github.com/IBT-FMI/SAMRI.git`.

## Key Concepts

Many SAMRI functions which take multiple paths as inputs, rely on what we call *BIDS-Iterator Inputs*.
These are pairs of one filename template string and a list of dictionaries (which are internally used by functions adhering to this input standard in order to format the aforementioned strings).
BIDS-Iterator Inputs can be produced via the `samri.utilities.bids_substitution_iterator()` function.

## Dependencies

The most precise description of the dependency graph (including conditionality) can be extracted from the [SAMRI ebuild](.gentoo/sci-biology/samri/samri-99999.ebuild).
For manual dependency management and overview you may use the following list:

* [argh](https://github.com/neithere/argh)
* [joblib](https://github.com/joblib/joblib)
* [matplotlib](https://matplotlib.org/) (>=`2.0.2`)
* [NumPy](https://www.numpy.org) (>=`1.13.3`)
* [pandas](https://pandas.pydata.org/)
* [seaborn](https://seaborn.pydata.org/)
* [statsmodels](https://github.com/statsmodels/statsmodels/)
* [FSL](http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/) (>=`5.0.9`)
* [Bru2Nii](https://github.com/neurolabusc/Bru2Nii)
* [nibabel](https://github.com/nipy/nibabel)
* [nipy](https://github.com/nipy/nipy) (>=`0.4.1`)
* [nipype](https://github.com/nipy/nipype) (>=`1.0.0`)
* [SciPy](https://www.scipy.org)
* [PyBIDS](https://github.com/INCF/pybids)
* [ANTs](https://github.com/ANTsX/ANTs/)
* [AFNI](https://afni.nimh.nih.gov/)
* [nilearn](https://nilearn.github.io/)

Needed if no other data is available for testing and development:
* Mouse Brain Atlases: [download link](http://chymera.eu/distfiles/mouse-brain-atlases-0.1.20180717.tar.xz)
* SAMRI example binary data: [download link](http://chymera.eu/distfiles/samri_bindata-0.1.2.tar.xz)

Needed only in conjunction with LabbookDB metadata management:
* [SQLAlchemy](http://www.sqlalchemy.org/library.html)
* [LabbookDB](https://github.com/TheChymera/LabbookDB)

