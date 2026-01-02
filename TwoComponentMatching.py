"""
Example 3: Direct RotDnn Component Matching (Concise)

Modifies two horizontal components from a historic record simultaneously so that
the resulting RotD100 response spectrum (computed from the pair)
matches the specified RotD100 design/target spectrum.

This is the recommended approach for matching two components.

"""

# Import necessary functions 
from typing import Tuple, List, Optional, Dict, Any
import streamlit as st
from reqpy_M import (REQPYrotdnn,  plot_rotdnn_results)
import numpy as np
import matplotlib.pyplot as plt
import logging
import io
import helperfunctions as hf

log = logging.getLogger(__name__)



plt.close('all')

st.header("Two Component Spectrum Matching", divider="gray")
st.write("Modifies two horizontal components from a historic record simultaneously so that the resulting RotD100 response spectrum (computed from the pair) matches the specified RotD100 design/target spectrum.")
st.write ("Uses REQPYrotdnn function from reqpy_M module.")
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
filenames1=None


c1,c2 =st.columns(2)
with c1:
    filenames1=st.file_uploader("Upload PEER file for component 1",type=[ "AT2"])
    if filenames1 is None:
        st.warning("Please upload a PEER file for component 1 to proceed.")
        st.stop()
    else:
            seed_file1=io.StringIO(filenames1.read().decode("utf-8"))
with c2:
    filenames2=st.file_uploader("Upload PEER file for component 2",type=[ "AT2"])
    if filenames2 is None:
        st.warning("Please upload a PEER file for component 2 to proceed.")
        st.stop()
    else:
            seed_file2=io.StringIO(filenames2.read().decode("utf-8"))


cc1,cc2=st.columns(2)
with cc1:
     dampratio=st.number_input("Damping ratio for spectra",value=0.05)
     TL1=st.number_input("Lower period limit for matching (s)",value=0.05)
     TL2=st.number_input("Upper period limit for matching (s)",value=6.0)
with cc2:
     nit_match=st.number_input("Number of matching iterations",value=15)
     nn = st.number_input("Percentile for RotD (e.g., 100 for RotD100)",value=100)
     baseline_correct=st.checkbox("Perform baseline correction?",value=True)
     p_order=st.number_input("Detrending order for baseline (-1 = none)",value=-1)

# seed_file_1 = 'RSN175_IMPVALL.H_H-E12140.AT2' # Seed record comp1 [g]
# seed_file_2 = 'RSN175_IMPVALL.H_H-E12230.AT2' # Seed record comp2 [g]
# target_file = 'ASCE7.txt'                    # Target spectrum (T, PSA)
# dampratio = 0.05                             # Damping ratio for spectra
# TL1 = 0.05                                   # Lower period limit for matching (s)
# TL2 = 6.0                                    # Upper period limit for matching (s)
# nit_match = 15
# nn = 100                                     # Percentile for RotD (100 = RotD100)
#baseline_correct = True
# p_order = -1
output_base_name = filenames1.name[:-10]+'_'+target.name[:-4]+'_RotD'+str(nn) # Base name for output files
saveR =False
placeholder = st.empty()
placeholder.write("Work in progress...")
# --- Load target spectrum and seed record ---

s1, dt, n1, name1 = hf.my_load_PEERNGA_record(seed_file1)
s2, _, n2, name2 = hf.my_load_PEERNGA_record(seed_file2)

fs = 1 / dt

target_spectrum = np.loadtxt(target_file)
sort_idx = np.argsort(target_spectrum[:, 0])
To = target_spectrum[sort_idx, 0]  # Target spectrum periods
dso = target_spectrum[sort_idx, 1] # Target spectrum PSA
    

# --- Perform Direct RotDnn Spectral Matching ---
# Call the  REQPYrotdnn function
results = REQPYrotdnn(
    s1=s1,
    s2=s2,
    fs=fs,
    dso=dso,
    To=To,
    nn=nn,
    T1=TL1,
    T2=TL2,
    zi=dampratio,
    nit=nit_match,
    baseline=baseline_correct,
    porder=p_order)

st.write("Spectral matching complete.")
st.write(f"Final RMSE (pre-BC): {results.get('rmsefin', 'N/A'):.2f}%")
st.write(f"Final Misfit (pre-BC): {results.get('meanefin', 'N/A'):.2f}%")


# --- Plot Results ---
# Call the plotting function for RotDnn results
fig_hist, fig_spec = plot_rotdnn_results(
    results=results,
    s1_orig=s1, # Pass original unscaled record 1
    s2_orig=s2, # Pass original unscaled record 2
    target_spec=(To, dso),
    T1=TL1,
    T2=TL2,
    xlim_min=None,
    xlim_max=None)

# Save and show plots
# hist_filename = f"{output_base_name}_TimeHistories.png"
# spec_filename = f"{output_base_name}_Spectra.png"
# fig_hist.savefig(hist_filename, dpi=300)
# fig_spec.savefig(spec_filename, dpi=300)
# print(f"Saved plots to {hist_filename} and {spec_filename}")
st.pyplot(fig_spec) # Display plots
st.pyplot(fig_hist) # Display plots

# --- Save Matched Records ---
placeholder.write("Completed")
saveR = True
if saveR:
    # --- Save Matched Record ---
    saveoption = st.selectbox(
        "Select output format for matched record:",
        ("Save as .AT2 format",
        "Save as 1-column (Accel) .txt file")
    )   

    if saveoption == "Save as .AT2 format":
        # --- Save Component 1 ---
        at2_filepath1 = f"{output_base_name}_Comp1_Matched.AT2"
        at2_header1 = {
            'title': f'Matched record from {filenames1.name} (Target: {target.name})',
            'station': name1.split('_comp_')[0] if '_comp_' in name1 else name1,
            'component': f"{name1.split('_comp_')[-1]}-Matched"
        }
        outputfile_1 = hf.my_save_results_as_at2(results, comp_key='scc1', header_details=at2_header1)
        

        # --- Save Component 2 ---
        at2_filepath2 = f"{output_base_name}_Comp2_Matched.AT2"
        at2_header2 = {
            'title': f'Matched record from {filenames2.name} (Target: {target.name})',
            'station': name2.split('_comp_')[0] if '_comp_' in name2 else name2,
            'component': f"{name2.split('_comp_')[-1]}-Matched"
        }
        outputfile_2 = hf.my_save_results_as_at2(results, comp_key='scc2', header_details=at2_header2)

        hf.callATSave(outputfile_1,outputfile_2, at2_filepath1,at2_filepath2)
        

    elif saveoption == "Save as 1-column (Accel) .txt file":
        # --- Save Component 1 ---  
        txt_1col_filepath1 = f"{output_base_name}_Comp1_Matched_1col.txt"
        header_1col_1 = (f"Matched acceleration (g), dt={results.get('dt', 0.0):.8f}s\n"
                        f"Original Seed: {name1}\n"
                        f"Target Spectrum: {target.name}\n"
                        f"Data points follow:")
        outputfile_1col_1 = hf.my_save_results_as_1col(results, comp_key='scc1', header_str=header_1col_1)
        
        # --- Save Component 2 ---
        txt_1col_filepath2 = f"{output_base_name}_Comp2_Matched_1col.txt"
        header_1col_2 = (f"Matched acceleration (g), dt={results.get('dt', 0.0):.8f}s\n"
                        f"Original Seed: {name2}\n"
                        f"Target Spectrum: {target.name}\n"
                        f"Data points follow:")
        outputfile_1col_2 = hf.my_save_results_as_1col(results, comp_key='scc2', header_str=header_1col_2)

        hf.call1colSave(outputfile_1col_1,outputfile_1col_2, txt_1col_filepath1,txt_1col_filepath2)
        
        


print("\nScript finished.")

