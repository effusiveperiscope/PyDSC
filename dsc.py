import numpy as np
import scipy.signal as ss
import itertools
import re
from util import get_encoding_type, print_summary_stats, si_intersect, \
    filter_control

SAVGOL_POLYORDER = 3

np.seterr(divide='ignore', invalid='ignore')

#################### DSC data base class ####################
class DSCData:
    def __init__(self):
        self.Index = []
        self.t = []
        self.Heatflow = []
        self.Tr = []
        self.name = ''
        self.notes = ''

        self.savgol_1_window = SAVGOL_POLYORDER + 1
        self.savgol_1_enabled = False

    # Tr space
    def get_tr_selection_mask(self, data_click_x, data_release_x):
        return (self.Tr > min(data_click_x, data_release_x)) & \
            (self.Tr < max(data_click_x, data_release_x))

    def max_tr(self):
        return (max(self.Tr))

    def deriv_of(self, idx):
        return self.Heatflow1Deriv[idx]

    def offset_of(self, idx, deriv):
        return (self.Heatflow[idx] - deriv*self.np_Tr[idx])

    def to_dict(self):
        return {'Index': self.Index, 't': self.t, 'Heatflow': self.Heatflow, 
                'Tr': self.Tr, 'name': self.name, 'notes': self.notes}

    # Prepare for extra analysis (Tg, peak/enthalpy)
    def prepare_extra(self):
        self.np_Index = np.array(self.Index)
        self.np_t = np.array(self.t)
        self.np_Heatflow = np.array(self.Heatflow)
        self.np_Tr = np.array(self.Tr)

        self.Heatflow1Deriv = np.gradient(
            self.np_Heatflow, self.np_Tr)
        if self.savgol_1_enabled:
            self.Heatflow1Deriv = ss.savgol_filter(self.Heatflow1Deriv,
                self.savgol_1_window, SAVGOL_POLYORDER)

    def __getitem__(self, index):
        return (self.Tr[index], self.Heatflow[index])

    # Method 1: Estimate local baseline as horizontal mean of endpoints of
    # region
    def estimate_baseline1(self, center_idx, l_idx, r_idx):
        return np.mean(self.np_Heatflow[np.array(l_idx, r_idx)])

    # Method 2: Estimate local baseline based on the mean of whichever side
    # has the lower standard deviation
    def estimate_baseline2(self, center_idx, l_idx, r_idx):
        center_tr = self.np_Tr[center_idx]
        l_region = (self.np_Tr < center_tr) & (self.np_Tr > l_idx)
        r_region = (self.np_Tr > center_tr) & (self.np_Tr < r_idx)
        return self.np_Heatflow[l_region].mean() if l_mean > r_mean else \
            self.np_Heatflow[r_region].mean()

    def peak_detect(self, x1, x2):
        ### Find peak
        # The peak(s) is/are where the derivative is closest to zero
        # i.e. the absolute value of the derivative is minimum
        sel_mask = self.get_tr_selection_mask(x1, x2)

        idx_in_sel = self.np_Index[sel_mask]

        l_idx = idx_in_sel[np.argmin(self.np_Tr[sel_mask])]
        r_idx = idx_in_sel[np.argmax(self.np_Tr[sel_mask])]

        hf_idx = np.argmin(np.abs(self.Heatflow1Deriv[sel_mask]))

        peak_idx = idx_in_sel[hf_idx]
        peak_tr = self.np_Tr[peak_idx]

        ### Find extrapolated onset/offset temperatures
        # ASTM E2253: Estimate local baseline based on region endpoints
        baseline_slope = (self.np_Heatflow[l_idx] - self.np_Heatflow[r_idx]) /\
            (self.np_Tr[l_idx] - self.np_Tr[r_idx])
        baseline_offset = self.offset_of(l_idx, baseline_slope)

        # Inflection occurs where the absolute value of the derivative is
        # maximum
        l_region = (self.np_Tr < peak_tr) & (self.np_Tr > self.np_Tr[l_idx])
        r_region = (self.np_Tr > peak_tr) & (self.np_Tr < self.np_Tr[r_idx])
        if self.np_Index[l_region].size == 0:
            l_extrap_idx = l_idx
        else:
            l_extrap_idx = \
                self.np_Index[l_region][
                    np.argmax(np.abs(self.Heatflow1Deriv[l_region]))]
        if self.np_Index[r_region].size == 0:
            r_extrap_idx = r_idx
        else:
            r_extrap_idx = \
                self.np_Index[r_region][
                    np.argmax(np.abs(self.Heatflow1Deriv[r_region]))]

        ### TODO Find enthalpy based on trapezoidal integration
        t_baseline_slope = (self.np_Heatflow[l_idx] - self.np_Heatflow[r_idx])\
         / (self.np_t[l_idx] - self.np_t[r_idx])
        t_baseline_offset = self.np_Heatflow[l_idx] - \
            t_baseline_slope*self.np_t[l_idx]

        enthalp_t = self.np_t[sel_mask]
        enthalp_base = enthalp_t * t_baseline_slope + t_baseline_offset
        enthalp_intg = self.np_Heatflow[sel_mask] - enthalp_base
        enthalp_area = np.trapz(enthalp_intg, enthalp_t)

        return {
            'peak_idx': int(peak_idx),
            'onset_Tr_idx': int(self.baseline_intersection2(
                l_extrap_idx, baseline_slope, baseline_offset)),
            'offset_Tr_idx': int(self.baseline_intersection2(
                r_extrap_idx, baseline_slope, baseline_offset)),
            'enthalp_area': float(enthalp_area)
            }

    # Returns an index of a point closest to the x-coordinate of the
    # intersection of the 1st derivative of point specified by point_idx and a
    # baseline specified by baseline_height
    def baseline_intersection(self, point_idx, baseline_height):
        point_deriv = self.Heatflow1Deriv[point_idx]
        point_offset = self.offset_of(point_idx, point_deriv)
        onset_Tr = (baseline_height - point_offset) / point_deriv
        return np.argmin(np.abs(self.np_Tr - onset_Tr))

    # Returns index of a point closest to the x-coordinate of the
    # intersection of the 1st derivative of point specified by point_idx and a
    # baseline specified by baseline_slope and baseline_offset
    def baseline_intersection2(self, point_idx,
            baseline_slope, baseline_offset):
        point_deriv = self.deriv_of(point_idx)
        point_offset = self.offset_of(point_idx, point_deriv)
        onset_Tr = si_intersect(point_deriv, baseline_slope,
            point_offset, baseline_offset)[0]
        return np.argmin(np.abs(self.np_Tr - onset_Tr))

    ### ASTM E1356
    # tg_index is index of maximum first derivative in region
    def tg_detect1(self, x1, x2):
        sel_mask = self.get_tr_selection_mask(x1, x2)

        ### Find Tg
        # Point of maximum absolute first derivative (i.e. 'inflection
        # temperature')
        tg_idx = self.np_Index[sel_mask][
            np.argmax(np.abs(self.Heatflow1Deriv[sel_mask]))]
        return {'tig_idx': tg_idx}

    # tg_index
    def tg_detect2(self, x1, x2):
        sel_mask = self.get_tr_selection_mask(x1, x2)
        idx_in_sel = self.np_Index[sel_mask]
        l_idx = idx_in_sel[np.argmin(self.np_Tr[sel_mask])]
        r_idx = idx_in_sel[np.argmax(self.np_Tr[sel_mask])]

        # The tangents to the points at the boundary of the region are taken as
        # baselines.
        l_deriv = self.Heatflow1Deriv[l_idx]
        l_offset = self.offset_of(l_idx, l_deriv)
        r_deriv = self.Heatflow1Deriv[r_idx]
        r_offset = self.offset_of(r_idx, r_deriv)

        # Inflection (point of greatest slope)
        tig_idx = self.tg_detect1(x1, x2)['tig_idx']

        tig_deriv = self.Heatflow1Deriv[tig_idx]
        tig_offset = self.offset_of(tig_idx, tig_deriv)
        
        # Extrapolated onset temperature
        tf_pt = si_intersect(l_deriv, tig_deriv, l_offset, tig_offset)
        tf_idx = np.argmin(np.abs(self.np_Tr - tf_pt[0]))

        # Extrapolated end temperature
        te_pt = si_intersect(r_deriv, tig_deriv, r_offset, tig_offset)
        te_idx = np.argmin(np.abs(self.np_Tr - te_pt[0]))

        # Midpoint temperature
        tm_idx = np.argmin(np.abs(self.np_Heatflow - np.mean(
            [tf_pt[1],te_pt[1]])))

        return {
            'tig_idx': int(tig_idx),
            'tf_idx': int(tf_idx),
            'tm_idx': int(tm_idx)
        }
        
#################### Text parsing ####################
RE_LINE = re.compile(
    '(\d+)\s+' # int
    '(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+\-]?\d+)?)\s+' # float
    '(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+\-]?\d+)?)\s+' # float
    '(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+\-]?\d+)?)') # float

def parse_tabulated_txt(text):
    ret = DSCData()
    stored_m = None
    for m in re.finditer(RE_LINE, text):
        ret.Index.append(int(m.group(1)))
        ret.t.append(float(m.group(2)))
        ret.Heatflow.append(float(m.group(3)))
        ret.Tr.append(float(m.group(4)))
        stored_m = m
    if not len(ret.Index):
        raise Exception('No rows parsed; possibly wrong file type')
    ret.notes = filter_control(text[stored_m.end():])
    return ret
