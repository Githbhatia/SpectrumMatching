from turtle import st
from typing import Tuple, List, Optional, Dict, Any
import numpy as np
import matplotlib.pyplot as plt
import logging
import io
import streamlit as st
log = logging.getLogger(__name__)

@st.cache_data
def my_load_PEERNGA_record(f) -> Tuple[np.ndarray, float, int, str]:
    
    print(f)
    try:
        with f as fp:
            next(fp) # Skip header line 1
            line2 = next(fp).strip().split(',')
            if len(line2) < 4:
                raise ValueError("Line 2 format incorrect. Expected Name, Date, Station, Component.")
            date_parts = line2[1].strip().split('/')
            if len(date_parts) < 3:
                raise ValueError("Date format incorrect on Line 2. Expected MM/DD/YYYY.")
            year = date_parts[2]
            eqname = (f"{year}_{line2[0].strip()}_{line2[2].strip()}_comp_{line2[3].strip()}")

            next(fp) # Skip header line 3
            line4 = next(fp).strip().split(',')
            if len(line4) < 2 or 'NPTS=' not in line4[0] or 'DT=' not in line4[1]:
                 raise ValueError("Line 4 format incorrect. Expected NPTS=..., DT=...")
            try:
                npts_str = line4[0].split('=')[1].strip()
                npts = int(npts_str)
                dt_str = line4[1].split('=')[1].split()[0] # Handle potential extra text
                dt = float(dt_str)
            except (IndexError, ValueError) as e:
                raise ValueError(f"Could not parse NPTS or DT from Line 4: {e}")

            # Read acceleration data efficiently
            acc_flat = [float(p) for line in fp for p in line.split()]
            acc = np.array(acc_flat)

            if len(acc) != npts:
                log.warning(f"Warning: Number of data points read ({len(acc)}) "
                            f"does not match NPTS specified in header ({npts}). Using read data.")
                npts = len(acc) # Update npts to actual data length
    except FileNotFoundError:
        log.error(f"File not found: {f.name}")
        raise
    except Exception as e:
        log.error(f"Error parsing file {f.name}: {e}")
        raise ValueError(f"Error parsing file {f.name}: {e}")

    return acc, dt, npts, eqname

@st.cache_data
def my_save_results_as_at2(
    results: Dict[str, Any],
    comp_key: str = 'ccs',
    header_details: Optional[Dict[str, str]] = None
) -> io.StringIO:
    """Saves a matched acceleration time series in PEER .AT2 format.

    Parameters
    ----------
    results : Dict[str, Any]
        The results dictionary from a REQPY function (e.g., REQPY_single).
        Must contain 'ccs' (or other comp_key) and 'dt'.
    comp_key : str, optional
        The key in the results dictionary for the acceleration array
        (e.g., 'ccs' for REQPY_single, 'scc1' for REQPYrotdnn).
        Default is 'ccs'.
    header_details : Optional[Dict[str, str]], optional
        A dictionary providing details for the .AT2 header.
        Keys: 'title', 'date', 'station', 'component'.
        If None, generic defaults are used.
    """
    accel = results.get(comp_key)
    dt = results.get('dt')

    if accel is None or dt is None:
        log.error(f"Cannot save .AT2 file: '{comp_key}' or 'dt' not found in results dictionary.")
        return

    npts = len(accel)
    
    # Fill header details with defaults if not provided
    if header_details is None:
        header_details = {}
    
    title = header_details.get('title', 'REQPY SPECTRALLY MATCHED RECORD')
    date = header_details.get('date', '01/01/2025')
    station = header_details.get('station', 'REQPY_STATION')
    component = header_details.get('component', f'Matched {comp_key}')

    header_line1 = f"{title}\n"
    header_line2 = f"EARTHQUAKE, {date}, {station}, {component}\n"
    header_line3 = "ACCELERATION IN G\n"
    header_line4 = f"NPTS= {npts}, DT= {dt:.8f} SEC\n"

    filetxt = ""
    filetxt += header_line1
    filetxt += header_line2
    filetxt += header_line3
    filetxt += header_line4

    for i in range(npts):
        filetxt += f" {accel[i]: 15.7e}"
        if (i + 1) % 8 == 0 and i != (npts - 1): # Add newline every 8 points
            filetxt += "\n"
    filetxt += "\n" # Final newline
    log.info(f"Successfully saved to text string for .AT2 format.")
    output = io.StringIO(filetxt)
    return output   
   
@st.cache_data
def my_save_results_as_2col(
    results: Dict[str, Any],
    comp_key: str = 'ccs',
    header_str: Optional[str] = None
) -> io.StringIO:   
    """Saves a matched time series as a 2-column (Time, Value) text file.

    Parameters
    ----------
    results : Dict[str, Any]
        The results dictionary from a REQPY function.
        Must contain 'dt' and the specified `comp_key`.
    comp_key : str, optional
        The key in the results dictionary for the data array
        (e.g., 'ccs', 'cvel', 'cdisp'). Default is 'ccs'.
    header_str : Optional[str], optional
        A string to write as the header. If None, a default
        header is generated.
    """
    data = results.get(comp_key)
    dt = results.get('dt')

    if data is None or dt is None:
        log.error(f"Cannot save 2-col file: '{comp_key}' or 'dt' not found in results.")
        return

    npts = len(data)
    t = np.linspace(0, (npts - 1) * dt, npts)
    
    # Stack time and data as columns
    data_to_save = np.stack((t, data), axis=1)

    # Create default header if none provided
    if header_str is None:
        header_str = (f"REQPY Matched Time Series\n"
                      f"Data key: '{comp_key}'\n"
                      f"Time Step (dt): {dt:.8f} s\n"
                      f"Time (s), Value (units vary)")
    

    try:
        output = io.StringIO()
        np.savetxt(output, data_to_save, header=header_str, fmt='%.8e', delimiter=',')
        log.info(f"Successfully saved 2-column file")
    except Exception as e:
        log.error(f"Error saving 2-column file: {e}")
    return output 

@st.cache_data
def my_save_results_as_1col(
    results: Dict[str, Any],
    comp_key: str = 'ccs',
    header_str: Optional[str] = None
) -> io.StringIO:
    """Saves a matched time series as a single-column (Value) text file.

    Parameters
    ----------
    results : Dict[str, Any]
        The results dictionary from a REQPY function.
        Must contain 'dt' and the specified `comp_key`.
    comp_key : str, optional
        The key in the results dictionary for the data array
        (e.g., 'ccs', 'cvel', 'cdisp'). Default is 'ccs'.
    header_str : Optional[str], optional
        A string to write as the header. If None, a default
        header is generated.
    """
    data = results.get(comp_key)
    dt = results.get('dt')

    if data is None or dt is None:
        log.error(f"Cannot save 1-col file: '{comp_key}' or 'dt' not found in results.")
        return None

    # Create default header if none provided
    if header_str is None:
        header_str = (f"REQPY Matched Time Series\n"
                      f"Data key: '{comp_key}'\n"
                      f"Time Step (dt): {dt:.8f} s\n"
                      f"Data points follow:")

    try:
        output = io.StringIO()
        np.savetxt(output, data, header=header_str, fmt='%.8e')
        log.info(f"Successfully saved 1-column file")
    except Exception as e:
        log.error(f"Error saving 1-column file: {e}")
    return output 

@st.fragment
def callATSave(outputfile_1,outputfile_2, at2_filepath1,at2_filepath2): 
    sc1,sc2=st.columns(2)
    with sc1:
        st.download_button("Save Spectrally Matched Record 1 as .AT2", outputfile_1.getvalue(), file_name=at2_filepath1, mime="text/csv",)
    with sc2:
        st.download_button("Save Spectrally Matched Record 2 as .AT2", outputfile_2.getvalue(), file_name=at2_filepath2, mime="text/csv",)

@st.fragment
def call1colSave(outputfile_1col_1,outputfile_1col_2, txt_1col_filepath1,txt_1col_filepath2):
    scc1,scc2=st.columns(2)
    with scc1:
        st.download_button("Save Spectrally Matched Record 1 as 1-Column TXT", outputfile_1col_1.getvalue(), file_name=txt_1col_filepath1, mime="text/csv",)        
    with scc2:
        st.download_button("Save Spectrally Matched Record 2 as 1-Column TXT", outputfile_1col_2.getvalue(), file_name=txt_1col_filepath2, mime="text/csv",)