"""
Example 1: Single Component Spectral Matching (Concise)

Matches a single component to a target spectrum using the refactored module.
Removes logging and defensive error handling around core functions for brevity.
"""

# Import necessary functions f
from typing import Tuple, List, Optional, Dict, Any
import streamlit as st

import reqpy_M

import numpy as np
import matplotlib.pyplot as plt
import logging
import io
import helperfunctions as hf

log = logging.getLogger(__name__)

st.header("Single Component Spectrum Matching", divider="gray")
st.write("Modifies a single component from a historic record so that the resulting response spectrum matches the specified design/target spectrum.")
st.write ("Uses generate_single_component_compatible_record function from reqpy_M module.")
plt.close('all')
# --- Configuration ---
# Setup basic logging to see output from the module
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


st.write("Target file should have two columns: Period (s) and PSA (g).")    
target=st.file_uploader("Upload target spectrum file",type=[ "txt"])
if target is None:
    st.warning("Please upload a target file to proceed.")
    st.stop()
else:
        target_file=io.StringIO(target.read().decode("utf-8"))
filenames=None
filenames=st.file_uploader("Upload PEER file",type=[ "AT2"])
if filenames is None:
    st.warning("Please upload a PEER file to proceed.")
    st.stop()
else:
        seed_file=io.StringIO(filenames.read().decode("utf-8"))


baseline_methods = ['none', 'classic', 'piecewise', 'sixth_order']
cc1,cc2=st.columns(2)
with cc1:
     dampratio=st.number_input("Damping ratio for spectra",value=0.05)
     TL1=st.number_input("Lower period limit for matching (s)",value=0.05)
     TL2=st.number_input("Upper period limit for matching (s)",value=6.0)
with cc2:
     nit_match=st.number_input("Number of matching iterations",value=15)
     baseline_correct=st.selectbox("Select baseline correction method", options=baseline_methods, index=3)
     p_order=st.number_input("Polynomial order for 'classic' baseline correction",value=4)



# seed_file = 'RSN175_IMPVALL.H_H-E12140.AT2'    # Seed record [g]
# target_file = 'ASCE7.txt'                     # Target spectrum (T, PSA)
# dampratio = 0.05                             # Damping ratio for spectra
# TL1 = 0.05                                    # Lower period limit for matching (s)
# TL2 = 6.0                                     # Upper period limit for matching (s)
# nit_match = 15                                # Number of matching iterations
# baseline_correct = True                       # Perform baseline correction?
# p_order = -1                                  # Detrending order for baseline (-1 = none)
output_base_name = filenames.name[:-4]+'_'+target.name[:-4] # Base name for output files
saveR =False
placeholder = st.empty()
placeholder.write("Work in progress...")
# --- Load target spectrum and seed record ---

s_orig, dt, npts, eqname = hf.my_load_PEERNGA_record(seed_file)
fs = 1 / dt

target_spectrum = np.loadtxt(target_file)
if target_spectrum.ndim != 2 or target_spectrum.shape[1] != 2:
    raise ValueError("Target file should have two columns (Period, PSA).")
    
sort_idx = np.argsort(target_spectrum[:, 0])
To = target_spectrum[sort_idx, 0]  # Target spectrum periods
dso = target_spectrum[sort_idx, 1] # Target spectrum PSA
targetPSAlimits = (0.9, 1.1) # Matching limits for target spectrum (e.g., 90% to 110%)

# --- Perform Spectral Matching ---
results = reqpy_M.generate_single_component_compatible_record(
    s=s_orig,
    fs=fs,
    T_PSA=To,
    targetPSA=dso,
    targetPSAlimits=targetPSAlimits,
    T1PSA=TL1,
    T2PSA=TL2,
    zi=dampratio,
    nit=nit_match,
    baseline_method=baseline_correct,
    PSA_poly_order=p_order)

st.write("Spectral matching complete.")
st.write(f"Final RMSE (pre-BC): {results['rmsefin']:.2f}%")
st.write(f"Final Misfit (pre-BC): {results['meanefin']:.2f}%")


# --- Extract Results ---
sc = results['sc']          
sf = results['scale_factor']
s_scaled = s_orig[:len(sc)] * sf  

# --- Plot Results ---

fig_spec, fig_hist,x  = reqpy_M.plot_single_component_results(
    results=results,
    targetPSAlimits=targetPSAlimits,
    T1PSA=TL1,
    T2PSA=TL2,
    zi=dampratio,
    units='g')

fig_spec.constrained_layout = True
fig_hist.constrained_layout = True


st.pyplot(fig_spec) # Display plots
st.pyplot(fig_hist) # Display plots
# print(x) # Display plots



saveR = True
placeholder.write("Completed")
if saveR:
    # --- Save Matched Record ---
    saveoption = st.selectbox(
        "Select output format for matched record:",
        ("Save as .AT2 format",
        "Save as 2-column (Time, Accel) .txt file",
        "Save as 1-column (Accel) .txt file")
    )   

    if saveoption == "Save as .AT2 format":
    # --- Option 1: Save as .AT2 format ---
        at2_filepath = f"{output_base_name}_Matched.AT2"
        at2_header_details = {
            'title': f'Matched record from {filenames.name} (Target: {target.name})',
            'date': '01/01/2025', # Placeholder date
            'station': eqname.split('_comp_')[0] if '_comp_' in eqname else eqname,
            'component': f"{eqname.split('_comp_')[-1]}-Matched"
        }
        outputfile = hf.my_save_results_as_at2(results, comp_key='sc', header_details=at2_header_details)
        st.download_button("Save Spectrally Matched Record as .AT2", outputfile.getvalue(), file_name=at2_filepath, mime="text/csv",)

    elif saveoption == "Save as 2-column (Time, Accel) .txt file":
        # --- Option 2: Save as 2-column (Time, Accel) .txt file ---
        txt_2col_filepath = f"{output_base_name}_Matched_2col.txt"
        header_2col = (f"Matched acceleration (g) vs. Time (s)\n"
                    f"Original Seed: {eqname}\n"
                    f"Target Spectrum: {target.name}\n"
                    f"Time (s), Acceleration (g)")
        outputfile = hf.my_save_results_as_2col(results, comp_key='sc', header_str=header_2col)
        st.download_button("Save Spectrally Matched Record as 2-Column TXT", outputfile.getvalue(), file_name=txt_2col_filepath, mime="text/plain")

    else:
        # --- Option 3: Save as 1-column (Accel) .txt file ---
        txt_1col_filepath = f"{output_base_name}_Matched_1col.txt"
        header_1col = (f"Matched acceleration (g), dt={results.get('dt', 0.0):.8f}s\n"
                    f"Original Seed: {eqname}\n"
                    f"Target Spectrum: {target.name}\n"
                    f"Data points follow:")
        outputfile = hf.my_save_results_as_1col(results, comp_key='sc', header_str=header_1col)
        st.download_button("Save Spectrally Matched Record as 1-Column TXT", outputfile.getvalue(), file_name=txt_1col_filepath, mime="text/plain")
        

    print("\nScript finished.")

