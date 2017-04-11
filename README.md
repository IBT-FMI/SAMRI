# SAMRI

SAMRI (Small Animal Magnetic Resonance Imaging) - pronounced "Sam-rye" - provides fMRI preprocessing, metadata parsing, and data analysis functions and pipelines.
SAMRI integrates functionalities from a number of other packages (listed under the dependencies section below) to create higher-level tools.
The resulting interfaces aim to maximize reproducibility, simplify batch processing, and minimize the number of function calls required to generate figures and statistical summaries from the raw data.

The package is compatible with small rodent data acquired via Bruker systems.

## Dependencies:

* [argh](https://github.com/neithere/argh) - in Portage as dev-python/argh
* [Bru2Nii](https://github.com/neurolabusc/Bru2Nii) - in Portage as sci-biology/bru2nii
* [FSL](http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/) - in Portage as sci-biology/fsl
* [nipy](https://github.com/nipy/nipy) - in Portage as sci-libs/nipy
* [nipype](https://github.com/nipy/nipype) - in Portage as sci-libs/nipype
* [scipy](https://www.scipy.org) - thealt LinuxDays test
