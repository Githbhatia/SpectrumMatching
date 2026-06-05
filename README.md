# Streamlit Spectrum Matching Application 

Has two pages - one for single component matching and one for two component matching.
Drag and drop target spectrum and earthquake records in PEER AT format.  Output in peer or single column text files.
Sample input files are included here (same as provided in REQPY_M repository, see https://github.com/LuisMontejo/REQPY).
Any questions an matching algorithm, contact Luis A. Montejo (luis.montejo@upr.edu)

Uses:
REQPY version 0.4.0: Spectral Matching of Earthquake Records

A Python module for spectral matching of earthquake records using the Continuous Wavelet Transform (CWT) based methodologies described in the referenced papers.

Its primary capabilities include:

* Matching a single ground motion component to a target spectrum.
* Matching a pair of horizontal components to an orientation-independent target spectrum RotDnn (e.g., RotD100).
* Analysis functions for generating standard and rotated (RotDnn) spectra.
* Baseline correction routines for processed time histories.


6/5/2026:  Updated to use reqpy_M version 0.4.0 which is not backward compatible to vervious versions.  Also had to duplicate some functions in helperfunctions.py due to some missing modules in the package.



You can use the Streamlit app at the following location:
https://3n9ky89qr77jdaacdpdqzq.streamlit.app/

