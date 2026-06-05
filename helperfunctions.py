from typing import Tuple, List, Optional, Dict, Any, Union
import numpy as np
import matplotlib.pyplot as plt
import logging
import io
import streamlit as st
log = logging.getLogger(__name__)
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec
import matplotlib as mpl
from scipy.spatial import ConvexHull

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



def my_plot_rotdnn_results(
    results: Dict[str, Any],
    targetPSAlimits: Tuple[float, float] = (0.9, 1.3),
    T1PSA: float = 0.02,
    T2PSA: float = 5.0,
    zi: float = 0.05,
    units: str = 'g',
    plot_directionality: bool = False,
    polar_freqs: List[float] = [0.5, 1, 2, 4, 8, 12, 16, 20]) -> Union[Tuple['plt.Figure', 'plt.Figure', Dict], Tuple['plt.Figure', 'plt.Figure', 'plt.Figure', 'plt.Figure', Dict]]:
    
    """
    Generates verification plots and metrics for biaxial RotDnn spectral matching results.

    Methodology:
    - Spectral Comparison (Figure 1): Generates a semi-log plot comparing the orientation-independent 
      Target Pseudo-Spectral Acceleration (RotDnn PSA) against the initial Scaled RotDnn PSA and the 
      final Matched RotDnn PSA. Sub-panels plot the ratio of the Matched PSA to the Target PSA, 
      highlighting the matching domain (defined by `T1PSA` and `T2PSA`) and verifying compliance 
      with the defined tolerance boundaries (`targetPSAlimits`).
    - Time-Domain Comparison (Figure 2): Creates a 3x2 grid of subplots displaying the acceleration, 
      velocity, and displacement time histories for both horizontal components (Component 1 on the left, 
      Component 2 on the right). It overlays the original scaled and final matched records. On secondary 
      y-axes, it plots the normalized energy buildup for each kinematic domain to ensure the temporal 
      envelope of the seed record is preserved.
    - Deviation Tracking: Computes the maximum absolute difference between the normalized energy buildups 
      of the matched and original records for both components independently, quantifying temporal alteration.
    - Directionality (Optional - Figures 3 & 4): If `plot_directionality` is activated, the function 
      solves the biaxial SDOF response at various resonant frequencies. It plots polar representations 
      of the response trajectories (Figure 3) at specific sample frequencies (`polar_freqs`), and constructs 
      the period-dependent RotD100/RotD50 ratios alongside the Directionality Spectrum of Acceleration (DSA) 
      using the `dfactor` routine (Figure 4) to verify that isotropic/polarized characteristics are maintained.

    Parameters
    ----------
    results : Dict[str, Any]
        The comprehensive output dictionary generated by the RotDnn matching function 
        (e.g., `generate_rotdnn_psa_compatible_record`), containing frequency/period arrays, 
        PSA spectra, time vectors, and kinematic histories for both components.
    targetPSAlimits : Tuple[float, float], optional
        The lower and upper tolerance bounds for the PSA matching ratio. Used to plot 
        the limit lines in the ratio sub-panels. Default is (0.9, 1.3).
    T1PSA : float, optional
        The start of the period range (s) over which the matching was performed. Used 
        to shade the target matching region on the plots. Default is 0.02.
    T2PSA : float, optional
        The end of the period range (s) over which the matching was performed. Used 
        to shade the target matching region on the plots. Default is 5.0.
    zi : float, optional
        The damping ratio (as a decimal) associated with the target response spectrum. 
        Used for plot labeling (e.g., 0.05 for 5% damping). Default is 0.05.
    units : str, optional
        The string representation of the acceleration units (e.g., 'g', 'm/s²'). 
        Used for plot labeling. Default is 'g'.
    plot_directionality : bool, optional
        If True, executes the necessary SDOF simulations to compute and plot the biaxial 
        polar response trajectories and the Directionality Spectrum of Acceleration (DSA). 
        Default is False.
    polar_freqs : List[float], optional
        A list of specific frequencies (Hz) at which to plot the polar response trajectories 
        in Figure 3 (only used if `plot_directionality` is True). 
        Default is [0.5, 1, 2, 4, 8, 12, 16, 20].

    Returns
    -------
    Union[Tuple[plt.Figure, plt.Figure, Dict[str, list]], Tuple[plt.Figure, plt.Figure, plt.Figure, plt.Figure, Dict[str, list]]]
        If `plot_directionality` is False:
        - fig1 (plt.Figure): The spectral comparison and ratio plots.
        - fig2 (plt.Figure): The kinematic time histories and energy buildup plots.
        - max_deltas_dict (Dict[str, list]): The maximum absolute deviations in normalized energy 
          buildup. Keys are `'Acc1'`, `'Acc2'`, `'Vel1'`, `'Vel2'`, `'Disp1'`, and `'Disp2'`.

        If `plot_directionality` is True, returns all of the above, plus:
        - fig3 (plt.Figure): The polar plots of biaxial response trajectories.
        - fig4 (plt.Figure): The RotD100/RotD50 ratios and the Directionality Spectrum of Acceleration.
    """
    
  
    
    mpl.rcParams['font.size'] = 9 
    mpl.rcParams['legend.frameon'] = False
    mpl.rcParams['mathtext.fontset'] = 'dejavuserif'
    mpl.rcParams['font.family'] = 'serif'
    
    LINEWIDTH_MAIN = 1.0
    C_TARGET = 'k'; C_SCALED = 'dimgray'; C_PSA = 'cornflowerblue'
    COLOR_SHADE = 'steelblue'; ALPHA_SHADE = 0.1

    periods = results['periods']; t = results['t']; nn = results.get('nn', 50)
    sf = results.get('scale_factor', 1.0) 
    
    idx_p = np.argsort(periods)
    p_plot = periods[idx_p]

    # =========================================================================
    # FIGURE 1: SPECTRA (1x3 Subplot Grid)
    # =========================================================================
    fig1 = plt.figure(figsize=(10.0, 4.5))
    gs = GridSpec(2, 3, figure=fig1, height_ratios=[7, 3], hspace=0.12, wspace=0.15)

    target = results['target_psa'][idx_p]
    
    p_s1 = results.get('psa_s1'); p_sc1 = results.get('psa_sc1')
    p_s2 = results.get('psa_s2'); p_sc2 = results.get('psa_sc2')
    p_data_s = results.get("psa_s"); p_data_sc = results.get("psa_sc")

    # Define the data sets for each of the 3 columns
    columns_data = [
        ('Component 1', p_s1, p_sc1),
        ('Component 2', p_s2, p_sc2),
        (f'RotD{nn}', p_data_s, p_data_sc)
    ]

    for i, (title, d_s, d_sc) in enumerate(columns_data):
        ax_top = fig1.add_subplot(gs[0, i])
        ax_bot = fig1.add_subplot(gs[1, i])

        # Shaded regions in all 3 subplots
        ax_top.axvspan(T1PSA, T2PSA, color=COLOR_SHADE, alpha=ALPHA_SHADE, zorder=0)
        ax_bot.axvspan(T1PSA, T2PSA, color=COLOR_SHADE, alpha=ALPHA_SHADE, zorder=0)

        # Target and Limits
        ax_top.semilogx(p_plot, target, color=C_TARGET, lw=LINEWIDTH_MAIN*2, zorder=5)
        if not np.isnan(targetPSAlimits[0]):
            ax_top.semilogx(p_plot, target * targetPSAlimits[0], color=C_TARGET, ls='--', lw=LINEWIDTH_MAIN, zorder=5)
            ax_bot.axhline(targetPSAlimits[0], color='k', ls='--', lw=LINEWIDTH_MAIN, zorder=5)
        if not np.isnan(targetPSAlimits[1]):
            ax_top.semilogx(p_plot, target * targetPSAlimits[1], color=C_TARGET, ls='--', lw=LINEWIDTH_MAIN, zorder=5)
            ax_bot.axhline(targetPSAlimits[1], color='k', ls='--', lw=LINEWIDTH_MAIN, zorder=5)

        # Scaled and Matched Traces
        if d_s is not None:
            data_s_sorted = d_s[idx_p]
            ax_top.semilogx(p_plot, data_s_sorted, color=C_SCALED, lw=LINEWIDTH_MAIN)
        if d_sc is not None:
            data_sc_sorted = d_sc[idx_p]
            ax_top.semilogx(p_plot, data_sc_sorted, color=C_PSA, lw=LINEWIDTH_MAIN)
            
        # Ratio plotting
        mask = (p_plot >= T1PSA) & (p_plot <= T2PSA)
        if d_s is not None:
            ax_bot.semilogx(p_plot, np.where(mask, data_s_sorted/target, np.nan), color=C_SCALED, lw=LINEWIDTH_MAIN)
        if d_sc is not None:
            ax_bot.semilogx(p_plot, np.where(mask, data_sc_sorted/target, np.nan), color=C_PSA, lw=LINEWIDTH_MAIN)
            
        # Formatting per column
        ax_top.set_title(title, fontsize=10, fontweight='bold')
        ax_top.set_xticklabels([])
        ax_bot.set_xlim(0.01, 10)
        ax_bot.set_xlabel('Period (s)')
        ax_bot.axhline(1.0, color='k', lw=LINEWIDTH_MAIN, zorder=5)
        
        mask_plot = (p_plot >= 0.01) & (p_plot <= 10)
        y_max = np.nanmax((target * targetPSAlimits[1])[mask_plot]) * 2.0
        y_min = np.nanmin((target * targetPSAlimits[0])[mask_plot]) * 0.7
        ax_top.set_ylim(bottom=y_min, top=y_max)
        
        if i == 0:
            ax_top.set_ylabel(f'PSA ({units})')
            ax_bot.set_ylabel('Ratio')
        else:
            ax_top.set_yticklabels([])
            ax_bot.set_yticklabels([])

    handles = [
        Line2D([0],[0], color=C_SCALED, lw=LINEWIDTH_MAIN, label='Scaled'),
        Line2D([0],[0], color=C_PSA, lw=LINEWIDTH_MAIN, label='Matched'),
        Line2D([0],[0], color=C_TARGET, lw=LINEWIDTH_MAIN*2, label='Target'),
        Line2D([0],[0], color=C_TARGET, lw=LINEWIDTH_MAIN, ls='--', label='Limits')
    ]
    
    fig1.legend(handles=handles, loc='upper center', ncol=4, bbox_to_anchor=(0.5, 1.02), frameon=False, columnspacing=1.5)
    fig1.constrained_layout = True
    fig1.subplots_adjust(top=0.88, bottom=0.12)

    # =========================================================================
    # FIGURE 2: TIME HISTORIES (Original Version)
    # =========================================================================
    if units == 'g': conv_vel = 980.665; conv_disp = 980.665; u_vel = 'cm/s'; u_disp = 'cm'
    else: conv_vel = 1.0; conv_disp = 1.0; u_vel = f'{units}-s'; u_disp = f'{units}-s^2'

    fig2, axs = plt.subplots(3, 2, figsize=(7.5, 6), sharex=True)
    trace_colors = [C_SCALED, C_PSA]
    max_deltas_dict = {}
    
    for comp in [1, 2]:
        th_list = [results[f's{comp}_scaled'], results[f'sc{comp}']]
        v_list = [results[f'vel{comp}_s'] * conv_vel, results[f'vel{comp}_sc'] * conv_vel]
        d_list = [results[f'disp{comp}_s'] * conv_disp, results[f'disp{comp}_sc'] * conv_disp]
        nai_list = [results[f'ai{comp}_s'], results[f'ai{comp}_sc']]
        ncsv_list = [results[f'csv{comp}_s'], results[f'csv{comp}_sc']]
        ncsd_list = [results[f'csd{comp}_s'], results[f'csd{comp}_sc']]

        groups = [
            (th_list, nai_list, 'Acc', units, 'Norm. CSA'),
            (v_list, ncsv_list, 'Vel', u_vel, 'Norm. CSV'),  
            (d_list, ncsd_list, 'Disp', u_disp, 'Norm. CSD') 
        ]

        y_pos = 0.05; x_anchor = 0.98; col = comp - 1

        for row, (th, norm, name, unit, norm_lbl) in enumerate(groups):
            axL = axs[row, col]; axR = axL.twinx()
            for d, c in zip(th, trace_colors): 
                if d is not None and not np.all(np.isnan(d)): axL.plot(t, d, color=c, lw=0.5, alpha=0.6)
            for n, c in zip(norm, trace_colors): 
                if n is not None and not np.all(n == 0.0): axR.plot(t, n, color=c, lw=1.0)
            
            deltas = [np.max(np.abs(n - norm[0])) for n in norm[1:]]
            max_deltas_dict[f"{name}{comp}"] = deltas
            
            if not np.all(norm[0] == 0.0):
                offset_val = 0.00; step = 0.12
                for i, delta in enumerate(reversed(deltas)):
                    c_idx = len(deltas) - i 
                    comma = ", " if i > 0 else ""
                    axL.text(x_anchor - offset_val, y_pos, f"{delta:.2f}{comma}", transform=axL.transAxes, fontsize=8, color=trace_colors[c_idx], va='bottom', ha='right', fontweight='bold')
                    offset_val += step
                axL.text(x_anchor - offset_val, y_pos, r'max $\Delta$:', transform=axL.transAxes, fontsize=8, color='black', va='bottom', ha='right')

            axL.set_ylabel(f'{name} [{unit}]' if col == 0 else '')
            axR.set_ylabel(norm_lbl if col == 1 else '', color='k', fontsize=9)
            axR.set_ylim(-0.05, 1.05)
            
            all_data = np.concatenate([d for d in th if d is not None and not np.all(np.isnan(d))])
            mx = np.nanmax(np.abs(all_data)); limit = 1.05 * mx if mx !=0 and np.isfinite(mx) else 1.0
            axL.set_ylim(-limit, limit); axL.grid(False); axR.grid(False)
            
            if col == 0: axR.set_yticks([])
            if col == 1: axL.set_yticks([])

    axs[2, 0].set_xlabel('Time [s]'); axs[2, 1].set_xlabel('Time [s]')
    
    fig2.legend(handles=handles[:2], loc='upper center', bbox_to_anchor=(0.5, 0.99), ncol=2, fontsize=9)
    fig2.tight_layout(rect=[0, 0, 1, 0.95])
    fig2.subplots_adjust(top=0.92) 

    if not plot_directionality: return fig1, fig2, max_deltas_dict

    # =========================================================================
    # FIGURE 3: POLAR SPECTRA (Original Version)
    # =========================================================================
    target_Ts = [1.0 / f for f in polar_freqs]
    indices = [np.argmin(np.abs(periods - pt)) for pt in target_Ts]
    actual_freqs = [1.0 / periods[i] for i in indices]
    
    psa_180_list = [results.get('psa_180_seed', np.zeros((1,len(periods)))) * sf, results.get('psa_180_sc', np.zeros((1,len(periods))))]
        
    n_plots = len(polar_freqs)
    ncols = 4
    nrows = int(np.ceil(n_plots / ncols))
    fig_height = 1.8 * nrows 
    
    fig3, axes = plt.subplots(nrows, ncols, subplot_kw={'projection': 'polar'}, figsize=(7.5, fig_height))
    axes_flat = axes.flatten() if n_plots > 1 else [axes]
    theta_rad = np.linspace(0, 2*np.pi, 360, endpoint=False)
    
    for i, ax in enumerate(axes_flat):
        if i < n_plots:
            pidx = indices[i]; f_val = actual_freqs[i]
            for mat, lbl, col in zip(psa_180_list, ['Scaled', 'PSA matched'], trace_colors):
                if mat is not None and mat.size > 1:
                    data = mat[:, pidx]; mx = np.max(data)
                    if mx > 0: data = data / mx
                    data_wrap = np.concatenate([data, data]); l_str = lbl if i == (n_plots - 1) else ""
                    ax.plot(theta_rad, data_wrap, color=col, linewidth=1.0, label=l_str)
            ax.set_title(f"f = {f_val:.1f} Hz", fontsize=8, pad=2); ax.set_xticks([]); ax.set_yticks([0.5, 1.0]); ax.set_yticklabels([]); ax.set_ylim(0, 1.1)
            ax.grid(True, linestyle=':', alpha=0.5); ax.set_theta_zero_location("E")
        else: ax.axis('off')
    
    fig3.legend(loc='lower center', ncol=len(trace_colors), bbox_to_anchor=(0.5, 0.0), fontsize=8, frameon=False, columnspacing=1.0)
    plt.tight_layout(rect=(0, 0.06, 1, 1.0))

    # =========================================================================
    # FIGURE 4: DIRECTIONALITY ANALYSIS (Original Version)
    # =========================================================================
    fig4, (ax_ratio, ax_dsa) = plt.subplots(1, 2, figsize=(7.5, 4.0))
    
    def calc_dsa_curve_fd(a1, a2, dt_rec, T_vec, damping):
        if a1 is None or a2 is None: return np.full_like(T_vec, np.nan)
        npts = len(a1); N = 2**int(np.ceil(np.log2(npts)))
        A1_w = np.fft.rfft(a1, n=N); A2_w = np.fft.rfft(a2, n=N)
        freqs_fft = np.fft.rfftfreq(N, d=dt_rec); omega = 2 * np.pi * freqs_fft
        dsa_list = []
        for T in T_vec:
            wn = 2 * np.pi / T
            with np.errstate(divide='ignore', invalid='ignore'): H = (wn**2 + 2j*damping*wn*omega) / (wn**2 - omega**2 + 2j*damping*wn*omega)
            H[0] = 1.0; R1_w = A1_w * H; R2_w = A2_w * H
            r1 = np.fft.irfft(R1_w, n=N)[:npts]; r2 = np.fft.irfft(R2_w, n=N)[:npts]
            d_out = dfactor(r1, r2, plot=0); dsa_list.append(d_out[4]) 
        return np.array(dsa_list)

    data_groups = [
        (results.get('psa_180_seed', np.zeros((1,len(periods))))*sf, results['s1_scaled'], results['s2_scaled'], C_SCALED, 'Scaled'),
        (results.get('psa_180_sc', np.zeros((1,len(periods)))), results['sc1'], results['sc2'], C_PSA, 'PSA matched')
    ]

    for (mat, acc_x, acc_y, col, lbl) in data_groups:
        if mat is not None and mat.size > 1:
            rotd100 = np.max(mat, axis=0)[idx_p]
            rotd50 = np.percentile(mat, 50, axis=0)[idx_p]
            ratio_curve = rotd100 / rotd50
            ax_ratio.semilogx(p_plot, ratio_curve, color=col, lw=1.0, label=lbl)
            
            dsa_curve = calc_dsa_curve_fd(acc_x, acc_y, results['dt'], periods, zi)[idx_p]
            ax_dsa.semilogx(p_plot, dsa_curve, color=col, lw=1.0, label=lbl)

    ax_ratio.set_xlabel('Period (s)'); ax_ratio.set_ylabel('RotD100 / RotD50'); ax_ratio.set_xlim(0.01, 10)
    ax_ratio.grid(True, which='both', linestyle=':', alpha=0.5); ax_ratio.axvspan(T1PSA, T2PSA, color=COLOR_SHADE, alpha=ALPHA_SHADE, zorder=0)

    ax_dsa.set_xlabel('Period (s)'); ax_dsa.set_ylabel('Directionality Factor'); ax_dsa.set_xlim(0.01, 10)
    ax_dsa.grid(True, which='both', linestyle=':', alpha=0.5); ax_dsa.axvspan(T1PSA, T2PSA, color=COLOR_SHADE, alpha=ALPHA_SHADE, zorder=0)

    legend_handles_4 = [Line2D([0], [0], color=C_SCALED, lw=1.5, label='Scaled'), Line2D([0], [0], color=C_PSA, lw=1.5, label='PSA matched')]
    fig4.legend(handles=legend_handles_4, loc='lower center', ncol=2, bbox_to_anchor=(0.5, 0.0), fontsize=8, frameon=False, columnspacing=1.0)
    plt.tight_layout(rect=(0, 0.1, 1, 1.0))

    return fig1, fig2, fig3, fig4, max_deltas_dict

def dfactor(
        x: np.ndarray, 
        y: np.ndarray, 
        plot: int = 1) -> Tuple[np.ndarray, np.ndarray, float, float, float]:
    
    """
    Computes the directionality factor of a biaxial ground motion or SDOF response.

    Methodology:
    - Coordinate Conversion: Takes the two orthogonal components of the response 
      (x and y) and converts them into polar coordinates to track the response 
      trajectory's radius and angle over time.
    - Envelope Generation: Uses a Convex Hull algorithm to determine the tightest 
      bounding polygon (envelope) containing the entire 2D response trajectory, and 
      calculates the area of this envelope (Area_hull).
    - Peak Response Area: Identifies the absolute maximum response vector (r_max) 
      and calculates the area of a perfect circle bounded by this maximum radius 
      (Area_circle = pi * r_max^2).
    - Directionality Factor (DF): Calculates the DF as the square root of the ratio 
      of the circular area over the hull area (DF = sqrt(Area_circle / Area_hull)). 
      Values close to 1.0 indicate low directionality (isotropic response), while 
      larger values indicate highly polarized, directional shaking (Rivera & Montejo, 2021).

    Parameters
    ----------
    x : np.ndarray
        The 1D time-series representing the x-coordinate of the response.
    y : np.ndarray
        The 1D time-series representing the y-coordinate of the response.
    plot : int, optional
        Flag (1 or 0) indicating whether to generate a polar plot visualizing 
        the response trajectory, convex hull, and bounding circle. Default is 1.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray, float, float, float]
        - hr (np.ndarray): Polar radii of the convex hull vertices.
        - htheta (np.ndarray): Polar angles (radians) of the convex hull vertices.
        - rmax (float): The maximum response magnitude (radius).
        - thetamax (float): The angle (degrees) at which `rmax` occurs.
        - df (float): The calculated Directionality Factor (DF).

    References
    ----------
    Rivera-Figueroa, A., & Montejo, L. A. (2021). Spectral matching 
    RotD100 target spectra: Effect on records characteristics and 
    seismic response. Earthquake Spectra, 37(4), 1-17.
    """   
    
    n1 = np.size(x); n2 = np.size(y); npo = np.min((n1,n2))
    x = x[:npo]; y = y[:npo]
    
    # Change data to polar coordinates:   
    r = np.sqrt(x**2+y**2)      # radius
    theta = np.arctan2(y,x)     # angle in radians
    
    # Maximum radius and angle of occurence:
    rmax = np.amax(r)
    thetamax = theta[np.argmax(r)]
    
    # Determine the envelope of data points (convex hull):
    points  = np.column_stack((x,y))    # stack data in columns
    hull    = ConvexHull(points)        # convex hull 
    
    # Obtain coordinates of the envelope:
    xh = points[hull.vertices,0]        # x-coordinate of hull
    yh = points[hull.vertices,1]        # y-coorindate of hull
    
    # Change envelope coordinates to polar:
    hr = np.sqrt(xh**2+yh**2)      # radius
    htheta = np.arctan2(yh,xh)     # angle in radians
    
    # Determine area of hull and circle with max radius:
    hArea   = 0.5*np.abs(np.dot(xh,np.roll(yh,1)) 
                         - np.dot(yh,np.roll(xh,1)))    # hull area
    mArea   = np.pi*rmax**2                             # circle area

    # Calculate directionality factor                          
    df = (mArea/hArea)**0.5
    
# =============================================================================
#     PLOT:
# =============================================================================
    
    if plot:
        
        plt.style.use('seaborn-talk')
        plt.figure(figsize=(5,4))
        plt.style.use('seaborn-talk')
        rlimit = rmax*1.05
        ax = plt.subplot(111, projection = 'polar')
        ax.plot([0, thetamax], [0, rmax] ,'-o', color='tab:orange', zorder = 3)
        ax.plot(theta, r, color='tab:blue', zorder = 2, linewidth = 1.5)
        ax.fill(htheta,hr, color='tab:blue',alpha = 0.5, linewidth=3, zorder=2)
        circle = plt.Circle((0, 0), rmax, color="tab:orange", 
                 transform=ax.transData._b, alpha=0.5, linewidth=3, zorder=1)
        ax.add_artist(circle)
        ax.set_facecolor('whitesmoke')
        ax.set_rlabel_position(0)
        ax.set_xlabel('DF = %.2f' %df, labelpad = -10, 
                        bbox=dict(boxstyle='square', fc='whitesmoke', ec = 'k'))
        lines, labels = plt.thetagrids(range(0,360,45),())
        lines, labels = ax.set_rgrids((rlimit*.25, rlimit*.5, rlimit*.75, 
                                            rlimit), fontsize = 8, fmt='%.2f')
        
        # To anotate the max resp and ocurrence angle:
        offset = (0,-30) if thetamax<0 else (0,30)
        if np.abs(thetamax+np.pi/2)<0.001: offset = (-30,0)
        hp = 'left' if thetamax<np.pi/2 and thetamax>-1*np.pi/2 else 'right'
        ax.annotate('(%.1f, %.0fº)'% (rmax, np.degrees(thetamax)), 
                      xy=(thetamax,rmax), 
                      textcoords='offset points', fontsize = 10,
                      xytext=offset, ha=hp, va='center',
                      arrowprops=dict(arrowstyle='->',  
                      connectionstyle="angle3,angleA=0,angleB=90"),
                      bbox = dict(boxstyle='round', fc='0.99'), zorder = 5)
        
        plt.suptitle('Directionality Factor') 
        plt.tight_layout(rect=(0,0,1,1))
    
    return(hr, htheta, rmax, np.degrees(thetamax), df)