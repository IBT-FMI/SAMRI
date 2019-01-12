# Copyright 1999-2017 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

EAPI=6

PYTHON_COMPAT=( python{2_7,3_4,3_5,3_6} )

inherit distutils-r1

DESCRIPTION="Small Animal Magnetic Resonance Imaging"
HOMEPAGE="https://github.com/IBT-FMI/SAMRI"

LICENSE="GPL-3"
SLOT="0"
IUSE="+atlases labbookdb test"
KEYWORDS=""

DEPEND="
	test? (
		dev-python/pytest[${PYTHON_USEDEP}]
		sci-biology/samri_bidsdata
		sci-biology/samri_bindata
		)
	"
RDEPEND="
	dev-python/argh[${PYTHON_USEDEP}]
	dev-python/joblib[${PYTHON_USEDEP}]
	>=dev-python/matplotlib-2.0.2[${PYTHON_USEDEP}]
	>=dev-python/numpy-1.13.3[${PYTHON_USEDEP}]
	dev-python/pandas[${PYTHON_USEDEP}]
	dev-python/seaborn[${PYTHON_USEDEP}]
	dev-python/sqlalchemy[${PYTHON_USEDEP}]
	dev-python/statsmodels[${PYTHON_USEDEP}]
	sci-biology/afni
	sci-biology/ants
	sci-biology/bru2nii
	>=sci-biology/fsl-5.0.9
	atlases? ( sci-biology/mouse-brain-atlases )
	sci-biology/nilearn[${PYTHON_USEDEP}]
	labbookdb? ( sci-libs/labbookdb[${PYTHON_USEDEP}] )
	sci-libs/nibabel[${PYTHON_USEDEP}]
	>=sci-libs/nipy-0.4.1[${PYTHON_USEDEP}]
	>=sci-libs/nipype-1.0.0[${PYTHON_USEDEP}]
	sci-libs/pybids[${PYTHON_USEDEP}]
	sci-libs/scipy[${PYTHON_USEDEP}]
	"

src_unpack() {
	cp -r -L "$DOTGENTOO_PACKAGE_ROOT" "$S"
}

python_prepare_all() {
	find . -type f -exec \
		sed -i "s:/usr/share/mouse-brain-atlases/:${EPREFIX}/usr/share/mouse-brain-atlases/:g" {} +
	distutils-r1_python_prepare_all
}

python_test() {
	distutils_install_for_testing
	export MPLBACKEND="agg"
	export PATH=${TEST_DIR}/scripts:$PATH
	export PYTHONIOENCODING=utf-8
	./test_scripts.sh || die "Test scripts failed."
	sed -i -e \
		"/def test_bru2bids():/i@pytest.mark.skip('Removed in full test suite, as this is already tested in `test_scripts.sh`')" \
		samri/pipelines/tests/test_repos.py || die
	pytest -vv || die
}
