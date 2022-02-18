import matplotlib
import matplotlib.pyplot as plt
import matplotlib.widgets as mwidgets
from dsc import parse_tabulated_txt
from util import get_encoding_type

# Using Qt backend
matplotlib.use('Qt5Agg')

def dsc_plot(data):
    # Prepare data
    data.prepare_extra()

    # Initialize figure
    fig = plt.figure(constrained_layout=True)
    ax = plt.subplot()

    def plot_tangent(idx, style="r"):
        slope = data.deriv_of(idx)
        offset = data.Heatflow[idx] - slope*data.Tr[idx]
        ax_left,ax_right = ax.get_xlim()
        ax.autoscale(False)
        ax.plot([0,ax_right], 
            [offset, ax_right*slope + offset],
            style)

    # Initialize selectors
    def peak_selector(eclick, erelease):
        pd = data.peak_detect(eclick, erelease)
        ax.plot(data[pd["peak_idx"]][0],
            data[pd["peak_idx"]][1], 'ro')
        ax.plot(data[pd["offset_Tr_idx"]][0],
            data[pd["offset_Tr_idx"]][1], 'go')
        ax.plot(data[pd["onset_Tr_idx"]][0],
            data[pd["onset_Tr_idx"]][1], 'go')

    def tg_selector(eclick, erelease):
        tg = data.tg_detect2(eclick, erelease)
        ax.plot(data[tg["tig_idx"]][0],
            data[tg["tig_idx"]][1], 'ro')
        ax.plot(data[tg["tf_idx"]][0],
            data[tg["tf_idx"]][1], 'go')
        ax.plot(data[tg["tm_idx"]][0],
            data[tg["tm_idx"]][1], 'bo')

    peak_props = dict(facecolor='blue', alpha=0.1)
    tg_props = dict(facecolor='purple', alpha=0.1)
    extra_lines = {}
    peak_selector = mwidgets.RectangleSelector(ax, peak_selector,
        props=peak_props)
    tg_selector = mwidgets.RectangleSelector(ax, tg_selector,
        props=tg_props)
    peak_selector.set_active(False)
    tg_selector.set_active(False)

    # Commands
    def toggle_selector(sel):
        if sel == 'peak': 
            peak_selector.set_active(True)
            tg_selector.set_active(False)
            return
        if sel == 'tg': 
            tg_selector.set_active(True)
            peak_selector.set_active(False)
            return
        elif sel == None:
            peak_selector.set_active(False)
            tg_selector.set_active(False)

    def key_press_event(event):
        if event.key == 'alt+q':
            toggle_selector('peak')
        elif event.key =='alt+w':
            toggle_selector('tg')
        elif event.key == 'alt+d':
            # show first derivative
            extra_lines["deriv1"] = ax.plot(data.Tr, data.Heatflow1Deriv)
        elif event.key == 'alt+f':
            # show second derivative
            extra_lines["deriv2"] = ax.plot(data.Tr, data.Heatflow2Deriv)
        elif event.key == 'escape':
            toggle_selector(None)

    # Connect commands
    fig.canvas.mpl_connect(
        'key_press_event', key_press_event)

    ax.plot(data.Tr, data.Heatflow)
    ax.set_xlabel('Tr')
    ax.set_ylabel('Heatflow')
    plt.show()

#import argparse
#if __name__ == '__main__':
#    parser = argparse.ArgumentParser(
#        description='Plots tabulated text export from Mettler-Toledo STARe '
#        'software.')
#    parser.add_argument('file', help='file to plot')
#    args = parser.parse_args()
#
#    with open(args.file,
#        encoding = get_encoding_type(args.file)) as f:
#        text = f.read()
#        dsc_plot(parse_tabulated_txt(text))
